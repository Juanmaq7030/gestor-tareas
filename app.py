from flask import (
    Flask, render_template, request, redirect, url_for,
    send_from_directory, make_response, session, flash, abort
)
import os
import time
import json
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

# ================= APP =================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CAMBIA-ESTO-EN-RENDER")

# ================= RUTAS ABSOLUTAS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# (mantenemos DATA_DIR solo por compatibilidad/migración)
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
os.makedirs(DATA_DIR, exist_ok=True)

# ================= CONFIGURACIÓN =================
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'txt'}
ESTADOS = ['Sin Ejecutar', 'En Ejecución', 'Pendiente de', 'Completada', 'Validada']

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ================= DATABASE (PostgreSQL / Render) =================
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# fallback local si no hay DATABASE_URL
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "local.db")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELOS =================
class Company(db.Model):
    __tablename__ = "companies"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    activa = db.Column(db.Boolean, default=True)

    licencia_max_usuarios = db.Column(db.Integer, default=5)
    licencia_max_proyectos = db.Column(db.Integer, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    nombre = db.Column(db.String(200), nullable=False)
    terminado = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_termino = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("empresa_id", "nombre", name="uq_project_empresa_nombre"),
    )

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)

    # superadmin => empresa_id NULL
    empresa_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True, index=True)

    nombre = db.Column(db.String(200), nullable=False)
    correo = db.Column(db.String(200), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(50), nullable=False)  # superadmin/supervisor/ejecutor
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)

    empresa_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)

    texto = db.Column(db.String(500), nullable=False)
    situacion = db.Column(db.String(50), default="Sin Ejecutar")  # usa tus ESTADOS

    responsable = db.Column(db.String(200), default="")
    centro_responsabilidad = db.Column(db.String(200), default="")
    plazo = db.Column(db.String(20), default="")  # guardas YYYY-MM-DD como string (para no romper tu lógica)
    observacion = db.Column(db.Text, default="")
    recursos = db.Column(db.Text, default="")

    documentos = db.Column(db.JSON, default=list)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Crear tablas automáticamente (para evitar “tabla no existe” en deploy)
with app.app_context():
    db.create_all()

# ================= HELPERS =================
def to_int(v, default=None):
    if v is None:
        return default
    try:
        if isinstance(v, bool):
            return default
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).strip()
        if s == "":
            return default
        return int(s)
    except Exception:
        return default

def _bool(v):
    return str(v).strip().lower() in ("1", "true", "on", "yes", "si", "sí")

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
    u = User.query.get(int(uid))
    if not u or not u.activo:
        return None
    # devolvemos dict para mantener compatibilidad con tu código
    return {
        "id": u.id,
        "nombre": u.nombre,
        "correo": u.correo,
        "rol": u.rol,
        "empresa_id": u.empresa_id
    }

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
    return to_int(session.get("project_id"), None)

def set_active_project(pid: int):
    session["project_id"] = int(pid)

def clear_active_project():
    session.pop("project_id", None)

def _get_project(proyecto_id: int):
    p = Project.query.get(int(proyecto_id))
    if not p:
        return None
    return {
        "id": p.id,
        "empresa_id": p.empresa_id,
        "nombre": p.nombre,
        "terminado": p.terminado
    }

def user_can_access_project(u, proyecto_id: int) -> bool:
    if not u:
        return False
    if u.get("rol") == "superadmin":
        return True

    p = Project.query.get(int(proyecto_id))
    if not p:
        return False

    if p.terminado:
        return False

    return int(p.empresa_id) == int(u.get("empresa_id") or 0)

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

# ================= TAREAS (DB) =================
def task_to_dict(t: Task):
    return {
        "id": t.id,
        "texto": t.texto,
        "situacion": t.situacion,
        "responsable": t.responsable or "",
        "centro_responsabilidad": t.centro_responsabilidad or "",
        "plazo": t.plazo or "",
        "observacion": t.observacion or "",
        "recursos": t.recursos or "",
        "documentos": t.documentos or []
    }

