from flask import Flask, render_template, request, redirect, url_for, send_from_directory, make_response, jsonify, session, flash, abort
import os
import time
import json
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import smtplib
from email.message import EmailMessage
import threading

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia-esto-en-render")

# ================= CONFIGURACIÓN =================

UPLOAD_FOLDER = 'uploads'
DATA_DIR = 'data'
ALLOWED_EXTENSIONS = {'pdf','png','jpg','jpeg','gif','doc','docx','xls','xlsx','txt'}

ESTADOS = ['Sin Ejecutar', 'En Ejecución', 'Pendiente de', 'Completada', 'Validada']

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ================= PERSISTENCIA (JSON “comercial simple”) =================
# Archivos:
# data/empresas.json
# data/proyectos.json
# data/usuarios.json
# data/tareas_<proyecto_id>.json

EMPRESAS_FILE = os.path.join(DATA_DIR, "empresas.json")
PROYECTOS_FILE = os.path.join(DATA_DIR, "proyectos.json")
USUARIOS_FILE = os.path.join(DATA_DIR, "usuarios.json")

def _read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _next_id(items):
    if not items:
        return 1
    return max(int(x.get("id", 0)) for x in items) + 1

def load_empresas():
    return _read_json(EMPRESAS_FILE, {"empresas": []})

def save_empresas(data):
    _write_json(EMPRESAS_FILE, data)

def load_proyectos():
    return _read_json(PROYECTOS_FILE, {"proyectos": []})

def save_proyectos(data):
    _write_json(PROYECTOS_FILE, data)

def load_usuarios():
    return _read_json(USUARIOS_FILE, {"usuarios": []})

def save_usuarios(data):
    _write_json(USUARIOS_FILE, data)

def tareas_file(proyecto_id: int):
    return os.path.join(DATA_DIR, f"tareas_{int(proyecto_id)}.json")

def load_tareas(proyecto_id: int):
    data = _read_json(tareas_file(proyecto_id), {"tareas": [], "contador_id": 1})
    # Normalización (igual a tu lógica actual)
    tareas = data.get("tareas", [])
    contador_id = data.get("contador_id", 1)
    if tareas:
        max_id = max(t.get("id", 0) for t in tareas)
        contador_id = max(contador_id, max_id + 1)
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

        # Multiusuario: asignación opcional
        t.setdefault('asignado_a_user_id', None)

    if cambios:
        save_tareas(proyecto_id, tareas, contador_id)

    return tareas, contador_id

def save_tareas(proyecto_id: int, tareas: list, contador_id: int):
    _write_json(tareas_file(proyecto_id), {"tareas": tareas, "contador_id": contador_id})


# ================= UTILIDADES =================

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

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    users = load_usuarios()["usuarios"]
    return next((u for u in users if u["id"] == uid), None)

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

def user_can_access_proyecto(user, proyecto_id: int) -> bool:
    if user["rol"] == "superadmin":
        return True
    proyectos = load_proyectos()["proyectos"]
    p = next((x for x in proyectos if x["id"] == int(proyecto_id)), None)
    if not p:
        return False
    return p["empresa_id"] == user.get("empresa_id")

def require_project_access(f):
    @wraps(f)
    def wrapper(proyecto_id, *args, **kwargs):
        u = current_user()
        if not u:
            return redirect(url_for("login"))
        if not user_can_access_proyecto(u, int(proyecto_id)):
            abort(403)
        return f(proyecto_id, *args, **kwargs)
    return wrapper


# ================= LÓGICA DE TAREAS (por proyecto) =================

def agregar_tarea(proyecto_id, texto, responsable, centro, plazo, observacion, recursos, asignado_a_user_id=None):
    tareas, contador_id = load_tareas(proyecto_id)
    tarea = {
        'id': contador_id,
        'texto': texto.strip(),
        'situacion': 'Sin Ejecutar',
        'responsable': responsable.strip(),
        'centro_responsabilidad': centro.strip(),
        'plazo': plazo.strip(),
        'observacion': observacion.strip(),
        'recursos': recursos.strip(),
        'documentos': [],
        'asignado_a_user_id': asignado_a_user_id
    }
    tareas.append(tarea)
    contador_id += 1
    save_tareas(proyecto_id, tareas, contador_id)
    return tarea

def obtener_tarea_por_id(proyecto_id, tid):
    tareas, _ = load_tareas(proyecto_id)
    return next((t for t in tareas if t["id"] == tid), None)

