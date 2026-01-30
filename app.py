import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True

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
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
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
@app.route("/")
@login_required
def dashboard():
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
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
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# -------------------------
# ADMIN DESACTIVADO
# -------------------------
@app.route("/admin")
@login_required
def admin():
    return redirect("/")

    @app.route("/")
def dashboard():
    
