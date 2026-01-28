# ARCHIVO app.py CORREGIDO
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

# Protección de login
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# Validación real de usuarios
def validar_usuario(username, password):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, empresa_id, nombre, rol
            FROM usuarios
            WHERE username=%s
              AND password_hash = crypt(%s, password_hash)
              AND activo = true
        """, (username, password))
        return cur.fetchone()

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = validar_usuario(username, password)

        if user:
            session["user_id"] = user["id"]
            session["empresa_id"] = user["empresa_id"]
            session["rol"] = user["rol"]
            session["nombre"] = user["nombre"]

            if user["rol"] == "superadmin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("dashboard"))

        else:
            flash("Credenciales incorrectas")

    return render_template("login.html")

    # Logout
    @app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# Dashboard Empresa
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")

# SuperAdmin
@app.route("/admin")
@login_required
def admin_dashboard():
    if session["rol"] != "superadmin":
        return redirect(url_for("dashboard"))

    return render_template("admin_dashboard.html")

init_db()
CREATE TABLE tareas ...

