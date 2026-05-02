from flask import (
    Flask, render_template, request, redirect, url_for,
    send_from_directory, make_response, session, flash, abort
)
import os
import time
import json
import secrets
from urllib.parse import urlencode
import requests
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, text, inspect as sa_inspect

# ================= APP =================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CAMBIA-ESTO-EN-RENDER")

# ================= RUTAS ABSOLUTAS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Compatibilidad para migración desde JSON
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

    # Calendario externo (credenciales OAuth por empresa: Google u Outlook / Microsoft 365)
    calendar_provider = db.Column(db.String(20), default="none")  # none | google | microsoft
    calendar_oauth_client_id = db.Column(db.Text, nullable=True)
    calendar_oauth_client_secret = db.Column(db.Text, nullable=True)
    calendar_google_calendar_id = db.Column(db.String(500), default="primary")
    calendar_access_token = db.Column(db.Text, nullable=True)
    calendar_refresh_token = db.Column(db.Text, nullable=True)
    calendar_token_expires_at = db.Column(db.DateTime, nullable=True)
    calendar_microsoft_tenant = db.Column(db.String(120), default="common")


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
    empresa_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True, index=True)  # superadmin => NULL

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
    situacion = db.Column(db.String(50), default="Sin Ejecutar")

    responsable = db.Column(db.String(200), default="")
    centro_responsabilidad = db.Column(db.String(200), default="")
    plazo = db.Column(db.String(20), default="")  # YYYY-MM-DD
    observacion = db.Column(db.Text, default="")
    recursos = db.Column(db.Text, default="")

    documentos = db.Column(db.JSON, default=list)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Objective(db.Model):
    __tablename__ = "objectives"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)

    nombre = db.Column(db.String(250), nullable=False)
    descripcion = db.Column(db.Text, default="")
    centros = db.Column(db.JSON, default=list)
    responsable = db.Column(db.String(200), default="")
    estado = db.Column(db.String(50), default="Activo")
    fecha_inicio = db.Column(db.String(20), default="")
    fecha_fin = db.Column(db.String(20), default="")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("proyecto_id", "nombre", name="uq_objective_project_nombre"),
    )


class KPI(db.Model):
    __tablename__ = "kpis"

    id = db.Column(db.Integer, primary_key=True)
    objetivo_id = db.Column(db.Integer, db.ForeignKey("objectives.id"), nullable=False, index=True)

    nombre = db.Column(db.String(250), nullable=False)
    unidad = db.Column(db.String(50), default="")
    meta = db.Column(db.Float, nullable=True)
    modo = db.Column(db.String(20), default="manual")
    auto_tipo = db.Column(db.String(50), nullable=True)
    actual_manual = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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


def company_to_dict(e):
    return {
        "id": e.id,
        "nombre": e.nombre,
        "activa": e.activa,
        "licencia_max_usuarios": e.licencia_max_usuarios,
        "licencia_max_proyectos": e.licencia_max_proyectos
    }


# -------- Calendario (OAuth por empresa) --------
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"

MS_SCOPES = "offline_access Calendars.ReadWrite"