def load_tareas(proyecto_id: int):
    # contador_id se mantiene por compatibilidad, pero aquí no se usa para ID
    tareas_q = Task.query.filter_by(proyecto_id=int(proyecto_id)).order_by(Task.id.asc()).all()
    tareas = [task_to_dict(t) for t in tareas_q]
    contador_id = (tareas[-1]["id"] + 1) if tareas else 1
    return tareas, contador_id

def agregar_tarea(proyecto_id, texto, responsable, centro, plazo, observacion, recursos):
    p = Project.query.get(int(proyecto_id))
    if not p:
        raise ValueError("Proyecto no existe")

    t = Task(
        empresa_id=p.empresa_id,
        proyecto_id=p.id,
        texto=(texto or "").strip(),
        situacion="Sin Ejecutar",
        responsable=(responsable or "").strip(),
        centro_responsabilidad=(centro or "").strip(),
        plazo=(plazo or "").strip(),
        observacion=(observacion or "").strip(),
        recursos=(recursos or "").strip(),
        documentos=[]
    )
    db.session.add(t)
    db.session.commit()
    return task_to_dict(t)

def cambiar_estado(proyecto_id, tid, estado, user):
    if estado == "Validada" and user.get("rol") not in ("supervisor", "superadmin"):
        return False
    if estado not in ESTADOS:
        return False

    t = Task.query.filter_by(proyecto_id=int(proyecto_id), id=int(tid)).first()
    if not t:
        return False

    t.situacion = estado
    db.session.commit()
    return True

def actualizar_tarea(proyecto_id, tid, responsable=None, centro=None, plazo=None, observacion=None, recursos=None):
    t = Task.query.filter_by(proyecto_id=int(proyecto_id), id=int(tid)).first()
    if not t:
        return False

    if responsable is not None:
        t.responsable = (responsable or "").strip()
    if centro is not None:
        t.centro_responsabilidad = (centro or "").strip()
    if plazo is not None:
        t.plazo = (plazo or "").strip()
    if observacion is not None:
        t.observacion = (observacion or "").strip()
    if recursos is not None:
        t.recursos = (recursos or "").strip()

    db.session.commit()
    return True

def agregar_documento(proyecto_id, tid, filename):
    t = Task.query.filter_by(proyecto_id=int(proyecto_id), id=int(tid)).first()
    if not t:
        return False
    docs = t.documentos or []
    if filename not in docs:
        docs.append(filename)
        t.documentos = docs
        db.session.commit()
    return True

# ================= ESTADÍSTICAS (igual que tu lógica) =================
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
            except Exception:
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
    tareas_filtradas = list(tareas)
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
                    except Exception:
                        pass
            tareas_filtradas = tmp
        elif plazo == 'por_vencer':
            tmp = []
            for t in tareas_filtradas:
                if t.get('plazo'):
                    try:
                        if datetime.strptime(t.get('plazo'), '%Y-%m-%d').date() >= hoy:
                            tmp.append(t)
                    except Exception:
                        pass
            tareas_filtradas = tmp
        elif plazo == 'sin_plazo':
            tareas_filtradas = [t for t in tareas_filtradas if not t.get('plazo')]

    return tareas_filtradas

# ================= SEED/RESET SUPERADMIN (DB) =================
def ensure_superadmin():
    admin_email = (os.getenv("ADMIN_EMAIL", "admin@tuapp.cl") or "admin@tuapp.cl").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")
    force_reset = os.getenv("ADMIN_FORCE_RESET", "0") == "1"

    u = User.query.filter_by(correo=admin_email).first()
    if u:
        # asegurar rol
        if u.rol != "superadmin" or u.empresa_id is not None:
            u.rol = "superadmin"
            u.empresa_id = None
        if force_reset:
            u.password_hash = generate_password_hash(admin_password)
        db.session.commit()
        print(f"✅ Superadmin OK (existente): {admin_email} | reset={force_reset}")
        return

    # si hay otro superadmin, opcionalmente resetea
    existing_super = User.query.filter_by(rol="superadmin").first()
    if existing_super:
        if force_reset:
            existing_super.correo = admin_email
            existing_super.password_hash = generate_password_hash(admin_password)
            existing_super.empresa_id = None
            existing_super.rol = "superadmin"
            db.session.commit()
            print(f"✅ Superadmin actualizado: {admin_email}")
        else:
            print("ℹ️ Ya existe un superadmin. Usa ADMIN_FORCE_RESET=1 si quieres resetearlo.")
        return

    u = User(
        nombre="Super Admin",
        correo=admin_email,
        password_hash=generate_password_hash(admin_password),
        rol="superadmin",
        empresa_id=None,
        activo=True
    )
    db.session.add(u)
    db.session.commit()
    print(f"✅ Superadmin creado: {admin_email} (cámbialo)")

