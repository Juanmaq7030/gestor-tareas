import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# ================== DATABASE ==================

DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True

def init_db():
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id SERIAL PRIMARY KEY,
            titulo TEXT NOT NULL,
            responsable TEXT,
            proyecto TEXT,
            estado TEXT DEFAULT 'Sin Ejecutar',
            fecha_creacion TIMESTAMP DEFAULT NOW()
        );
        """)
    print("Base de datos lista")

init_db()

# ================== MODELO ==================

def obtener_tareas():
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM tareas ORDER BY id DESC")
        return cur.fetchall()

def crear_tarea(titulo, responsable, proyecto):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO tareas (titulo, responsable, proyecto)
            VALUES (%s, %s, %s)
        """, (titulo, responsable, proyecto))

def cambiar_estado(id, estado):
    with conn.cursor() as cur:
        cur.execute("UPDATE tareas SET estado=%s WHERE id=%s", (estado, id))

# ================== RUTAS ==================

@app.route("/")
def index():
    tareas = obtener_tareas()
    return render_template("index.html", tareas=tareas)

@app.route("/agregar", methods=["POST"])
def agregar():
    titulo = request.form.get("titulo")
    responsable = request.form.get("responsable")
    proyecto = request.form.get("proyecto")

    if titulo:
        crear_tarea(titulo, responsable, proyecto)

    return redirect(url_for("index"))

@app.route("/estado/<int:id>/<estado>")
def cambiar(id, estado):
    cambiar_estado(id, estado)
    return redirect(url_for("index"))