def cambiar_estado(proyecto_id, tid, estado, user):
    # Permisos: solo Supervisor (o superadmin) puede poner "Validada"
    if estado == "Validada" and user["rol"] not in ("supervisor", "superadmin"):
        return False
    tareas, contador_id = load_tareas(proyecto_id)
    for t in tareas:
        if t['id'] == tid:
            if estado in ESTADOS:
                t['situacion'] = estado
                save_tareas(proyecto_id, tareas, contador_id)
                return True
    return False

def actualizar_tarea(proyecto_id, tid, responsable=None, centro=None, plazo=None, observacion=None, recursos=None, user=None):
    tareas, contador_id = load_tareas(proyecto_id)
    for t in tareas:
        if t['id'] == tid:
            # Si quieres que el ejecutor solo edite “sus” tareas, descomenta:
            # if user and user["rol"] == "ejecutor" and t.get("asignado_a_user_id") not in (None, user["id"]):
            #     return False

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
        if t['id'] == tid:
            if filename not in t['documentos']:
                t['documentos'].append(filename)
                save_tareas(proyecto_id, tareas, contador_id)
                return True
    return False

# ================= ESTADÍSTICAS (idénticas, pero por proyecto) =================

def obtener_estadisticas(tareas_filtradas):
    hoy = datetime.now().date()

    por_estado = {estado: 0 for estado in ESTADOS}
    for t in tareas_filtradas:
        estado = t.get('situacion', 'Sin Ejecutar')
        if estado in por_estado:
            por_estado[estado] += 1

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
                elif plazo_date >= hoy:
                    por_vencer += 1
            except:
                sin_plazo += 1
        else:
            sin_plazo += 1

    completadas = por_estado.get("Completada", 0)
    validadas = por_estado.get("Validada", 0)

    return {
        'total': len(tareas_filtradas),
        'por_estado': por_estado,
        'por_responsable': por_responsable,
        'por_centro': por_centro,
        'vencidas': vencidas,
        'por_vencer': por_vencer,
        'sin_plazo': sin_plazo,
        'completadas': completadas,
        'validadas': validadas
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
            tareas_filtradas = [t for t in tareas_filtradas if not t.get('plazo') or t.get('plazo') == '']

    return tareas_filtradas


# ================= ALERTAS (por proyecto: opcional luego) =================
# Puedes mantener tu scheduler, pero en multiempresa se suele programar por empresa/proyecto.
# Lo dejo apagado para no generar ruido al desplegar.

# ================= SEED: crear superadmin si no existe =================

def ensure_superadmin():
    data = load_usuarios()
    users = data["usuarios"]
    if any(u.get("rol") == "superadmin" for u in users):
        return
    # Crea superadmin por defecto (cambia credenciales después)
    uid = _next_id(users)
    users.append({
        "id": uid,
        "nombre": "Super Admin",
        "correo": "admin@tuapp.cl",
        "password_hash": generate_password_hash("Admin123!"),
        "rol": "superadmin",
        "empresa_id": None
    })
    data["usuarios"] = users
    save_usuarios(data)
    print("✅ Superadmin creado: admin@tuapp.cl / Admin123! (cámbialo)")

def crear_empresa_con_proyecto_y_roles(nombre_empresa, nombre_proyecto, correo_supervisor, pass_supervisor, correo_ejecutor, pass_ejecutor, licencia_max_usuarios=5, licencia_max_proyectos=1):
    # Empresa
    edata = load_empresas()
    empresas = edata["empresas"]
    empresa_id = _next_id(empresas)
    empresas.append({
        "id": empresa_id,
        "nombre": nombre_empresa,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d"),
        "licencia_max_usuarios": licencia_max_usuarios,
        "licencia_max_proyectos": licencia_max_proyectos
    })
    edata["empresas"] = empresas
    save_empresas(edata)

    # Proyecto inicial
    pdata = load_proyectos()
    proyectos = pdata["proyectos"]
    proyecto_id = _next_id(proyectos)
    proyectos.append({
        "id": proyecto_id,
        "nombre": nombre_proyecto,
        "empresa_id": empresa_id,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d")
    })
    pdata["proyectos"] = proyectos
    save_proyectos(pdata)

    # Usuarios (supervisor + ejecutor)
    udata = load_usuarios()
    users = udata["usuarios"]

    # Validación de correos únicos
    if any(u["correo"].lower() == correo_supervisor.lower() for u in users):
        raise ValueError("Correo de supervisor ya existe")
    if any(u["correo"].lower() == correo_ejecutor.lower() for u in users):
        raise ValueError("Correo de ejecutor ya existe")

    supervisor_id = _next_id(users)
    users.append({
        "id": supervisor_id,
        "nombre": "Supervisor",
        "correo": correo_supervisor,
        "password_hash": generate_password_hash(pass_supervisor),
        "rol": "supervisor",
        "empresa_id": empresa_id
    })

    ejecutor_id = _next_id(users)
    users.append({
        "id": ejecutor_id,
        "nombre": "Ejecutor",
        "correo": correo_ejecutor,
        "password_hash": generate_password_hash(pass_ejecutor),
        "rol": "ejecutor",
        "empresa_id": empresa_id
    })

    udata["usuarios"] = users
    save_usuarios(udata)

    # Inicializa archivo de tareas del proyecto
    save_tareas(proyecto_id, [], 1)

    return empresa_id, proyecto_id


# ================= AUTH ROUTES =================

@app.route("/login", methods=["GET", "POST"])
@no_cache
def login():
    ensure_superadmin()
    if request.method == "POST":
        correo = (request.form.get("correo") or "").strip().lower()
        password = request.form.get("password") or ""

        users = load_usuarios()["usuarios"]
        u = next((x for x in users if x["correo"].lower() == correo), None)
        if not u or not check_password_hash(u["password_hash"], password):
            flash("Credenciales inválidas", "error")
            return render_template("login.html")

        session["user_id"] = u["id"]

        # Redirección según rol
        if u["rol"] == "superadmin":
            return redirect(url_for("sa_dashboard"))
        else:
            return redirect(url_for("empresa_dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================= SUPERADMIN: EMPRESAS/PROYECTOS/USUARIOS =================

@app.route("/sa")
@login_required
@require_roles("superadmin")
def sa_dashboard():
    empresas = load_empresas()["empresas"]
    proyectos = load_proyectos()["proyectos"]
    usuarios = load_usuarios()["usuarios"]

    # Resumen simple por empresa
    resumen = []
    for e in empresas:
        proys = [p for p in proyectos if p["empresa_id"] == e["id"]]
        users = [u for u in usuarios if u.get("empresa_id") == e["id"]]
        resumen.append({
            "empresa": e,
            "n_proyectos": len(proys),
            "n_usuarios": len(users)
        })
    return render_template("sa_dashboard.html", resumen=resumen, empresas=empresas)

@app.route("/sa/empresa/nueva", methods=["GET", "POST"])
@login_required
@require_roles("superadmin")
def sa_empresa_nueva():
    if request.method == "POST":
        nombre_empresa = (request.form.get("nombre_empresa") or "").strip()
        nombre_proyecto = (request.form.get("nombre_proyecto") or "Proyecto 1").strip()

        correo_supervisor = (request.form.get("correo_supervisor") or "").strip()
        pass_supervisor = request.form.get("pass_supervisor") or ""

        correo_ejecutor = (request.form.get("correo_ejecutor") or "").strip()
        pass_ejecutor = request.form.get("pass_ejecutor") or ""

        licencia_max_usuarios = int(request.form.get("licencia_max_usuarios") or 5)
        licencia_max_proyectos = int(request.form.get("licencia_max_proyectos") or 1)

        if not (nombre_empresa and correo_supervisor and pass_supervisor and correo_ejecutor and pass_ejecutor):
            flash("Faltan datos para crear empresa/proyecto/usuarios", "error")
            return render_template("sa_empresa_nueva.html")

        try:
            crear_empresa_con_proyecto_y_roles(
                nombre_empresa, nombre_proyecto,
                correo_supervisor, pass_supervisor,
                correo_ejecutor, pass_ejecutor,
                licencia_max_usuarios, licencia_max_proyectos
            )
            flash("Empresa creada con proyecto y usuarios (Supervisor/Ejecutor).", "ok")
            return redirect(url_for("sa_dashboard"))
        except Exception as e:
            flash(str(e), "error")
            return render_template("sa_empresa_nueva.html")

    return render_template("sa_empresa_nueva.html")


# ================= EMPRESA DASHBOARD (SUPERVISOR/EJECUTOR) =================

@app.route("/empresa")
@login_required
@require_roles("supervisor", "ejecutor")
@no_cache
def empresa_dashboard():
    u = current_user()
    empresas = load_empresas()["empresas"]
    proyectos = load_proyectos()["proyectos"]

    empresa = next((e for e in empresas if e["id"] == u["empresa_id"]), None)
    proys = [p for p in proyectos if p["empresa_id"] == u["empresa_id"]]

    # Avance por proyecto (usando tus mismas estadísticas)
    avances = []
    for p in proys:
        tareas, _ = load_tareas(p["id"])
        est = obtener_estadisticas(tareas)
        avances.append({
            "proyecto": p,
            "estadisticas": est
        })

    return render_template("empresa_dashboard.html", empresa=empresa, avances=avances, user=u)


# ================= PROYECTO: PLANIFICADOR / TABLERO / INFORME =================

@app.route("/p/<int:proyecto_id>/")
@login_required
@require_project_access
@no_cache
def proyecto_index(proyecto_id):
    u = current_user()
    tareas, _ = load_tareas(proyecto_id)

    # Si quieres que ejecutor vea solo tareas asignadas:
    # if u["rol"] == "ejecutor":
    #     tareas = [t for t in tareas if t.get("asignado_a_user_id") in (None, u["id"])]

    return render_template("index.html", tareas=tareas, estados=ESTADOS, proyecto_id=proyecto_id, user=u)

@app.route("/p/<int:proyecto_id>/agregar", methods=["POST"])
@login_required
@require_project_access
def proyecto_agregar(proyecto_id):
    u = current_user()
    texto = (request.form.get('texto', '') or '').strip()
    if texto:
        # Asignación simple: si llega un user_id (opcional), si no, None.
        asignado_a = request.form.get("asignado_a_user_id")
        asignado_a = int(asignado_a) if asignado_a else None

        agregar_tarea(
            proyecto_id,
            texto,
            request.form.get('responsable', ''),
            request.form.get('centro_responsabilidad', ''),
            request.form.get('plazo', ''),
            request.form.get('observacion', ''),
            request.form.get('recursos', ''),
            asignado_a_user_id=asignado_a
        )
    return redirect(url_for('proyecto_index', proyecto_id=proyecto_id))

@app.route("/p/<int:proyecto_id>/cambiar_estado/<int:tid>", methods=["POST"])
@login_required
@require_project_access
def proyecto_cambiar_estado(proyecto_id, tid):
    u = current_user()
    estado = request.form.get('situacion', '')
    cambiar_estado(proyecto_id, tid, estado, u)
    return redirect(url_for('proyecto_index', proyecto_id=proyecto_id))

@app.route("/p/<int:proyecto_id>/actualizar_tarea/<int:tid>", methods=["POST"])
@login_required
@require_project_access
def proyecto_actualizar_tarea(proyecto_id, tid):
    u = current_user()
    actualizar_tarea(
        proyecto_id,
        tid,
        request.form.get('responsable'),
        request.form.get('centro_responsabilidad'),
        request.form.get('plazo'),
        request.form.get('observacion'),
        request.form.get('recursos'),
        user=u
    )
    return redirect(url_for('proyecto_index', proyecto_id=proyecto_id))

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
    return redirect(url_for('proyecto_index', proyecto_id=proyecto_id))

@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/p/<int:proyecto_id>/tablero")
@login_required
@require_project_access
@no_cache
def proyecto_tablero(proyecto_id):
    u = current_user()
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
        'tablero.html',
        tareas=tareas_filtradas,
        estadisticas=estadisticas,
        estadisticas_totales=estadisticas_totales,
        estados=ESTADOS,
        responsables=responsables_unicos,
        centros=centros_unicos,
        filtros={'centro': centro_filtro,'responsable': responsable_filtro,'estado': estado_filtro,'plazo': plazo_filtro},
        proyecto_id=proyecto_id,
        user=u
    )

@app.route("/p/<int:proyecto_id>/api/estadisticas")
@login_required
@require_project_access
def proyecto_api_estadisticas(proyecto_id):
    tareas, _ = load_tareas(proyecto_id)
    return jsonify(obtener_estadisticas(tareas))

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
        'informe.html',
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


# ================= ROOT =================
@app.route("/")
def root():
    u = current_user()
    if not u:
        return redirect(url_for("login"))
    if u["rol"] == "superadmin":
        return redirect(url_for("sa_dashboard"))
    return redirect(url_for("empresa_dashboard"))


if __name__ == "__main__":
    ensure_superadmin()
    app.run(debug=True, host="0.0.0.0", port=5000)