# ================= CREACIÓN EMPRESA+PROYECTO+ROLES (DB) =================
def crear_empresa_con_proyecto_y_roles(nombre_empresa, nombre_proyecto, correo_sup, pass_sup, correo_eje, pass_eje, max_users=5, max_proys=1):
    correo_sup = correo_sup.strip().lower()
    correo_eje = correo_eje.strip().lower()

    if User.query.filter_by(correo=correo_sup).first():
        raise ValueError("Correo supervisor ya existe")
    if User.query.filter_by(correo=correo_eje).first():
        raise ValueError("Correo ejecutor ya existe")

    empresa = Company(
        nombre=nombre_empresa,
        activa=True,
        licencia_max_usuarios=int(max_users),
        licencia_max_proyectos=int(max_proys),
    )
    db.session.add(empresa)
    db.session.flush()  # para obtener empresa.id sin commit aún

    proyecto = Project(
        empresa_id=empresa.id,
        nombre=nombre_proyecto,
        terminado=False
    )
    db.session.add(proyecto)
    db.session.flush()

    sup = User(
        nombre="Supervisor",
        correo=correo_sup,
        password_hash=generate_password_hash(pass_sup),
        rol="supervisor",
        empresa_id=empresa.id
    )
    eje = User(
        nombre="Ejecutor",
        correo=correo_eje,
        password_hash=generate_password_hash(pass_eje),
        rol="ejecutor",
        empresa_id=empresa.id
    )

    db.session.add_all([sup, eje])
    db.session.commit()

    return empresa.id, proyecto.id

# ================= RUTAS AUTH =================
@app.route("/login", methods=["GET", "POST"])
@no_cache
def login():
    if request.method == "POST":
        ident = (request.form.get("correo") or request.form.get("username") or request.form.get("usuario") or "").strip().lower()
        password = request.form.get("password") or ""

        u = User.query.filter_by(correo=ident).first()

        if (not u) or (not u.activo) or (not check_password_hash(u.password_hash, password)):
            flash("Credenciales inválidas", "error")
            return render_template("login.html"), 200

        session.clear()
        session["user_id"] = u.id
        session["nombre"] = u.nombre or u.correo or "Usuario"
        session["rol"] = u.rol
        session["empresa_id"] = u.empresa_id
        clear_active_project()

        if u.rol == "superadmin":
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
    empresas = Company.query.order_by(Company.nombre.asc()).all()
    resumen = []
    for e in empresas:
        n_proys = Project.query.filter_by(empresa_id=e.id).count()
        n_users = User.query.filter_by(empresa_id=e.id).count()
        resumen.append({"empresa": {"id": e.id, "nombre": e.nombre}, "n_proyectos": n_proys, "n_usuarios": n_users})
    return render_template("admin_dashboard.html", resumen=resumen)

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

