import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

# -------------------------
# RUTAS ABSOLUTAS PARA RENDER
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

DATABASE_URL = os.environ.get("DATABASE_URL")

# -------------------------
# CONEXIÓN A POSTGRES (RENDER)
# -------------------------
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    conn.autocommit = True
    return conn

# -------------------------
# LOGIN REQUIRED
# -------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# -------------------------
# AUTH
# -------------------------
def validar_usuario(username, password):
    with get_conn().cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, empresa_id, nombre, rol
            FROM usuarios
            WHERE username = %s
              AND password_hash = crypt(%s, password_hash)
              AND activo = true
        """, (username, password))
        return cur.fetchone()

# -------------------------
# LOGIN
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = validar_usuario(username, password)

        if user:
            session["user_id"] = user["id"]
            session["empresa_id"] = user["empresa_id"]
            session["nombre"] = user["nombre"]
            session["rol"] = user["rol"]
            return redirect("/")
        else:
            flash("Usuario o contraseña incorrectos")

    return render_template("login.html")

# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -------------------------
# DASHBOARD
# -------------------------
@app.route("/")
@login_required
def dashboard():
    with get_conn().cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, nombre, descripcion
            FROM proyectos
            WHERE empresa_id = %s
              AND activo = true
            ORDER BY fecha_creacion DESC
        """, (session["empresa_id"],))
        proyectos = cur.fetchall()

    return render_template("dashboard.html", proyectos=proyectos)

# -------------------------
# ADMIN DESACTIVADO
# -------------------------
@app.route("/admin")
@login_required
def admin():
    return redirect("/")
