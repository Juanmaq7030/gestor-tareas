from flask import (
    Flask, render_template, request, redirect, url_for,
    send_from_directory, make_response, jsonify, session, flash, abort
)
import os
import time
import json
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# ================= APP =================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CAMBIA-ESTO-EN-RENDER")

# ================= RUTAS ABSOLUTAS (CRÍTICO PARA RENDER) =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= CONFIGURACIÓN =================
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'txt'}
ESTADOS = ['Sin Ejecutar', 'En Ejecución', 'Pendiente de', 'Completada', 'Validada']

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

EMPRESAS_FILE = os.path.join(DATA_DIR, "empresas.json")
PROYECTOS_FILE = os.path.join(DATA_DIR, "proyectos.json")
USUARIOS_FILE = os.path.join(DATA_DIR, "usuarios.json")

# ================= UTILIDADES JSON =================
def _read_json(path, default):
    """Lee JSON robusto. Si no existe / está vacío / corrupto => default."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return default
            return json.loads(content)
    except Exception:
        return default

def _write_json(path, data):
    """Escribe JSON asegurando carpeta."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _next_id(items):
    return (max([int(x.get("id", 0)) for x in items]) + 1) if items else 1

def empresas_data():
    return _read_json(EMPRESAS_FILE, {"empresas": []})

def proyectos_data():
    return _read_json(PROYECTOS_FILE, {"proyectos": []})

def usuarios_data():
    return _read_json(USUARIOS_FILE, {"usuarios": []})

def tareas_file(proyecto_id: int):
    return os.path.join(DATA_DIR, f"tareas_{int(proyecto_id)}.json")