# ================= SUPERADMIN: CONFIG PANEL (CRUD) - DB =================
@app.route("/sa/config")
@login_required
@require_roles("superadmin")
@no_cache
def sa_config():
    empresa_id = request.args.get("empresa_id", type=int)

    empresas = Company.query.order_by(Company.nombre.asc()).all()
    empresa_sel = None

    if empresas:
        if empresa_id:
            empresa_sel = Company.query.get(empresa_id)
        if not empresa_sel:
            empresa_sel = empresas[0]
            empresa_id = empresa_sel.id

    proyectos_sel = []
    usuarios_sel = []
    if empresa_sel:
        proyectos_sel = Project.query.filter_by(empresa_id=empresa_sel.id).order_by(Project.nombre.asc()).all()
        usuarios_sel = User.query.filter_by(empresa_id=empresa_sel.id).order_by(User.correo.asc()).all()

        # pasamos a dicts para no romper templates
        proyectos_sel = [{
            "id": p.id, "empresa_id": p.empresa_id, "nombre": p.nombre,
            "terminado": p.terminado
        } for p in proyectos_sel]

        usuarios_sel = [{
            "id": uu.id, "empresa_id": uu.empresa_id, "nombre": uu.nombre,
            "correo": uu.correo, "rol": uu.rol
        } for uu in usuarios_sel]

    empresas_out = [{
        "id": e.id, "nombre": e.nombre, "activa": e.activa,
        "licencia_max_usuarios": e.licencia_max_usuarios,
        "licencia_max_proyectos": e.licencia_max_proyectos
    } for e in empresas]

    empresa_sel_out = None
    if empresa_sel:
        empresa_sel_out = {
            "id": empresa_sel.id, "nombre": empresa_sel.nombre, "activa": empresa_sel.activa,
            "licencia_max_usuarios": empresa_sel.licencia_max_usuarios,
            "licencia_max_proyectos": empresa_sel.licencia_max_proyectos
        }

    return render_template(
        "sa_config.html",
        data_dir=DATA_DIR,
        empresas=empresas_out,
        empresa_sel=empresa_sel_out,
        proyectos_sel=proyectos_sel,
        usuarios_sel=usuarios_sel
    )