def public_app_base_url():
    """URL pública del sitio (obligatoria en producción para OAuth)."""
    u = (os.getenv("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if u:
        return u
    return request.url_root.rstrip("/")


def calendar_callback_urls():
    base = public_app_base_url()
    return {
        "google": f"{base}{url_for('oauth_google_callback')}",
        "microsoft": f"{base}{url_for('oauth_microsoft_callback')}",
    }


def ensure_company_calendar_columns():
    """Añade columnas de calendario si la tabla ya existía antes del cambio de modelo."""
    try:
        insp = sa_inspect(db.engine)
        if not insp.has_table("companies"):
            return
        existing = {c["name"] for c in insp.get_columns("companies")}
    except Exception:
        return

    alters = []
    dialect = db.engine.dialect.name

    def need(name):
        return name not in existing

    defs = [
        ("calendar_provider", "VARCHAR(20) DEFAULT 'none'"),
        ("calendar_oauth_client_id", "TEXT"),
        ("calendar_oauth_client_secret", "TEXT"),
        ("calendar_google_calendar_id", "VARCHAR(500) DEFAULT 'primary'"),
        ("calendar_access_token", "TEXT"),
        ("calendar_refresh_token", "TEXT"),
        ("calendar_token_expires_at", "TIMESTAMP" if dialect != "sqlite" else "DATETIME"),
        ("calendar_microsoft_tenant", "VARCHAR(120) DEFAULT 'common'"),
    ]
    for col, typedef in defs:
        if need(col):
            alters.append((col, typedef))

    if not alters:
        return

    for col, typedef in alters:
        try:
            db.session.execute(text(f"ALTER TABLE companies ADD COLUMN {col} {typedef}"))
            db.session.commit()
        except Exception:
            db.session.rollback()


def company_calendar_connected(e: Company) -> bool:
    return bool(e and (e.calendar_refresh_token or "").strip())


def _company_for_calendar_user(u) -> Optional[Company]:
    if not u or u.get("rol") != "supervisor":
        return None
    eid = u.get("empresa_id")
    if not eid:
        return None
    return db.session.get(Company, int(eid))


def _clear_calendar_tokens(e: Company):
    e.calendar_access_token = None
    e.calendar_refresh_token = None
    e.calendar_token_expires_at = None


def project_to_dict(p):
    return {
        "id": p.id,
        "empresa_id": p.empresa_id,
        "nombre": p.nombre,
        "terminado": p.terminado
    }


def user_to_dict(u):
    return {
        "id": u.id,
        "empresa_id": u.empresa_id,
        "nombre": u.nombre,
        "correo": u.correo,
        "rol": u.rol
    }


# ================= AUTH =================
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None

    u = db.session.get(User, int(uid))
    if not u or not u.activo:
        return None

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
    p = db.session.get(Project, int(proyecto_id))
    if not p:
        return None
    return project_to_dict(p)


def user_can_access_project(u, proyecto_id: int) -> bool:
    if not u:
        return False

    if u.get("rol") == "superadmin":
        return True

    p = db.session.get(Project, int(proyecto_id))
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
    tareas_q = Task.query.filter_by(proyecto_id=int(proyecto_id)).order_by(Task.id.asc()).all()
    tareas = [task_to_dict(t) for t in tareas_q]
    contador_id = (tareas[-1]["id"] + 1) if tareas else 1
    return tareas, contador_id


def agregar_tarea(proyecto_id, texto, responsable, centro, plazo, observacion, recursos):
    p = db.session.get(Project, int(proyecto_id))
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


def filtrar_tareas(tareas, centro=None, responsable=None, estado=None, plazo=None, objetivo_id=None, objetivos_map=None):
    tareas_filtradas = list(tareas)
    hoy = datetime.now().date()

    if centro and centro != 'Todos':
        tareas_filtradas = [t for t in tareas_filtradas if t.get('centro_responsabilidad') == centro]

    if responsable and responsable != 'Todos':
        tareas_filtradas = [t for t in tareas_filtradas if t.get('responsable') == responsable]

    if estado and estado != 'Todos':
        tareas_filtradas = [t for t in tareas_filtradas if t.get('situacion') == estado]

    if objetivo_id is not None and objetivo_id != 'Todos' and objetivos_map:
        try:
            oid = int(objetivo_id)
            obj = objetivos_map.get(oid)
            if obj:
                centros = obj.get('centros') or []
                if centros:
                    tareas_filtradas = [t for t in tareas_filtradas if (t.get('centro_responsabilidad') or '') in centros]
        except Exception:
            pass

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


KPI_AUTO_TIPOS = [
    'avance_completadas_pct',
    'avance_validadas_pct',
    'tareas_vencidas',
    'tareas_total',
]


def objective_to_dict(o: Objective):
    return {
        'id': o.id,
        'empresa_id': o.empresa_id,
        'proyecto_id': o.proyecto_id,
        'nombre': o.nombre,
        'descripcion': o.descripcion or '',
        'centros': o.centros or [],
        'responsable': o.responsable or '',
        'estado': o.estado or 'Activo',
        'fecha_inicio': o.fecha_inicio or '',
        'fecha_fin': o.fecha_fin or ''
    }


def calcular_kpi_actual(k: KPI, proyecto_id: int, objetivos_map: dict):
    modo = (k.modo or 'manual')
    if modo == 'manual':
        return k.actual_manual

    obj = objetivos_map.get(k.objetivo_id)
    if not obj:
        return None

    centros = obj.get('centros') or []
    tq = Task.query.filter_by(proyecto_id=int(proyecto_id))
    tareas = [task_to_dict(t) for t in tq.all()]
    if centros:
        tareas = [t for t in tareas if (t.get('centro_responsabilidad') or '') in centros]

    total = len(tareas)
    if k.auto_tipo == 'tareas_total':
        return float(total)

    hoy = datetime.now().date()
    if k.auto_tipo == 'tareas_vencidas':
        vencidas = 0
        for t in tareas:
            plazo_str = t.get('plazo')
            if not plazo_str:
                continue
            try:
                plazo_date = datetime.strptime(plazo_str, '%Y-%m-%d').date()
            except Exception:
                continue
            if t.get('situacion') in ('Completada', 'Validada'):
                continue
            if plazo_date < hoy:
                vencidas += 1
        return float(vencidas)

    if total <= 0:
        return 0.0

    if k.auto_tipo == 'avance_completadas_pct':
        return 100.0 * sum(1 for t in tareas if t.get('situacion') == 'Completada') / total
    if k.auto_tipo == 'avance_validadas_pct':
        return 100.0 * sum(1 for t in tareas if t.get('situacion') == 'Validada') / total

    return None


def kpi_to_dict(k: KPI, proyecto_id: int, objetivos_map: dict):
    actual = calcular_kpi_actual(k, proyecto_id, objetivos_map)
    estado_kpi = 'sin_meta'
    if k.meta is not None and actual is not None:
        estado_kpi = 'ok' if actual >= k.meta else 'bajo'
    return {
        'id': k.id,
        'objetivo_id': k.objetivo_id,
        'nombre': k.nombre,
        'unidad': k.unidad or '',
        'meta': k.meta,
        'modo': k.modo or 'manual',
        'auto_tipo': k.auto_tipo,
        'actual_manual': k.actual_manual,
        'actual': actual,
        'estado_kpi': estado_kpi,
    }


# ================= SEED/RESET SUPERADMIN =================
def ensure_superadmin():
    admin_email = (os.getenv("ADMIN_EMAIL", "admin@tuapp.cl") or "admin@tuapp.cl").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")
    force_reset = os.getenv("ADMIN_FORCE_RESET", "0") == "1"

    u = User.query.filter_by(correo=admin_email).first()
    if u:
        if u.rol != "superadmin" or u.empresa_id is not None:
            u.rol = "superadmin"
            u.empresa_id = None
        if force_reset:
            u.password_hash = generate_password_hash(admin_password)
        db.session.commit()
        print(f"✅ Superadmin OK (existente): {admin_email} | reset={force_reset}")
        return

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


# ================= CREACIÓN EMPRESA+PROYECTO (sin usuarios) =================
def crear_empresa_full(nombre_empresa, proyectos_nombres, max_users=5, max_proys=1):
    """
    Crea una empresa y sus proyectos iniciales.
    No crea usuarios automáticamente: los usuarios se crean desde los formularios
    del panel de configuración del superadmin.
    """
    nombre_empresa = (nombre_empresa or "").strip()

    empresa = Company(
        nombre=nombre_empresa,
        activa=True,
        licencia_max_usuarios=max_users,
        licencia_max_proyectos=max_proys
    )

    db.session.add(empresa)
    db.session.flush()

    # Crear proyectos respetando el máximo de la licencia
    proyectos_creados = []
    for nombre in proyectos_nombres:
        if len(proyectos_creados) >= (empresa.licencia_max_proyectos or 1):
            break

        nombre = (nombre or "").strip()
        if not nombre:
            continue

        p = Project(
            empresa_id=empresa.id,
            nombre=nombre,
            terminado=False
        )

        db.session.add(p)
        proyectos_creados.append(p)

    db.session.commit()
    return empresa.id

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
        resumen.append({
            "empresa": {"id": e.id, "nombre": e.nombre},
            "n_proyectos": n_proys,
            "n_usuarios": n_users
        })

    return render_template("admin_dashboard.html", resumen=resumen)


# Rutas faltantes que algunos templates antiguos usan
@app.route("/sa/empresas")
@login_required
@require_roles("superadmin")
def sa_empresas():
    return redirect(url_for("sa_config"))


@app.route("/sa/usuarios")
@login_required
@require_roles("superadmin")
def sa_usuarios():
    return redirect(url_for("sa_config"))


@app.route("/sa/proyectos")
@login_required
@require_roles("superadmin")
def sa_proyectos():
    return redirect(url_for("sa_config"))


@app.route("/sa/empresa/nueva", methods=["GET", "POST"])
@login_required
@require_roles("superadmin")
def sa_empresa_nueva():
    # GET: mostrar formulario
    if request.method == "GET":
        return render_template("sa_empresa_nueva.html")

    # POST: crear empresa + proyectos + (opcionalmente) usuarios iniciales
    nombre_empresa = (request.form.get("nombre_empresa") or "").strip()
    if not nombre_empresa:
        flash("Debes ingresar un nombre de empresa.", "error")
        return render_template("sa_empresa_nueva.html"), 200

    licencia_max_usuarios = to_int(request.form.get("licencia_max_usuarios"), 5) or 5
    licencia_max_proyectos = to_int(request.form.get("licencia_max_proyectos"), 1) or 1

    # Recoger nombres de proyectos desde el formulario
    proyectos = []
    for i in range(1, licencia_max_proyectos + 1):
        field_name = f"nombre_proyecto_{i}"
        nombre_proy = (request.form.get(field_name) or "").strip()
        if nombre_proy:
            proyectos.append(nombre_proy)

    if not proyectos:
        flash("Debes ingresar al menos un proyecto.", "error")
        return render_template("sa_empresa_nueva.html"), 200

    # Crear empresa y proyectos
    empresa_id = crear_empresa_full(
        nombre_empresa,
        proyectos,
        max_users=licencia_max_usuarios,
        max_proys=licencia_max_proyectos,
    )

    # Crear supervisores y ejecutores iniciales respetando la licencia de usuarios
    empresa = db.session.get(Company, empresa_id)
    max_users_total = int(empresa.licencia_max_usuarios or 5)
    usuarios_creados = 0

    def _maybe_crear_usuario(nombre, correo, password, rol):
        nonlocal usuarios_creados
        nombre = (nombre or "").strip()
        correo = (correo or "").strip().lower()
        password = password or ""

        if not (nombre and correo and password):
            return

        if usuarios_creados >= max_users_total:
            return

        if User.query.filter_by(correo=correo).first():
            # Correo duplicado, se omite silenciosamente
            return

        u = User(
            nombre=nombre,
            correo=correo,
            password_hash=generate_password_hash(password),
            rol=rol,
            empresa_id=empresa_id,
            activo=True,
        )
        db.session.add(u)
        usuarios_creados += 1

    # Supervisores
    for i in range(1, 6):
        _maybe_crear_usuario(
            request.form.get(f"nombre_supervisor_{i}"),
            request.form.get(f"correo_supervisor_{i}"),
            request.form.get(f"pass_supervisor_{i}"),
            "supervisor",
        )
        if usuarios_creados >= max_users_total:
            break

    # Ejecutores
    if usuarios_creados < max_users_total:
        for i in range(1, 6):
            _maybe_crear_usuario(
                request.form.get(f"nombre_ejecutor_{i}"),
                request.form.get(f"correo_ejecutor_{i}"),
                request.form.get(f"pass_ejecutor_{i}"),
                "ejecutor",
            )
            if usuarios_creados >= max_users_total:
                break

    db.session.commit()

    if usuarios_creados > max_users_total:
        flash(
            f"Se alcanzó el máximo de usuarios permitidos por la licencia "
            f"({usuarios_creados}/{max_users_total}).",
            "error",
        )

    flash("Empresa creada correctamente ✅", "ok")
    return redirect(url_for("sa_config", empresa_id=empresa_id))

# ================= SUPERADMIN: CONFIG PANEL (CRUD) =================
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
            empresa_sel = db.session.get(Company, empresa_id)
        if not empresa_sel:
            empresa_sel = empresas[0]
            empresa_id = empresa_sel.id

    proyectos_sel = []
    usuarios_sel = []

    if empresa_sel:
        proyectos_q = Project.query.filter_by(empresa_id=empresa_sel.id).order_by(Project.nombre.asc()).all()
        usuarios_q = User.query.filter_by(empresa_id=empresa_sel.id).order_by(User.correo.asc()).all()

        proyectos_sel = [project_to_dict(p) for p in proyectos_q]
        usuarios_sel = [user_to_dict(u) for u in usuarios_q]

    empresas_out = [company_to_dict(e) for e in empresas]
    empresa_sel_out = company_to_dict(empresa_sel) if empresa_sel else None

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
    e = db.session.get(Company, empresa_id)
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
    proys = Project.query.filter_by(empresa_id=empresa_id).all()
    proy_ids = [p.id for p in proys]

    if proy_ids:
        Task.query.filter(Task.proyecto_id.in_(proy_ids)).delete(synchronize_session=False)

    User.query.filter_by(empresa_id=empresa_id).delete(synchronize_session=False)
    Project.query.filter_by(empresa_id=empresa_id).delete(synchronize_session=False)
    Company.query.filter_by(id=empresa_id).delete(synchronize_session=False)

    db.session.commit()

    flash("Empresa eliminada (con proyectos, usuarios y tareas asociadas).", "ok")
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

    empresa = db.session.get(Company, empresa_id_int)
    if not empresa:
        flash("Empresa no encontrada.", "error")
        return redirect(url_for("sa_config"))

    n_actual = Project.query.filter_by(empresa_id=empresa_id_int).count()
    max_proys = int(empresa.licencia_max_proyectos or 1)

    if n_actual >= max_proys:
        flash(f"Límite de proyectos alcanzado ({n_actual}/{max_proys}).", "error")
        return redirect(url_for("sa_config", empresa_id=empresa_id_int))

    existente = Project.query.filter_by(empresa_id=empresa_id_int, nombre=nombre).first()
    if existente:
        flash("Ya existe un proyecto con ese nombre en esta empresa.", "error")
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
    p = db.session.get(Project, proyecto_id)
    if not p:
        abort(404)

    nombre = (request.form.get("nombre") or "").strip()
    terminado = _bool(request.form.get("terminado"))

    if nombre:
        otro = Project.query.filter(
            Project.empresa_id == p.empresa_id,
            Project.nombre == nombre,
            Project.id != proyecto_id
        ).first()
        if otro:
            flash("Ya existe otro proyecto con ese nombre en la empresa.", "error")
            return redirect(url_for("sa_config", empresa_id=p.empresa_id))
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
    p = db.session.get(Project, proyecto_id)
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

    empresa = db.session.get(Company, empresa_id_int)
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
        empresa_id=empresa_id_int,
        activo=True
    )
    db.session.add(u)
    db.session.commit()

    flash("Usuario creado ✅", "ok")
    return redirect(url_for("sa_config", empresa_id=empresa_id_int))


@app.route("/sa/usuario/<int:user_id>/editar", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_usuario_editar(user_id):
    u = db.session.get(User, user_id)
    if not u:
        abort(404)

    empresa_id_redirect = u.empresa_id

    nombre = (request.form.get("nombre") or "").strip()
    correo = (request.form.get("correo") or "").strip().lower()
    rol = (request.form.get("rol") or "").strip().lower()

    if nombre:
        u.nombre = nombre

    if correo and correo != u.correo:
        existe = User.query.filter(User.correo == correo, User.id != user_id).first()
        if existe:
            flash("Ese correo ya existe en otro usuario.", "error")
            return redirect(url_for("sa_config", empresa_id=empresa_id_redirect))
        u.correo = correo

    if rol in ("superadmin", "supervisor", "ejecutor"):
        u.rol = rol
        if rol == "superadmin":
            u.empresa_id = None
            empresa_id_redirect = None

    db.session.commit()
    flash("Usuario actualizado.", "ok")
    return redirect(url_for("sa_config", empresa_id=empresa_id_redirect))


@app.route("/sa/usuario/<int:user_id>/reset-password", methods=["POST"])
@login_required
@require_roles("superadmin")
def sa_usuario_reset_password(user_id):
    u = db.session.get(User, user_id)
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
    u = db.session.get(User, user_id)
    empresa_id = u.empresa_id if u else None

    if not u:
        abort(404)

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
    empresa = db.session.get(Company, int(u.get("empresa_id")))

    proys = Project.query.filter_by(
        empresa_id=int(u.get("empresa_id"))
    ).order_by(Project.nombre.asc()).all()

    avances = []
    for p in proys:
        tareas, _ = load_tareas(p.id)
        est = obtener_estadisticas(tareas)
        total = est["total"]
        comp = est["por_estado"].get("Completada", 0)
        val = est["por_estado"].get("Validada", 0)
        avance = round(((comp + val) / total) * 100, 1) if total else 0
        avances.append({
            "proyecto": project_to_dict(p),
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


# ================= CALENDARIO: credenciales OAuth por empresa =================
@app.route("/empresa/calendario", methods=["GET", "POST"])
@login_required
@require_roles("supervisor")
@no_cache
def empresa_calendario():
    u = current_user()
    empresa = _company_for_calendar_user(u)
    if not empresa:
        abort(403)

    if request.method == "POST":
        prov = (request.form.get("calendar_provider") or "none").strip().lower()
        if prov not in ("none", "google", "microsoft"):
            prov = "none"
        empresa.calendar_provider = prov
        cid = (request.form.get("oauth_client_id") or "").strip()
        csec = (request.form.get("oauth_client_secret") or "").strip()
        empresa.calendar_oauth_client_id = cid or None
        if csec:
            empresa.calendar_oauth_client_secret = csec
        gcal = (request.form.get("google_calendar_id") or "primary").strip() or "primary"
        empresa.calendar_google_calendar_id = gcal
        mst = (request.form.get("microsoft_tenant") or "common").strip() or "common"
        empresa.calendar_microsoft_tenant = mst
        db.session.commit()
        flash(
            "Configuración guardada. Registra las URLs de redirección en Google Cloud o Azure "
            "y pulsa Conectar.",
            "ok",
        )
        return redirect(url_for("empresa_calendario"))

    cbs = calendar_callback_urls()
    connected = company_calendar_connected(empresa)
    return render_template(
        "empresa_calendario.html",
        user=u,
        empresa=empresa,
        callback_google=cbs["google"],
        callback_microsoft=cbs["microsoft"],
        connected=connected,
        base_url_hint=public_app_base_url(),
    )


@app.route("/empresa/calendario/desconectar", methods=["POST"])
@login_required
@require_roles("supervisor")
def empresa_calendario_desconectar():
    u = current_user()
    empresa = _company_for_calendar_user(u)
    if not empresa:
        abort(403)
    _clear_calendar_tokens(empresa)
    db.session.commit()
    flash("Conexión con el calendario cerrada (tokens eliminados en el ERP).", "ok")
    return redirect(url_for("empresa_calendario"))


@app.route("/oauth/google/iniciar")
@login_required
@require_roles("supervisor")
def oauth_google_iniciar():
    u = current_user()
    empresa = _company_for_calendar_user(u)
    if not empresa:
        abort(403)
    if empresa.calendar_provider != "google":
        flash("Elige Google Calendar y guarda Client ID y Client secret.", "error")
        return redirect(url_for("empresa_calendario"))
    if not (empresa.calendar_oauth_client_id or "").strip() or not (
        empresa.calendar_oauth_client_secret or ""
    ).strip():
        flash("Faltan Client ID o Client secret de Google.", "error")
        return redirect(url_for("empresa_calendario"))

    redirect_uri = calendar_callback_urls()["google"]
    state = secrets.token_urlsafe(32)
    session["cal_oauth"] = {
        "state": state,
        "company_id": empresa.id,
        "provider": "google",
    }
    q = {
        "client_id": empresa.calendar_oauth_client_id.strip(),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_CALENDAR_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(q)}")


@app.route("/oauth/google/callback")
@login_required
def oauth_google_callback():
    u = current_user()
    if not u or u.get("rol") != "supervisor":
        flash("Solo supervisores pueden conectar el calendario.", "error")
        return redirect(url_for("empresa_dashboard"))
    err = request.args.get("error")
    if err:
        flash(f"Google no completó la autorización: {err}", "error")
        return redirect(url_for("empresa_calendario"))

    cal = session.pop("cal_oauth", None)
    code = request.args.get("code")
    st = request.args.get("state")
    if not cal or cal.get("provider") != "google" or not code or st != cal.get("state"):
        flash("Sesión de autorización inválida o expirada. Intenta de nuevo.", "error")
        return redirect(url_for("empresa_calendario"))

    empresa = _company_for_calendar_user(u)
    if not empresa or empresa.id != cal.get("company_id"):
        flash("La sesión no coincide con la empresa.", "error")
        return redirect(url_for("empresa_calendario"))

    redirect_uri = calendar_callback_urls()["google"]
    try:
        r = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": (empresa.calendar_oauth_client_id or "").strip(),
                "client_secret": (empresa.calendar_oauth_client_secret or "").strip(),
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=45,
        )
        data = r.json()
    except Exception as ex:
        flash(f"Error al contactar Google: {ex}", "error")
        return redirect(url_for("empresa_calendario"))

    if r.status_code != 200 or "access_token" not in data:
        msg = data.get("error_description") or data.get("error") or (r.text or "")[:200]
        flash(f"No se pudo obtener el token: {msg}", "error")
        return redirect(url_for("empresa_calendario"))

    empresa.calendar_access_token = data.get("access_token")
    empresa.calendar_refresh_token = data.get("refresh_token") or empresa.calendar_refresh_token
    exp = data.get("expires_in")
    if exp:
        empresa.calendar_token_expires_at = datetime.utcnow() + timedelta(seconds=int(exp))
    db.session.commit()
    flash("Google Calendar conectado. Siguiente paso: sincronizar eventos desde las tareas.", "ok")
    return redirect(url_for("empresa_calendario"))


@app.route("/oauth/microsoft/iniciar")
@login_required
@require_roles("supervisor")
def oauth_microsoft_iniciar():
    u = current_user()
    empresa = _company_for_calendar_user(u)
    if not empresa:
        abort(403)
    if empresa.calendar_provider != "microsoft":
        flash("Elige Microsoft 365 / Outlook y guarda el Client ID y el secret.", "error")
        return redirect(url_for("empresa_calendario"))
    if not (empresa.calendar_oauth_client_id or "").strip() or not (
        empresa.calendar_oauth_client_secret or ""
    ).strip():
        flash("Faltan Client ID o Client secret de Microsoft.", "error")
        return redirect(url_for("empresa_calendario"))

    tenant = (empresa.calendar_microsoft_tenant or "common").strip() or "common"
    redirect_uri = calendar_callback_urls()["microsoft"]
    state = secrets.token_urlsafe(32)
    session["cal_oauth"] = {
        "state": state,
        "company_id": empresa.id,
        "provider": "microsoft",
    }
    auth_base = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
    q = {
        "client_id": empresa.calendar_oauth_client_id.strip(),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": MS_SCOPES,
        "state": state,
        "prompt": "consent",
    }
    return redirect(f"{auth_base}?{urlencode(q)}")


@app.route("/oauth/microsoft/callback")
@login_required
def oauth_microsoft_callback():
    u = current_user()
    if not u or u.get("rol") != "supervisor":
        flash("Solo supervisores pueden conectar el calendario.", "error")
        return redirect(url_for("empresa_dashboard"))
    err = request.args.get("error")
    if err:
        desc = (request.args.get("error_description") or "")[:200]
        flash(f"Microsoft no completó la autorización: {err} {desc}", "error")
        return redirect(url_for("empresa_calendario"))

    cal = session.pop("cal_oauth", None)
    code = request.args.get("code")
    st = request.args.get("state")
    if not cal or cal.get("provider") != "microsoft" or not code or st != cal.get("state"):
        flash("Sesión de autorización inválida o expirada. Intenta de nuevo.", "error")
        return redirect(url_for("empresa_calendario"))

    empresa = _company_for_calendar_user(u)
    if not empresa or empresa.id != cal.get("company_id"):
        flash("La sesión no coincide con la empresa.", "error")
        return redirect(url_for("empresa_calendario"))

    tenant = (empresa.calendar_microsoft_tenant or "common").strip() or "common"
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    redirect_uri = calendar_callback_urls()["microsoft"]
    try:
        r = requests.post(
            token_url,
            data={
                "client_id": (empresa.calendar_oauth_client_id or "").strip(),
                "client_secret": (empresa.calendar_oauth_client_secret or "").strip(),
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "scope": MS_SCOPES,
            },
            timeout=45,
        )
        data = r.json()
    except Exception as ex:
        flash(f"Error al contactar Microsoft: {ex}", "error")
        return redirect(url_for("empresa_calendario"))

    if r.status_code != 200 or "access_token" not in data:
        msg = data.get("error_description") or data.get("error") or (r.text or "")[:200]
        flash(f"No se pudo obtener el token: {msg}", "error")
        return redirect(url_for("empresa_calendario"))

    empresa.calendar_access_token = data.get("access_token")
    empresa.calendar_refresh_token = data.get("refresh_token") or empresa.calendar_refresh_token
    exp = data.get("expires_in")
    if exp:
        empresa.calendar_token_expires_at = datetime.utcnow() + timedelta(seconds=int(exp))
    db.session.commit()
    flash("Microsoft 365 / Outlook conectado. Siguiente paso: sincronizar eventos desde las tareas.", "ok")
    return redirect(url_for("empresa_calendario"))


# ================= SELECCIONAR PROYECTO =================
@app.route("/seleccionar-proyecto", methods=["GET"])
@login_required
@require_roles("supervisor", "ejecutor")
@no_cache
def seleccionar_proyecto():
    u = current_user()
    proys = Project.query.filter_by(
        empresa_id=int(u.get("empresa_id"))
    ).order_by(Project.nombre.asc()).all()

    if not proys:
        flash("Tu empresa no tiene proyectos activos. Pide al Superadmin que cree o reactive uno.", "error")
        return redirect(url_for("empresa_dashboard"))

    if len(proys) == 1:
        pid = proys[0].id
        set_active_project(pid)
        if u.get("rol") == "supervisor":
            return redirect(url_for("proyecto_tablero", proyecto_id=pid))
        return redirect(url_for("proyecto_index", proyecto_id=pid))

    proys_out = [project_to_dict(p) for p in proys]
    return render_template("seleccionar_proyecto.html", proyectos=proys_out, user=u)


@app.route("/seleccionar-proyecto/<int:proyecto_id>", methods=["POST"])
@login_required
@require_roles("supervisor", "ejecutor")
def seleccionar_proyecto_post(proyecto_id):
    """Compatibilidad con formulario del selector de proyectos."""
    u = current_user()
    if not user_can_access_project(u, proyecto_id):
        abort(403)

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
    u = current_user()

    empresa = db.session.get(Company, int(u.get("empresa_id"))) if u.get("empresa_id") else None
    empresa_nombre = empresa.nombre if empresa else ""

    proys = Project.query.filter_by(
        empresa_id=int(u.get("empresa_id"))
    ).order_by(Project.nombre.asc()).all()

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
    objetivo_filtro = request.args.get('objetivo', 'Todos')

    u = current_user()
    empresa = db.session.get(Company, int(u.get("empresa_id"))) if u.get("empresa_id") else None
    empresa_nombre = empresa.nombre if empresa else ""

    proys = Project.query.filter_by(
        empresa_id=int(u.get("empresa_id"))
    ).order_by(Project.nombre.asc()).all()

    proyectos_usuario = [{"id": p.id, "nombre": p.nombre} for p in proys]

    objetivos = [objective_to_dict(o) for o in Objective.query.filter_by(proyecto_id=int(proyecto_id)).order_by(Objective.id.asc()).all()]
    objetivos_map = {o['id']: o for o in objetivos}

    tareas_filtradas = filtrar_tareas(
        tareas,
        centro=centro_filtro if centro_filtro != 'Todos' else None,
        responsable=responsable_filtro if responsable_filtro != 'Todos' else None,
        estado=estado_filtro if estado_filtro != 'Todos' else None,
        plazo=plazo_filtro if plazo_filtro != 'Todos' else None,
        objetivo_id=objetivo_filtro,
        objetivos_map=objetivos_map
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
            "plazo": plazo_filtro,
            "objetivo": objetivo_filtro
        },
        objetivos=objetivos,
        objetivos_map=objetivos_map,
        kpis=[kpi_to_dict(k, int(proyecto_id), objetivos_map) for k in KPI.query.join(Objective, KPI.objetivo_id == Objective.id).filter(Objective.proyecto_id == int(proyecto_id)).order_by(KPI.id.asc()).all()],
        proyecto_id=proyecto_id,
        user=u,
        empresa_nombre=empresa_nombre,
        proyectos_usuario=proyectos_usuario
    )


# ================= PROYECTO: OBJETIVOS + KPIs =================
@app.route("/p/<int:proyecto_id>/objetivos")
@login_required
@require_project_access
@no_cache
def proyecto_objetivos(proyecto_id):
    u = current_user()
    empresa = db.session.get(Company, int(u.get("empresa_id"))) if u.get("empresa_id") else None
    empresa_nombre = empresa.nombre if empresa else ""

    proys = Project.query.filter_by(empresa_id=int(u.get("empresa_id"))).order_by(Project.nombre.asc()).all()
    proyectos_usuario = [{"id": p.id, "nombre": p.nombre} for p in proys]

    objetivos = [objective_to_dict(o) for o in Objective.query.filter_by(proyecto_id=int(proyecto_id)).order_by(Objective.id.asc()).all()]
    objetivos_map = {o['id']: o for o in objetivos}
    kpis = [kpi_to_dict(k, int(proyecto_id), objetivos_map) for k in KPI.query.join(Objective, KPI.objetivo_id == Objective.id).filter(Objective.proyecto_id == int(proyecto_id)).order_by(KPI.id.asc()).all()]
    kpis_por_obj = {}
    for k in kpis:
        kpis_por_obj.setdefault(k['objetivo_id'], []).append(k)

    return render_template(
        "objetivos.html",
        proyecto_id=proyecto_id,
        user=u,
        empresa_nombre=empresa_nombre,
        proyectos_usuario=proyectos_usuario,
        objetivos=objetivos,
        kpis_por_obj=kpis_por_obj,
        kpi_auto_tipos=KPI_AUTO_TIPOS
    )


@app.route("/p/<int:proyecto_id>/objetivos/agregar", methods=["POST"])
@login_required
@require_project_access
def proyecto_objetivo_agregar(proyecto_id):
    p = db.session.get(Project, int(proyecto_id))
    if p:
        nombre = (request.form.get("nombre") or "").strip()
        if nombre:
            centros_raw = request.form.get("centros", "")
            centros = [c.strip() for c in (centros_raw or "").split(",") if c.strip()]
            db.session.add(Objective(
                empresa_id=p.empresa_id,
                proyecto_id=p.id,
                nombre=nombre,
                descripcion=(request.form.get("descripcion") or "").strip(),
                centros=centros,
                responsable=(request.form.get("responsable") or "").strip(),
                estado=(request.form.get("estado") or "Activo").strip(),
                fecha_inicio=(request.form.get("fecha_inicio") or "").strip(),
                fecha_fin=(request.form.get("fecha_fin") or "").strip(),
            ))
            db.session.commit()
    return redirect(url_for("proyecto_objetivos", proyecto_id=proyecto_id))


@app.route("/p/<int:proyecto_id>/objetivos/<int:objetivo_id>/eliminar", methods=["POST"])
@login_required
@require_project_access
def proyecto_objetivo_eliminar(proyecto_id, objetivo_id):
    Objective.query.filter_by(id=objetivo_id, proyecto_id=int(proyecto_id)).delete(synchronize_session=False)
    KPI.query.filter_by(objetivo_id=objetivo_id).delete(synchronize_session=False)
    db.session.commit()
    return redirect(url_for("proyecto_objetivos", proyecto_id=proyecto_id))


@app.route("/p/<int:proyecto_id>/kpi/agregar/<int:objetivo_id>", methods=["POST"])
@login_required
@require_project_access
def proyecto_kpi_agregar(proyecto_id, objetivo_id):
    obj = Objective.query.filter_by(id=objetivo_id, proyecto_id=int(proyecto_id)).first()
    if obj:
        try:
            meta = float(request.form.get("meta")) if request.form.get("meta") not in (None, "") else None
        except Exception:
            meta = None
        try:
            actual_manual = float(request.form.get("actual_manual")) if request.form.get("actual_manual") not in (None, "") else None
        except Exception:
            actual_manual = None
        modo = (request.form.get("modo") or "manual").strip()
        auto_tipo = request.form.get("auto_tipo")
        if modo not in ("manual", "auto"):
            modo = "manual"
        if auto_tipo not in KPI_AUTO_TIPOS:
            auto_tipo = None

        db.session.add(KPI(
            objetivo_id=objetivo_id,
            nombre=(request.form.get("nombre") or "").strip(),
            unidad=(request.form.get("unidad") or "").strip(),
            meta=meta,
            modo=modo,
            auto_tipo=auto_tipo if modo == "auto" else None,
            actual_manual=actual_manual if modo == "manual" else None,
        ))
        db.session.commit()
    return redirect(url_for("proyecto_objetivos", proyecto_id=proyecto_id))


@app.route("/p/<int:proyecto_id>/kpi/<int:kpi_id>/eliminar", methods=["POST"])
@login_required
@require_project_access
def proyecto_kpi_eliminar(proyecto_id, kpi_id):
    KPI.query.filter_by(id=kpi_id).delete(synchronize_session=False)
    db.session.commit()
    return redirect(url_for("proyecto_objetivos", proyecto_id=proyecto_id))


# ================= PROYECTO: INFORME =================
@app.route("/p/<int:proyecto_id>/informe")
@login_required
@require_project_access
@no_cache
def proyecto_informe(proyecto_id):
    tareas, _ = load_tareas(proyecto_id)
    estadisticas = obtener_estadisticas(tareas)
    hoy = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    proyecto = _get_project(proyecto_id)
    proyecto_nombre = (proyecto or {}).get("nombre", "Proyecto")

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
        proyecto_id=proyecto_id,
        proyecto_nombre=proyecto_nombre
    )


@app.route("/about")
def about():
    return render_template("about.html")


# ================= MIGRACIÓN (JSON -> DB) =================
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
    if os.getenv("ALLOW_DB_MIGRATION", "0") != "1":
        abort(403)

    ed = _read_json(EMPRESAS_FILE, {"empresas": []})
    pd_ = _read_json(PROYECTOS_FILE, {"proyectos": []})
    ud = _read_json(USUARIOS_FILE, {"usuarios": []})

    empresas = ed.get("empresas", [])
    proyectos = pd_.get("proyectos", [])
    usuarios = ud.get("usuarios", [])

    for e in empresas:
        eid = to_int(e.get("id"))
        if not eid:
            continue
        exists = db.session.get(Company, eid)
        if not exists:
            db.session.add(Company(
                id=eid,
                nombre=(e.get("nombre") or "").strip() or f"Empresa {eid}",
                activa=bool(e.get("activa", True)),
                licencia_max_usuarios=to_int(e.get("licencia_max_usuarios"), 5) or 5,
                licencia_max_proyectos=to_int(e.get("licencia_max_proyectos"), 1) or 1,
            ))
    db.session.commit()

    for p in proyectos:
        pid = to_int(p.get("id"))
        empid = to_int(p.get("empresa_id"))
        if not pid or not empid:
            continue
        exists = db.session.get(Project, pid)
        if not exists:
            db.session.add(Project(
                id=pid,
                empresa_id=empid,
                nombre=(p.get("nombre") or "").strip() or f"Proyecto {pid}",
                terminado=bool(p.get("terminado", False))
            ))
    db.session.commit()

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
with app.app_context():
    db.create_all()
    ensure_company_calendar_columns()
    ensure_superadmin()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
