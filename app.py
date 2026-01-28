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
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = validar_usuario(
            request.form["username"],
            request.form["password"]
        )

        if user:
            session["user_id"] = user["id"]
            session["empresa_id"] = user["empresa_id"]
            session["rol"] = user["rol"]
            session["nombre"] = user["nombre"]

            if user["rol"] == "superadmin":
                return redirect("/admin")
            return redirect("/")

        flash("Credenciales incorrectas")

    return render_template("login.html")

# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -------------------------
# DASHBOARD EMPRESA
# -------------------------
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")

# -------------------------
# SUPERADMIN
# -------------------------
@app.route("/admin")
@login_required
def admin():
    if session["rol"] != "superadmin":
        return redirect("/")
    return render_template("admin_dashboard.html")