def _safe_remove(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def ensure_core_files():
    """Asegura JSON base (evita 500 por archivos faltantes)."""
    if not os.path.exists(EMPRESAS_FILE):
        _write_json(EMPRESAS_FILE, {"empresas": []})
    if not os.path.exists(PROYECTOS_FILE):
        _write_json(PROYECTOS_FILE, {"proyectos": []})
    if not os.path.exists(USUARIOS_FILE):
        _write_json(USUARIOS_FILE, {"usuarios": []})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def no_cache(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return wrapper

# ================= AUTH =================
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    users = usuarios_data()["usuarios"]
    return next((u for u in users if u.get("id") == uid), None)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def require_roles(*roles):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            u = current_user()
            if not u:
                return redirect(url_for("login"))
            if u.get("rol") not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return deco

# -------- Proyecto activo en sesión --------
def active_project_id():
    pid = session.get("project_id")
    try:
        return int(pid) if pid is not None else None
    except Exception:
        return None

def set_active_project(pid: int):
    session["project_id"] = int(pid)

def clear_active_project():
    session.pop("project_id", None)

def _get_project(proyecto_id: int):
    proyectos = proyectos_data()["proyectos"]
    return next((p for p in proyectos if p.get("id") == int(proyecto_id)), None)

def _is_project_terminated(proyecto_id: int) -> bool:
    p = _get_project(proyecto_id)
    if not p:
        return True
    return bool(p.get("terminado", False))

def user_can_access_project(u, proyecto_id: int) -> bool:
    if u.get("rol") == "superadmin":
        return True
    p = _get_project(int(proyecto_id))
    if not p:
        return False
    # bloquea acceso a proyectos terminados para no-superadmin
    if p.get("terminado", False):
        return False
    return p.get("empresa_id") == u.get("empresa_id")

def require_project_access(f):
    @wraps(f)
    def wrapper(proyecto_id, *args, **kwargs):
        u = current_user()
        if not u:
            return redirect(url_for("login"))
        if not user_can_access_project(u, int(proyecto_id)):
            abort(403)
        return f(proyecto_id, *args, **kwargs)
    return wrapper

# ================= TAREAS POR PROYECTO =================
def load_tareas(proyecto_id: int):
    data = _read_json(tareas_file(proyecto_id), {"tareas": [], "contador_id": 1})
    tareas = data.get("tareas", [])
    contador_id = data.get("contador_id", 1)
    if tareas:
        contador_id = max(contador_id, max(t.get('id', 0) for t in tareas) + 1)

    cambios = False
    for t in tareas:
        estado_antiguo = t.get('situacion', 'Pendiente')
        if estado_antiguo == 'Pendiente':
            t['situacion'] = 'Sin Ejecutar'; cambios = True
        elif estado_antiguo == 'Terminada':
            t['situacion'] = 'Completada'; cambios = True
        elif estado_antiguo == 'Lista Para Validar':
            t['situacion'] = 'Pendiente de'; cambios = True
        elif estado_antiguo not in ESTADOS:
            t['situacion'] = 'Sin Ejecutar'; cambios = True

        t.setdefault('responsable', '')
        t.setdefault('centro_responsabilidad', '')
        t.setdefault('plazo', '')
        t.setdefault('documentos', [])
        t.setdefault('observacion', '')
        t.setdefault('recursos', '')

    if cambios:
        save_tareas(proyecto_id, tareas, contador_id)

    return tareas, contador_id

def save_tareas(proyecto_id: int, tareas: list, contador_id: int):
    _write_json(tareas_file(proyecto_id), {"tareas": tareas, "contador_id": contador_id})

def agregar_tarea(proyecto_id, texto, responsable, centro, plazo, observacion, recursos):
    tareas, contador_id = load_tareas(proyecto_id)
    tarea = {
        'id': contador_id,
        'texto': texto.strip(),
        'situacion': 'Sin Ejecutar',
        'responsable': (responsable or '').strip(),
        'centro_responsabilidad': (centro or '').strip(),
        'plazo': (plazo or '').strip(),
        'observacion': (observacion or '').strip(),
        'recursos': (recursos or '').strip(),
        'documentos': []
    }
    tareas.append(tarea)
    contador_id += 1
    save_tareas(proyecto_id, tareas, contador_id)
    return tarea

def cambiar_estado(proyecto_id, tid, estado, user):
    if estado == "Validada" and user.get("rol") not in ("supervisor", "superadmin"):
        return False
    tareas, contador_id = load_tareas(proyecto_id)
    for t in tareas:
        if t.get("id") == tid and estado in ESTADOS:
            t["situacion"] = estado
            save_tareas(proyecto_id, tareas, contador_id)
            return True
    return False

def actualizar_tarea(proyecto_id, tid, responsable=None, centro=None, plazo=None, observacion=None, recursos=None):
    tareas, contador_id = load_tareas(proyecto_id)
    for t in tareas:
        if t.get('id') == tid:
            if responsable is not None: t['responsable'] = responsable.strip()
            if centro is not None: t['centro_responsabilidad'] = centro.strip()
            if plazo is not None: t['plazo'] = plazo.strip()
            if observacion is not None: t['observacion'] = observacion.strip()
            if recursos is not None: t['recursos'] = recursos.strip()
            save_tareas(proyecto_id, tareas, contador_id)
            return True
    return False

def agregar_documento(proyecto_id, tid, filename):
    tareas, contador_id = load_tareas(proyecto_id)
    for t in tareas:
        if t.get('id') == tid:
            if filename not in t['documentos']:
                t['documentos'].append(filename)
                save_tareas(proyecto_id, tareas, contador_id)
                return True
    return False

# ================= ESTADÍSTICAS =================
def obtener_estadisticas(tareas_filtradas, estados=ESTADOS):
    hoy = datetime.now().date()

    por_estado = {estado: 0 for estado in estados}
    for t in tareas_filtradas:
        est = t.get('situacion', 'Sin Ejecutar')
        if est in por_estado:
            por_estado[est] += 1

    por_responsable = {}
    for t in tareas_filtradas:
        resp = t.get('responsable', '') or 'Sin asignar'
        por_responsable[resp] = por_responsable.get(resp, 0) + 1

    por_centro = {}
    for t in tareas_filtradas:
        centro = t.get('centro_responsabilidad', '') or 'Sin asignar'
        por_centro[centro] = por_centro.get(centro, 0) + 1

    vencidas = 0
    por_vencer = 0
    sin_plazo = 0

    for t in tareas_filtradas:
        plazo_str = t.get('plazo', '')
        if plazo_str:
            try:
                plazo_date = datetime.strptime(plazo_str, '%Y-%m-%d').date()
                if plazo_date < hoy:
                    vencidas += 1
                else:
                    por_vencer += 1
            except:
                sin_plazo += 1
        else:
            sin_plazo += 1

    return {
        'total': len(tareas_filtradas),
        'por_estado': por_estado,
        'por_responsable': por_responsable,
        'por_centro': por_centro,
        'vencidas': vencidas,
        'por_vencer': por_vencer,
        'sin_plazo': sin_plazo
    }

def filtrar_tareas(tareas, centro=None, responsable=None, estado=None, plazo=None):
    tareas_filtradas = tareas.copy()
    hoy = datetime.now().date()

    if centro and centro != 'Todos':
        tareas_filtradas = [t for t in tareas_filtradas if t.get('centro_responsabilidad') == centro]

    if responsable and responsable != 'Todos':
        tareas_filtradas = [t for t in tareas_filtradas if t.get('responsable') == responsable]

    if estado and estado != 'Todos':
        tareas_filtradas = [t for t in tareas_filtradas if t.get('situacion') == estado]

    if plazo and plazo != 'Todos':
        if plazo == 'vencidas':
            tmp = []
            for t in tareas_filtradas:
                if t.get('plazo'):
                    try:
                        if datetime.strptime(t.get('plazo'), '%Y-%m-%d').date() < hoy:
                            tmp.append(t)
                    except:
                        pass
            tareas_filtradas = tmp
        elif plazo == 'por_vencer':
            tmp = []
            for t in tareas_filtradas:
                if t.get('plazo'):
                    try:
                        if datetime.strptime(t.get('plazo'), '%Y-%m-%d').date() >= hoy:
                            tmp.append(t)
                    except:
                        pass
            tareas_filtradas = tmp
        elif plazo == 'sin_plazo':
            tareas_filtradas = [t for t in tareas_filtradas if not t.get('plazo')]

    return tareas_filtradas

# ================= SEED/RESET SUPERADMIN =================
def ensure_superadmin():
    """
    Crea o actualiza el superadmin usando variables de entorno:
    - ADMIN_EMAIL (default admin@tuapp.cl)
    - ADMIN_PASSWORD (default Admin123!)
    - ADMIN_FORCE_RESET=1 para forzar cambio de contraseña/correo
    """
    ensure_core_files()

    admin_email = (os.getenv("ADMIN_EMAIL", "admin@tuapp.cl") or "admin@tuapp.cl").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")
    force_reset = os.getenv("ADMIN_FORCE_RESET", "0") == "1"

    ud = usuarios_data()
    users = ud["usuarios"]

    by_email = next((u for u in users if (u.get("correo", "").strip().lower() == admin_email)), None)
    if by_email:
        by_email["rol"] = "superadmin"
        by_email["empresa_id"] = None
        if force_reset:
            by_email["password_hash"] = generate_password_hash(admin_password)
        ud["usuarios"] = users
        _write_json(USUARIOS_FILE, ud)
        print(f"✅ Superadmin OK (existente): {admin_email} | reset={force_reset}")
        return

    existing_super = next((u for u in users if u.get("rol") == "superadmin"), None)
    if existing_super:
        if force_reset:
            existing_super["correo"] = admin_email
            existing_super["password_hash"] = generate_password_hash(admin_password)
            existing_super["empresa_id"] = None
            existing_super["rol"] = "superadmin"
            ud["usuarios"] = users
            _write_json(USUARIOS_FILE, ud)
            print(f"✅ Superadmin actualizado: {admin_email}")
        else:
            print("ℹ️ Ya existe un superadmin. Usa ADMIN_FORCE_RESET=1 si quieres resetearlo.")
        return

    uid = _next_id(users)
    users.append({
        "id": uid,
        "nombre": "Super Admin",
        "correo": admin_email,
        "password_hash": generate_password_hash(admin_password),
        "rol": "superadmin",
        "empresa_id": None
    })
    ud["usuarios"] = users
    _write_json(USUARIOS_FILE, ud)
    print(f"✅ Superadmin creado: {admin_email} (cámbialo)")

# ================= CREACIÓN EMPRESA/PROYECTO/USUARIOS =================
def crear_empresa_con_proyecto_y_roles(nombre_empresa, nombre_proyecto, correo_sup, pass_sup, correo_eje, pass_eje, max_users=5, max_proys=1):
    ensure_core_files()

    ed = empresas_data()
    empresas = ed["empresas"]
    empresa_id = _next_id(empresas)
    empresas.append({
        "id": empresa_id,
        "nombre": nombre_empresa,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d"),
        "licencia_max_usuarios": int(max_users),
        "licencia_max_proyectos": int(max_proys),
        "activa": True
    })
    ed["empresas"] = empresas
    _write_json(EMPRESAS_FILE, ed)

    pd_ = proyectos_data()
    proyectos = pd_["proyectos"]
    proyecto_id = _next_id(proyectos)
    proyectos.append({
        "id": proyecto_id,
        "empresa_id": empresa_id,
        "nombre": nombre_proyecto,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d"),
        "terminado": False
    })
    pd_["proyectos"] = proyectos
    _write_json(PROYECTOS_FILE, pd_)

    save_tareas(proyecto_id, [], 1)

    ud = usuarios_data()
    users = ud["usuarios"]

    if any((u.get("correo", "").lower() == correo_sup.lower()) for u in users):
        raise ValueError("Correo supervisor ya existe")
    if any((u.get("correo", "").lower() == correo_eje.lower()) for u in users):
        raise ValueError("Correo ejecutor ya existe")

    sup_id = _next_id(users)
    users.append({
        "id": sup_id,
        "nombre": "Supervisor",
        "correo": correo_sup,
        "password_hash": generate_password_hash(pass_sup),
        "rol": "supervisor",
        "empresa_id": empresa_id
    })

    eje_id = _next_id(users)
    users.append({
        "id": eje_id,
        "nombre": "Ejecutor",
        "correo": correo_eje,
        "password_hash": generate_password_hash(pass_eje),
        "rol": "ejecutor",
        "empresa_id": empresa_id
    })

    ud["usuarios"] = users
    _write_json(USUARIOS_FILE, ud)

    return empresa_id, proyecto_id

# ================= RUTAS AUTH =================
@app.route("/login", methods=["GET", "POST"])
@no_cache
def login():
    if request.method == "POST":
        ident = (request.form.get("correo") or request.form.get("username") or request.form.get("usuario") or "").strip().lower()
        password = request.form.get("password") or ""

        users = usuarios_data()["usuarios"]
        u = next((x for x in users if (x.get("correo", "").strip().lower() == ident)), None)

        if not u or not check_password_hash(u.get("password_hash", ""), password):
            flash("Credenciales inválidas", "error")
            return render_template("login.html"), 200

        session.clear()
        session["user_id"] = u["id"]
        session["nombre"] = u.get("nombre") or u.get("correo") or "Usuario"
        session["rol"] = u.get("rol")
        session["empresa_id"] = u.get("empresa_id")
        clear_active_project()

        if u.get("rol") == "superadmin":
            return redirect(url_for("sa_dashboard"))

        return redirect(url_for("seleccionar_proyecto"))

    return render_template("login.html"), 200

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def root():
    u = current_user()
    if not u:
        return redirect(url_for("login"))

    if u.get("rol") == "superadmin":
        return redirect(url_for("sa_dashboard"))

    pid = active_project_id()
    if pid:
        if u.get("rol") == "supervisor":
            return redirect(url_for("proyecto_tablero", proyecto_id=pid))
        return redirect(url_for("proyecto_index", proyecto_id=pid))

    return redirect(url_for("seleccionar_proyecto"))

# ================= SUPERADMIN =================
@app.route("/sa")
@login_required
@require_roles("superadmin")
def sa_dashboard():
    empresas = empresas_data()["empresas"]
    proyectos = proyectos_data()["proyectos"]
    usuarios = usuarios_data()["usuarios"]
    resumen = []
    for e in empresas:
        proys = [p for p in proyectos if p.get("empresa_id") == e.get("id")]
        users = [u for u in usuarios if u.get("empresa_id") == e.get("id")]
        resumen.append({"empresa": e, "n_proyectos": len(proys), "n_usuarios": len(users)})
    return render_template("admin_dashboard.html", resumen=resumen)

# ================= SUPERADMIN: SECCIONES (LISTADOS) =================
@app.route("/sa/empresas")
@login_required
@require_roles("superadmin")
def sa_empresas():
    empresas = empresas_data()["empresas"]
    return render_template("sa_empresas.html", empresas=empresas)

@app.route("/sa/usuarios")
@login_required
@require_roles("superadmin")
def sa_usuarios():
    usuarios = usuarios_data()["usuarios"]
    empresas = empresas_data()["empresas"]
    emp_map = {e.get("id"): e.get("nombre") for e in empresas}
    usuarios_out = []
    for u in usuarios:
        uu = dict(u)
        uu["empresa_nombre"] = emp_map.get(uu.get("empresa_id"), "-")
        usuarios_out.append(uu)
    return render_template("sa_usuarios.html", usuarios=usuarios_out)

@app.route("/sa/proyectos")
@login_required
@require_roles("superadmin")
def sa_proyectos():
    proyectos = proyectos_data()["proyectos"]
    empresas = empresas_data()["empresas"]
    emp_map = {e.get("id"): e.get("nombre") for e in empresas}
    proyectos_out = []
    for p in proyectos:
        pp = dict(p)
        pp["empresa_nombre"] = emp_map.get(pp.get("empresa_id"), "-")
        proyectos_out.append(pp)
    return render_template("sa_proyectos.html", proyectos=proyectos_out)

@app.route("/sa/empresa/nueva", methods=["GET", "POST"])
@login_required
@require_roles("superadmin")
def sa_empresa_nueva():
    if request.method == "POST":
        nombre_empresa = (request.form.get("nombre_empresa") or "").strip()
        nombre_proyecto = (request.form.get("nombre_proyecto") or "Proyecto 1").strip()

        correo_sup = (request.form.get("correo_supervisor") or "").strip()
        pass_sup = request.form.get("pass_supervisor") or ""

        correo_eje = (request.form.get("correo_ejecutor") or "").strip()
        pass_eje = request.form.get("pass_ejecutor") or ""

        try:
            max_users = int(request.form.get("licencia_max_usuarios") or 5)
        except ValueError:
            max_users = 5
        try:
            max_proys = int(request.form.get("licencia_max_proyectos") or 1)
        except ValueError:
            max_proys = 1

        if not (nombre_empresa and correo_sup and pass_sup and correo_eje and pass_eje):
            flash("Faltan datos", "error")
            return render_template("sa_empresa_nueva.html")

        try:
            crear_empresa_con_proyecto_y_roles(
                nombre_empresa, nombre_proyecto,
                correo_sup, pass_sup,
                correo_eje, pass_eje,
                max_users, max_proys
            )
            flash("Empresa creada con proyecto y roles (Supervisor/Ejecutor).", "ok")
            return redirect(url_for("sa_dashboard"))
        except Exception as e:
            flash(str(e), "error")
            return render_template("sa_empresa_nueva.html")

    return render_template("sa_empresa_nueva.html")

# ================= SUPERADMIN: ELIMINAR EMPRESA (cascada) =================
@app.route("/sa/empresa/<int:empresa_id>/eliminar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_empresa_eliminar(empresa_id):
    ed = empresas_data()
    pd_ = proyectos_data()
    ud = usuarios_data()

    empresas = ed["empresas"]
    proyectos = pd_["proyectos"]
    usuarios = ud["usuarios"]

    proys_emp = [p for p in proyectos if p.get("empresa_id") == empresa_id]
    for p in proys_emp:
        _safe_remove(tareas_file(p.get("id")))

    proyectos = [p for p in proyectos if p.get("empresa_id") != empresa_id]
    usuarios = [u for u in usuarios if u.get("empresa_id") != empresa_id]
    empresas = [e for e in empresas if e.get("id") != empresa_id]

    ed["empresas"] = empresas
    pd_["proyectos"] = proyectos
    ud["usuarios"] = usuarios

    _write_json(EMPRESAS_FILE, ed)
    _write_json(PROYECTOS_FILE, pd_)
    _write_json(USUARIOS_FILE, ud)

    flash("Empresa eliminada (con proyectos/usuarios asociados).", "ok")
    return redirect(url_for("sa_config"))

# =======================
# SUPERADMIN: CONFIG PANEL (CRUD)
# =======================
def _bool(v):
    return str(v).strip().lower() in ("1", "true", "on", "yes", "si", "sí")

@app.route("/sa/config")
@login_required
@require_roles("superadmin")
@no_cache
def sa_config():
    ed = empresas_data()
    pd_ = proyectos_data()
    ud = usuarios_data()

    empresas = ed["empresas"]
    proyectos = pd_["proyectos"]
    usuarios = ud["usuarios"]

    proys_por_empresa = {}
    for p in proyectos:
        proys_por_empresa.setdefault(p.get("empresa_id"), []).append(p)

    users_por_empresa = {}
    for u in usuarios:
        users_por_empresa.setdefault(u.get("empresa_id"), []).append(u)

    empresas_sorted = sorted(empresas, key=lambda x: (str(x.get("nombre", "")).lower(), x.get("id", 0)))
    for k in proys_por_empresa:
        proys_por_empresa[k] = sorted(proys_por_empresa[k], key=lambda x: (str(x.get("nombre", "")).lower(), x.get("id", 0)))
    for k in users_por_empresa:
        users_por_empresa[k] = sorted(users_por_empresa[k], key=lambda x: (str(x.get("correo", "")).lower(), x.get("id", 0)))

    return render_template(
        "sa_config.html",
        empresas=empresas_sorted,
        proys_por_empresa=proys_por_empresa,
        users_por_empresa=users_por_empresa,
        proyectos=proyectos,
        usuarios=usuarios,
        data_dir=DATA_DIR
    )

@app.route("/sa/empresa/<int:empresa_id>/editar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_empresa_editar(empresa_id):
    ed = empresas_data()
    empresas = ed["empresas"]

    nombre = (request.form.get("nombre") or "").strip()
    activa = _bool(request.form.get("activa"))

    e = next((x for x in empresas if x.get("id") == empresa_id), None)
    if not e:
        abort(404)

    if nombre:
        e["nombre"] = nombre
    e["activa"] = activa

    ed["empresas"] = empresas
    _write_json(EMPRESAS_FILE, ed)
    flash("Empresa actualizada.", "ok")
    return redirect(url_for("sa_config"))

@app.route("/sa/proyecto/<int:proyecto_id>/editar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_proyecto_editar(прoyecto_id=None, proyecto_id=None):
    # (compat) por si algún editor mete caracteres raros; usamos proyecto_id real
    proyecto_id = proyecto_id if proyecto_id is not None else int(прoyecto_id)

    pd_ = proyectos_data()
    proyectos = pd_["proyectos"]

    nombre = (request.form.get("nombre") or "").strip()
    terminado = _bool(request.form.get("terminado"))

    p = next((x for x in proyectos if x.get("id") == proyecto_id), None)
    if not p:
        abort(404)

    if nombre:
        p["nombre"] = nombre

    if terminado:
        p["terminado"] = True
        p["fecha_termino"] = datetime.now().strftime("%Y-%m-%d")
    else:
        p["terminado"] = False
        p.pop("fecha_termino", None)

    pd_["proyectos"] = proyectos
    _write_json(PROYECTOS_FILE, pd_)
    flash("Proyecto actualizado.", "ok")
    return redirect(url_for("sa_config"))

@app.route("/sa/proyecto/<int:proyecto_id>/eliminar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_proyecto_eliminar_post(proyecto_id):
    pd_ = proyectos_data()
    proyectos = pd_["proyectos"]
    proyectos = [p for p in proyectos if p.get("id") != proyecto_id]
    pd_["proyectos"] = proyectos
    _write_json(PROYECTOS_FILE, pd_)

    _safe_remove(tareas_file(proyecto_id))
    flash("Proyecto eliminado (y archivo de tareas asociado).", "ok")
    return redirect(url_for("sa_config"))

@app.route("/sa/usuario/<int:user_id>/editar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_usuario_editar(user_id):
    ud = usuarios_data()
    usuarios = ud["usuarios"]

    nombre = (request.form.get("nombre") or "").strip()
    correo = (request.form.get("correo") or "").strip().lower()
    rol = (request.form.get("rol") or "").strip().lower()

    u = next((x for x in usuarios if x.get("id") == user_id), None)
    if not u:
        abort(404)

    if nombre:
        u["nombre"] = nombre

    if correo:
        existe = any((x.get("id") != user_id and (x.get("correo", "").strip().lower() == correo)) for x in usuarios)
        if existe:
            flash("Ese correo ya existe en otro usuario.", "error")
            return redirect(url_for("sa_config"))
        u["correo"] = correo

    if rol in ("superadmin", "supervisor", "ejecutor"):
        u["rol"] = rol
        if rol == "superadmin":
            u["empresa_id"] = None

    ud["usuarios"] = usuarios
    _write_json(USUARIOS_FILE, ud)
    flash("Usuario actualizado.", "ok")
    return redirect(url_for("sa_config"))

@app.route("/sa/usuario/<int:user_id>/reset-password", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_usuario_reset_password(user_id):
    ud = usuarios_data()
    usuarios = ud["usuarios"]

    new_pass = request.form.get("new_password") or ""
    if len(new_pass) < 6:
        flash("La nueva contraseña debe tener al menos 6 caracteres.", "error")
        return redirect(url_for("sa_config"))

    u = next((x for x in usuarios if x.get("id") == user_id), None)
    if not u:
        abort(404)

    u["password_hash"] = generate_password_hash(new_pass)
    ud["usuarios"] = usuarios
    _write_json(USUARIOS_FILE, ud)

    flash("Contraseña reseteada ✅", "ok")
    return redirect(url_for("sa_config"))

@app.route("/sa/usuario/<int:user_id>/eliminar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_usuario_eliminar_post(user_id):
    ud = usuarios_data()
    usuarios = ud["usuarios"]
    usuarios = [u for u in usuarios if u.get("id") != user_id]
    ud["usuarios"] = usuarios
    _write_json(USUARIOS_FILE, ud)
    flash("Usuario eliminado.", "ok")
    return redirect(url_for("sa_config"))

# ================= DASHBOARD EMPRESA =================
@app.route("/empresa")
@login_required
@require_roles("supervisor", "ejecutor")
@no_cache
def empresa_dashboard():
    u = current_user()
    empresas = empresas_data()["empresas"]
    proyectos = proyectos_data()["proyectos"]

    empresa = next((e for e in empresas if e.get("id") == u.get("empresa_id")), None)

    # ocultar terminados
    proys = [
        p for p in proyectos
        if p.get("empresa_id") == u.get("empresa_id") and not p.get("terminado", False)
    ]

    avances = []
    for p in proys:
        tareas, _ = load_tareas(p.get("id"))
        est = obtener_estadisticas(tareas)

        total = est["total"]
        comp = est["por_estado"].get("Completada", 0)
        val = est["por_estado"].get("Validada", 0)
        avance = round(((comp + val) / total) * 100, 1) if total else 0
        avances.append({"proyecto": p, "estadisticas": est, "avance_pct": avance})

    return render_template("empresa_dashboard.html", empresa=empresa, avances=avances, user=u)

# ================= SELECCIONAR PROYECTO =================
@app.route("/seleccionar-proyecto", methods=["GET"])
@login_required
@require_roles("supervisor", "ejecutor")
@no_cache
def seleccionar_proyecto():
    u = current_user()
    proyectos = proyectos_data()["proyectos"]

    # ocultar terminados
    proys = [
        p for p in proyectos
        if p.get("empresa_id") == u.get("empresa_id") and not p.get("terminado", False)
    ]

    if not proys:
        flash("Tu empresa no tiene proyectos activos. Pide al Superadmin que cree o reactive uno.", "error")
        return redirect(url_for("empresa_dashboard"))

    if len(proys) == 1:
        pid = int(proys[0]["id"])
        set_active_project(pid)
        if u.get("rol") == "supervisor":
            return redirect(url_for("proyecto_tablero", proyecto_id=pid))
        return redirect(url_for("proyecto_index", proyecto_id=pid))

    return render_template("seleccionar_proyecto.html", proyectos=proys, user=u)

@app.route("/seleccionar-proyecto/<int:proyecto_id>", methods=["POST"])
@login_required
@require_roles("supervisor", "ejecutor")
def seleccionar_proyecto_post(proyecto_id):
    u = current_user()
    if not user_can_access_project(u, proyecto_id):
        abort(403)

    set_active_project(proyecto_id)

    if u.get("rol") == "supervisor":
        return redirect(url_for("proyecto_tablero", proyecto_id=proyecto_id))
    return redirect(url_for("proyecto_index", proyecto_id=proyecto_id))

@app.route("/cambiar-proyecto", methods=["POST"])
@login_required
@require_roles("supervisor", "ejecutor")
def cambiar_proyecto():
    clear_active_project()
    return redirect(url_for("seleccionar_proyecto"))

# ✅ Atajo para entrar a un proyecto desde empresa_dashboard.html
@app.route("/empresa/ir/<int:proyecto_id>")
@login_required
@require_roles("supervisor", "ejecutor", "superadmin")
def empresa_ir_proyecto(proyecto_id):
    u = current_user()

    # superadmin puede entrar a terminados (si quisiera), otros NO
    if u.get("rol") != "superadmin" and _is_project_terminated(proyecto_id):
        abort(403)

    if not user_can_access_project(u, proyecto_id):
        abort(403)

    if u.get("rol") != "superadmin":
        set_active_project(proyecto_id)

    if u.get("rol") == "supervisor":
        return redirect(url_for("proyecto_tablero", proyecto_id=proyecto_id))
    return redirect(url_for("proyecto_index", proyecto_id=proyecto_id))

# ================= PROYECTO: PLANIFICADOR =================
@app.route("/p/<int:proyecto_id>/")
@login_required
@require_project_access
@no_cache
def proyecto_index(proyecto_id):
    tareas, _ = load_tareas(proyecto_id)
    return render_template("index.html", tareas=tareas, estados=ESTADOS, proyecto_id=proyecto_id, user=current_user())

@app.route("/p/<int:proyecto_id>/agregar", methods=["POST"])
@login_required
@require_project_access
def proyecto_agregar(proyecto_id):
    texto = request.form.get('texto', '').strip()
    if texto:
        agregar_tarea(
            proyecto_id,
            texto,
            request.form.get('responsable', ''),
            request.form.get('centro_responsabilidad', ''),
            request.form.get('plazo', ''),
            request.form.get('observacion', ''),
            request.form.get('recursos', '')
        )
    return redirect(url_for("proyecto_index", proyecto_id=proyecto_id))

@app.route("/p/<int:proyecto_id>/cambiar_estado/<int:tid>", methods=["POST"])
@login_required
@require_project_access
def proyecto_cambiar_estado(proyecto_id, tid):
    estado = request.form.get('situacion', '')
    cambiar_estado(proyecto_id, tid, estado, current_user())
    return redirect(url_for("proyecto_index", proyecto_id=proyecto_id))

@app.route("/p/<int:proyecto_id>/actualizar_tarea/<int:tid>", methods=["POST"])
@login_required
@require_project_access
def proyecto_actualizar_tarea(proyecto_id, tid):
    actualizar_tarea(
        proyecto_id,
        tid,
        request.form.get('responsable'),
        request.form.get('centro_responsabilidad'),
        request.form.get('plazo'),
        request.form.get('observacion'),
        request.form.get('recursos')
    )
    return redirect(url_for("proyecto_index", proyecto_id=proyecto_id))

@app.route("/p/<int:proyecto_id>/adjuntar/<int:tid>", methods=["POST"])
@login_required
@require_project_access
def proyecto_adjuntar(proyecto_id, tid):
    file = request.files.get('documento')
    if file and file.filename and allowed_file(file.filename):
        name, ext = os.path.splitext(secure_filename(file.filename))
        if not name:
            name = 'documento'
        filename = f"{proyecto_id}_{tid}_{name}_{int(time.time() * 1000)}{ext}"
        filename = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        if os.path.exists(filepath):
            agregar_documento(proyecto_id, tid, filename)
    return redirect(url_for("proyecto_index", proyecto_id=proyecto_id))

@app.route("/uploads/<filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ================= PROYECTO: TABLERO =================
@app.route("/p/<int:proyecto_id>/tablero")
@login_required
@require_project_access
@no_cache
def proyecto_tablero(proyecto_id):
    tareas, _ = load_tareas(proyecto_id)

    centro_filtro = request.args.get('centro', 'Todos')
    responsable_filtro = request.args.get('responsable', 'Todos')
    estado_filtro = request.args.get('estado', 'Todos')
    plazo_filtro = request.args.get('plazo', 'Todos')

    tareas_filtradas = filtrar_tareas(
        tareas,
        centro=centro_filtro if centro_filtro != 'Todos' else None,
        responsable=responsable_filtro if responsable_filtro != 'Todos' else None,
        estado=estado_filtro if estado_filtro != 'Todos' else None,
        plazo=plazo_filtro if plazo_filtro != 'Todos' else None
    )

    estadisticas = obtener_estadisticas(tareas_filtradas)
    estadisticas_totales = obtener_estadisticas(tareas)

    responsables_unicos = sorted(set([t.get('responsable', '') for t in tareas if t.get('responsable')]))
    centros_unicos = sorted(set([t.get('centro_responsabilidad', '') for t in tareas if t.get('centro_responsabilidad')]))

    return render_template(
        "tablero.html",
        tareas=tareas_filtradas,
        estadisticas=estadisticas,
        estadisticas_totales=estadisticas_totales,
        estados=ESTADOS,
        responsables=responsables_unicos,
        centros=centros_unicos,
        filtros={
            "centro": centro_filtro,
            "responsable": responsable_filtro,
            "estado": estado_filtro,
            "plazo": plazo_filtro
        },
        proyecto_id=proyecto_id,
        user=current_user()
    )

# ================= PROYECTO: INFORME =================
@app.route("/p/<int:proyecto_id>/informe")
@login_required
@require_project_access
@no_cache
def proyecto_informe(proyecto_id):
    tareas, _ = load_tareas(proyecto_id)
    estadisticas = obtener_estadisticas(tareas)
    hoy = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    tareas_vencidas = []
    limite = datetime.now().date() + timedelta(days=7)
    tareas_por_vencer = []

    for t in tareas:
        plazo_str = t.get("plazo", "")
        if not plazo_str:
            continue
        try:
            fecha = datetime.strptime(plazo_str, '%Y-%m-%d').date()
        except:
            continue
        if fecha < datetime.now().date():
            tareas_vencidas.append(t)
        if datetime.now().date() <= fecha <= limite:
            tareas_por_vencer.append(t)

    return render_template(
        "informe.html",
        estadisticas=estadisticas,
        tareas=tareas,
        tareas_vencidas=tareas_vencidas,
        tareas_por_vencer=tareas_por_vencer,
        fecha_reporte=hoy,
        estados=ESTADOS,
        proyecto_id=proyecto_id
    )

@app.route("/about")
def about():
    return render_template("about.html")

# ================= INIT =================
ensure_superadmin()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