@app.route("/sa/empresa/<int:empresa_id>/editar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_empresa_editar(empresa_id):
    e = Company.query.get(empresa_id)
    if not e:
        abort(404)

    nombre = (request.form.get("nombre") or "").strip()
    activa = _bool(request.form.get("activa"))

    if nombre:
        e.nombre = nombre
    e.activa = activa
    db.session.commit()

    flash("Empresa actualizada.", "ok")
    return redirect(url_for("sa_config", empresa_id=empresa_id))

@app.route("/sa/empresa/<int:empresa_id>/eliminar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_empresa_eliminar(empresa_id):
    # elimina en cascada manual (proyectos, usuarios, tareas)
    proys = Project.query.filter_by(empresa_id=empresa_id).all()
    proy_ids = [p.id for p in proys]

    Task.query.filter(Task.proyecto_id.in_(proy_ids)).delete(synchronize_session=False)
    User.query.filter_by(empresa_id=empresa_id).delete(synchronize_session=False)
    Project.query.filter_by(empresa_id=empresa_id).delete(synchronize_session=False)

    Company.query.filter_by(id=empresa_id).delete(synchronize_session=False)
    db.session.commit()

    flash("Empresa eliminada (con proyectos/usuarios/tareas asociados).", "ok")
    return redirect(url_for("sa_config"))

@app.route("/sa/proyecto/nuevo-simple", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_proyecto_nuevo_simple():
    empresa_id = (request.form.get("empresa_id") or "").strip()
    nombre = (request.form.get("nombre_proyecto") or "").strip()

    try:
        empresa_id_int = int(empresa_id)
    except Exception:
        flash("Empresa inválida.", "error")
        return redirect(url_for("sa_config"))

    if not nombre:
        flash("Debes ingresar un nombre de proyecto.", "error")
        return redirect(url_for("sa_config", empresa_id=empresa_id_int))

    empresa = Company.query.get(empresa_id_int)
    if not empresa:
        flash("Empresa no encontrada.", "error")
        return redirect(url_for("sa_config"))

    n_actual = Project.query.filter_by(empresa_id=empresa_id_int).count()
    max_proys = int(empresa.licencia_max_proyectos or 1)
    if n_actual >= max_proys:
        flash(f"Límite de proyectos alcanzado ({n_actual}/{max_proys}).", "error")
        return redirect(url_for("sa_config", empresa_id=empresa_id_int))

    p = Project(empresa_id=empresa_id_int, nombre=nombre, terminado=False)
    db.session.add(p)
    db.session.commit()

    flash("Proyecto creado ✅", "ok")
    return redirect(url_for("sa_config", empresa_id=empresa_id_int))

@app.route("/sa/proyecto/<int:proyecto_id>/editar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_proyecto_editar(proyecto_id):
    p = Project.query.get(proyecto_id)
    if not p:
        abort(404)

    nombre = (request.form.get("nombre") or "").strip()
    terminado = _bool(request.form.get("terminado"))

    if nombre:
        p.nombre = nombre

    if terminado:
        p.terminado = True
        p.fecha_termino = datetime.utcnow()
    else:
        p.terminado = False
        p.fecha_termino = None

    db.session.commit()
    flash("Proyecto actualizado.", "ok")
    return redirect(url_for("sa_config", empresa_id=p.empresa_id))

@app.route("/sa/proyecto/<int:proyecto_id>/eliminar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_proyecto_eliminar_post(proyecto_id):
    p = Project.query.get(proyecto_id)
    if not p:
        abort(404)

    empresa_id = p.empresa_id

    Task.query.filter_by(proyecto_id=proyecto_id).delete(synchronize_session=False)
    Project.query.filter_by(id=proyecto_id).delete(synchronize_session=False)
    db.session.commit()

    flash("Proyecto eliminado (y tareas asociadas).", "ok")
    return redirect(url_for("sa_config", empresa_id=empresa_id))

@app.route("/sa/usuario/nuevo-simple", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_usuario_nuevo_simple():
    empresa_id = (request.form.get("empresa_id") or "").strip()
    nombre = (request.form.get("nombre") or "").strip()
    correo = (request.form.get("correo") or "").strip().lower()
    password = request.form.get("password") or ""
    rol = (request.form.get("rol") or "").strip().lower()

    try:
        empresa_id_int = int(empresa_id)
    except Exception:
        flash("Empresa inválida.", "error")
        return redirect(url_for("sa_config"))

    if not (nombre and correo and password and rol):
        flash("Faltan datos para crear usuario.", "error")
        return redirect(url_for("sa_config", empresa_id=empresa_id_int))

    if rol not in ("supervisor", "ejecutor"):
        flash("Rol inválido (solo supervisor/ejecutor).", "error")
        return redirect(url_for("sa_config", empresa_id=empresa_id_int))

    if len(password) < 6:
        flash("La contraseña debe tener al menos 6 caracteres.", "error")
        return redirect(url_for("sa_config", empresa_id=empresa_id_int))

    empresa = Company.query.get(empresa_id_int)
    if not empresa:
        flash("Empresa no encontrada.", "error")
        return redirect(url_for("sa_config", empresa_id=empresa_id_int))

    n_users = User.query.filter_by(empresa_id=empresa_id_int).count()
    max_users = int(empresa.licencia_max_usuarios or 5)
    if n_users >= max_users:
        flash(f"Límite de usuarios alcanzado ({n_users}/{max_users}).", "error")
        return redirect(url_for("sa_config", empresa_id=empresa_id_int))

    if User.query.filter_by(correo=correo).first():
        flash("Ese correo ya existe en otro usuario.", "error")
        return redirect(url_for("sa_config", empresa_id=empresa_id_int))

    u = User(
        nombre=nombre,
        correo=correo,
        password_hash=generate_password_hash(password),
        rol=rol,
        empresa_id=empresa_id_int
    )
    db.session.add(u)
    db.session.commit()

    flash("Usuario creado ✅", "ok")
    return redirect(url_for("sa_config", empresa_id=empresa_id_int))

@app.route("/sa/usuario/<int:user_id>/editar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_usuario_editar(user_id):
    u = User.query.get(user_id)
    if not u:
        abort(404)

    nombre = (request.form.get("nombre") or "").strip()
    correo = (request.form.get("correo") or "").strip().lower()
    rol = (request.form.get("rol") or "").strip().lower()

    if nombre:
        u.nombre = nombre

    if correo and correo != u.correo:
        if User.query.filter(User.correo == correo, User.id != user_id).first():
            flash("Ese correo ya existe en otro usuario.", "error")
            return redirect(url_for("sa_config", empresa_id=u.empresa_id))
        u.correo = correo

    if rol in ("superadmin", "supervisor", "ejecutor"):
        u.rol = rol
        if rol == "superadmin":
            u.empresa_id = None

    db.session.commit()
    flash("Usuario actualizado.", "ok")
    return redirect(url_for("sa_config", empresa_id=u.empresa_id))

@app.route("/sa/usuario/<int:user_id>/reset-password", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_usuario_reset_password(user_id):
    u = User.query.get(user_id)
    if not u:
        abort(404)

    new_pass = request.form.get("new_password") or ""
    if len(new_pass) < 6:
        flash("La nueva contraseña debe tener al menos 6 caracteres.", "error")
        return redirect(url_for("sa_config", empresa_id=u.empresa_id))

    u.password_hash = generate_password_hash(new_pass)
    db.session.commit()

    flash("Contraseña reseteada ✅", "ok")
    return redirect(url_for("sa_config", empresa_id=u.empresa_id))

@app.route("/sa/usuario/<int:user_id>/eliminar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_usuario_eliminar_post(user_id):
    u = User.query.get(user_id)
    empresa_id = u.empresa_id if u else None

    User.query.filter_by(id=user_id).delete(synchronize_session=False)
    db.session.commit()

    flash("Usuario eliminado.", "ok")
    return redirect(url_for("sa_config", empresa_id=empresa_id))

# ================= DASHBOARD EMPRESA =================
@app.route("/empresa")
@login_required
@require_roles("supervisor", "ejecutor")
@no_cache
def empresa_dashboard():
    u = current_user()
    empresa = Company.query.get(int(u.get("empresa_id")))

    proys = Project.query.filter_by(empresa_id=int(u.get("empresa_id")), terminado=False).order_by(Project.nombre.asc()).all()

    avances = []
    for p in proys:
        tareas, _ = load_tareas(p.id)
        est = obtener_estadisticas(tareas)
        total = est["total"]
        comp = est["por_estado"].get("Completada", 0)
        val = est["por_estado"].get("Validada", 0)
        avance = round(((comp + val) / total) * 100, 1) if total else 0
        avances.append({
            "proyecto": {"id": p.id, "empresa_id": p.empresa_id, "nombre": p.nombre, "terminado": p.terminado},
            "estadisticas": est,
            "avance_pct": avance
        })

    empresa_out = {"id": empresa.id, "nombre": empresa.nombre} if empresa else None
    return render_template("empresa_dashboard.html", empresa=empresa_out, avances=avances, user=u)

@app.route("/empresa/ir/<int:proyecto_id>")
@login_required
@require_roles("supervisor", "ejecutor")
def empresa_ir(proyecto_id):
    u = current_user()
    if not user_can_access_project(u, proyecto_id):
        abort(403)

    set_active_project(proyecto_id)
    if u.get("rol") == "supervisor":
        return redirect(url_for("proyecto_tablero", proyecto_id=proyecto_id))
    return redirect(url_for("proyecto_index", proyecto_id=proyecto_id))

# ================= SELECCIONAR PROYECTO =================
@app.route("/seleccionar-proyecto", methods=["GET"])
@login_required
@require_roles("supervisor", "ejecutor")
@no_cache
def seleccionar_proyecto():
    u = current_user()
    proys = Project.query.filter_by(empresa_id=int(u.get("empresa_id")), terminado=False).order_by(Project.nombre.asc()).all()

    if not proys:
        flash("Tu empresa no tiene proyectos activos. Pide al Superadmin que cree o reactive uno.", "error")
        return redirect(url_for("empresa_dashboard"))

    if len(proys) == 1:
        pid = proys[0].id
        set_active_project(pid)
        if u.get("rol") == "supervisor":
            return redirect(url_for("proyecto_tablero", proyecto_id=pid))
        return redirect(url_for("proyecto_index", proyecto_id=pid))

    proys_out = [{"id": p.id, "empresa_id": p.empresa_id, "nombre": p.nombre, "terminado": p.terminado} for p in proys]
    return render_template("seleccionar_proyecto.html", proyectos=proys_out, user=u)

# ================= PROYECTO: PLANIFICADOR =================
@app.route("/p/<int:proyecto_id>/")
@login_required
@require_project_access
@no_cache
def proyecto_index(proyecto_id):
    tareas, _ = load_tareas(proyecto_id)
    u = current_user()

    empresa = Company.query.get(int(u.get("empresa_id"))) if u.get("empresa_id") else None
    empresa_nombre = empresa.nombre if empresa else ""

    proys = Project.query.filter_by(empresa_id=int(u.get("empresa_id")), terminado=False).order_by(Project.nombre.asc()).all()
    proyectos_usuario = [{"id": p.id, "nombre": p.nombre} for p in proys]

    return render_template(
        "index.html",
        tareas=tareas,
        estados=ESTADOS,
        proyecto_id=proyecto_id,
        user=u,
        empresa_nombre=empresa_nombre,
        proyectos_usuario=proyectos_usuario
    )

@app.route("/p/<int:proyecto_id>/agregar", methods=["POST"])
@login_required
@require_project_access
def proyecto_agregar(proyecto_id):
    texto = (request.form.get('texto') or '').strip()
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

    u = current_user()
    empresa = Company.query.get(int(u.get("empresa_id"))) if u.get("empresa_id") else None
    empresa_nombre = empresa.nombre if empresa else ""

    proys = Project.query.filter_by(empresa_id=int(u.get("empresa_id")), terminado=False).order_by(Project.nombre.asc()).all()
    proyectos_usuario = [{"id": p.id, "nombre": p.nombre} for p in proys]

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
        user=u,
        empresa_nombre=empresa_nombre,
        proyectos_usuario=proyectos_usuario
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
        except Exception:
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

# ================= MIGRACIÓN (JSON -> DB) =================
# Úsalo UNA vez si quieres traer lo que ya tenías en /data/*.json
EMPRESAS_FILE = os.path.join(DATA_DIR, "empresas.json")
PROYECTOS_FILE = os.path.join(DATA_DIR, "proyectos.json")
USUARIOS_FILE = os.path.join(DATA_DIR, "usuarios.json")

def _read_json(path, default):
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

@app.route("/sa/migrate-json-to-db", methods=["POST"])
@login_required
@require_roles("superadmin")
def migrate_json_to_db():
    # seguridad: requiere flag
    if os.getenv("ALLOW_DB_MIGRATION", "0") != "1":
        abort(403)

    ed = _read_json(EMPRESAS_FILE, {"empresas": []})
    pd_ = _read_json(PROYECTOS_FILE, {"proyectos": []})
    ud = _read_json(USUARIOS_FILE, {"usuarios": []})

    empresas = ed.get("empresas", [])
    proyectos = pd_.get("proyectos", [])
    usuarios = ud.get("usuarios", [])

    # empresas
    for e in empresas:
        eid = to_int(e.get("id"))
        if not eid:
            continue
        exists = Company.query.get(eid)
        if not exists:
            db.session.add(Company(
                id=eid,
                nombre=(e.get("nombre") or "").strip() or f"Empresa {eid}",
                activa=bool(e.get("activa", True)),
                licencia_max_usuarios=to_int(e.get("licencia_max_usuarios"), 5) or 5,
                licencia_max_proyectos=to_int(e.get("licencia_max_proyectos"), 1) or 1,
            ))

    db.session.commit()

    # proyectos
    for p in proyectos:
        pid = to_int(p.get("id"))
        empid = to_int(p.get("empresa_id"))
        if not pid or not empid:
            continue
        exists = Project.query.get(pid)
        if not exists:
            db.session.add(Project(
                id=pid,
                empresa_id=empid,
                nombre=(p.get("nombre") or "").strip() or f"Proyecto {pid}",
                terminado=bool(p.get("terminado", False))
            ))

    db.session.commit()

    # usuarios
    for u in usuarios:
        correo = (u.get("correo") or "").strip().lower()
        if not correo:
            continue
        exists = User.query.filter_by(correo=correo).first()
        if not exists:
            db.session.add(User(
                id=to_int(u.get("id")),
                nombre=(u.get("nombre") or correo),
                correo=correo,
                password_hash=u.get("password_hash") or generate_password_hash("Temp123!"),
                rol=(u.get("rol") or "ejecutor"),
                empresa_id=u.get("empresa_id", None),
                activo=True
            ))

    db.session.commit()

    flash("Migración JSON -> DB completada ✅", "ok")
    return redirect(url_for("sa_dashboard"))

# ================= INIT =================
ensure_superadmin()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
