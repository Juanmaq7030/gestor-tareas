import os
import psycopg2
import psycopg2.extras

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, make_response, jsonify
import time
import json
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from functools import wraps
import smtplib
from email.message import EmailMessage
import threading

DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True

def init_db():
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id SERIAL PRIMARY KEY,
            titulo TEXT,
            descripcion TEXT,
            estado TEXT,
            fecha_creacion TIMESTAMP,
            fecha_vencimiento TIMESTAMP,
            responsable TEXT,
            proyecto TEXT
        );
        """)
    print("Base de datos lista")

init_db()

app = Flask(__name__)

# ================= CONFIGURACIÓN =================

UPLOAD_FOLDER = 'uploads'
DATA_FILE = 'tareas.json'

ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'gif',
    'doc', 'docx', 'xls', 'xlsx', 'txt'
}

# Estados actualizados según requerimientos
ESTADOS = [
    'Sin Ejecutar',
    'En Ejecución',
    'Pendiente de',
    'Completada',
    'Validada'
]

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

tareas = []
contador_id = 1

# ================= UTILIDADES =================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def guardar_tareas():
    global tareas, contador_id
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'tareas': tareas,
                'contador_id': contador_id
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error al guardar tareas: {e}")


def cargar_tareas():
    global tareas, contador_id
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                tareas = data.get('tareas', [])
                contador_id = data.get('contador_id', 1)
                if tareas:
                    max_id = max(t.get('id', 0) for t in tareas)
                    contador_id = max(contador_id, max_id + 1)
        normalizar_tareas()
    except Exception as e:
        print(f"Error al cargar tareas: {e}")
        tareas = []
        contador_id = 1


def no_cache(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return wrapper


def normalizar_tareas():
    """Normaliza las tareas antiguas al nuevo formato"""
    global tareas
    cambios = False
    for t in tareas:
        # Migrar estados antiguos a nuevos
        estado_antiguo = t.get('situacion', 'Pendiente')
        if estado_antiguo == 'Pendiente':
            t['situacion'] = 'Sin Ejecutar'
            cambios = True
        elif estado_antiguo == 'Terminada':
            t['situacion'] = 'Completada'
            cambios = True
        elif estado_antiguo == 'Lista Para Validar':
            t['situacion'] = 'Pendiente de'
            cambios = True
        elif estado_antiguo not in ESTADOS:
            t['situacion'] = 'Sin Ejecutar'
            cambios = True
        
        # Asegurar que todos los campos existan
        t.setdefault('responsable', '')
        t.setdefault('centro_responsabilidad', '')
        t.setdefault('plazo', '')
        t.setdefault('documentos', [])
        t.setdefault('observacion', '')
        t.setdefault('recursos', '')
    
    if cambios:
        guardar_tareas()

# ================= LÓGICA DE TAREAS =================

def agregar_tarea(texto, responsable, centro, plazo, observacion, recursos):
    global contador_id
    tarea = {
        'id': contador_id,
        'texto': texto.strip(),
        'situacion': 'Sin Ejecutar',
        'responsable': responsable.strip(),
        'centro_responsabilidad': centro.strip(),
        'plazo': plazo.strip(),
        'observacion': observacion.strip(),
        'recursos': recursos.strip(),
        'documentos': []
    }
    tareas.append(tarea)
    contador_id += 1
    guardar_tareas()
    return tarea


def cambiar_estado(id, estado):
    for t in tareas:
        if t['id'] == id:
            if estado in ESTADOS:
                t['situacion'] = estado
                guardar_tareas()
                return True
    return False


def actualizar_tarea(id, responsable=None, centro=None, plazo=None, observacion=None, recursos=None):
    for t in tareas:
        if t['id'] == id:
            if responsable is not None:
                t['responsable'] = responsable.strip()
            if centro is not None:
                t['centro_responsabilidad'] = centro.strip()
            if plazo is not None:
                t['plazo'] = plazo.strip()
            if observacion is not None:
                t['observacion'] = observacion.strip()
            if recursos is not None:
                t['recursos'] = recursos.strip()
            guardar_tareas()
            return True
    return False


def agregar_documento(id, filename):
    for t in tareas:
        if t['id'] == id:
            if filename not in t['documentos']:
                t['documentos'].append(filename)
                guardar_tareas()
                return True
    return False


def obtener_tarea_por_id(id):
    for t in tareas:
        if t['id'] == id:
            return t
    return None

# ================= ESTADÍSTICAS =================

def obtener_estadisticas(tareas_filtradas=None):
    """Obtiene estadísticas completas de las tareas"""
    if tareas_filtradas is None:
        tareas_filtradas = tareas
    
    hoy = datetime.now().date()
    
    # Estadísticas por estado
    por_estado = {estado: 0 for estado in ESTADOS}
    for t in tareas_filtradas:
        estado = t.get('situacion', 'Sin Ejecutar')
        if estado in por_estado:
            por_estado[estado] += 1
    
    # Estadísticas por responsable
    por_responsable = {}
    for t in tareas_filtradas:
        resp = t.get('responsable', '') or 'Sin asignar'
        por_responsable[resp] = por_responsable.get(resp, 0) + 1
    
    # Estadísticas por centro
    por_centro = {}
    for t in tareas_filtradas:
        centro = t.get('centro_responsabilidad', '') or 'Sin asignar'
        por_centro[centro] = por_centro.get(centro, 0) + 1
    
    # Tareas por plazo
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
    
    return {
        'total': len(tareas_filtradas),
        'por_estado': por_estado,
        'por_responsable': por_responsable,
        'por_centro': por_centro,
        'vencidas': vencidas,
        'por_vencer': por_vencer,
        'sin_plazo': sin_plazo
    }


def filtrar_tareas(centro=None, responsable=None, estado=None, plazo=None):
    """Filtra las tareas según los criterios especificados"""
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
            tareas_filtradas = [
                t for t in tareas_filtradas
                if t.get('plazo') and datetime.strptime(t.get('plazo'), '%Y-%m-%d').date() < hoy
            ]
        elif plazo == 'por_vencer':
            tareas_filtradas = [
                t for t in tareas_filtradas
                if t.get('plazo') and datetime.strptime(t.get('plazo'), '%Y-%m-%d').date() >= hoy
            ]
        elif plazo == 'sin_plazo':
            tareas_filtradas = [t for t in tareas_filtradas if not t.get('plazo') or t.get('plazo') == '']
    
    return tareas_filtradas

# ================= ALERTAS POR CORREO =================

def obtener_tareas_por_vencer(dias_antes=2):
    """Obtiene tareas que vencen en los próximos días"""
    hoy = datetime.now().date()
    limite = hoy + timedelta(days=dias_antes)
    tareas_alertas = []
    
    for tarea in tareas:
        plazo_str = tarea.get('plazo', '')
        if not plazo_str:
            continue
        
        try:
            plazo_date = datetime.strptime(plazo_str, '%Y-%m-%d').date()
        except:
            continue
        
        # Solo tareas no completadas ni validadas
        situacion = tarea.get('situacion', '')
        if situacion in ('Completada', 'Validada'):
            continue
        
        if hoy <= plazo_date <= limite:
            tareas_alertas.append(tarea)
    
    return tareas_alertas


def enviar_alerta_correo(tareas_alertas):
    """Envía alerta por correo con las tareas por vencer"""
    # Configuración desde variables de entorno
    email_host = os.getenv('EMAIL_HOST', '')
    email_port = int(os.getenv('EMAIL_PORT', '587'))
    email_user = os.getenv('EMAIL_USER', '')
    email_password = os.getenv('EMAIL_PASSWORD', '')
    email_from = os.getenv('EMAIL_FROM', email_user)
    email_to = os.getenv('EMAIL_TO', '')
    
    if not (email_host and email_user and email_password and email_to):
        print("⚠️  Configuración de correo incompleta. Configure las variables de entorno:")
        print("   EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM, EMAIL_TO")
        return False
    
    if not tareas_alertas:
        return True
    
    # Preparar mensaje
    lineas = [
        "ALERTA: Tareas por vencer",
        "",
        f"Se encontraron {len(tareas_alertas)} tarea(s) por vencer en los próximos días:",
        ""
    ]
    
    for t in tareas_alertas:
        lineas.append(f"ID: {t['id']}")
        lineas.append(f"  Tarea: {t['texto']}")
        lineas.append(f"  Responsable: {t.get('responsable', 'Sin asignar')}")
        lineas.append(f"  Centro: {t.get('centro_responsabilidad', 'Sin asignar')}")
        lineas.append(f"  Plazo: {t.get('plazo', 'Sin plazo')}")
        lineas.append(f"  Estado: {t.get('situacion', 'Sin estado')}")
        lineas.append("")
    
    cuerpo = "\n".join(lineas)
    
    try:
        msg = EmailMessage()
        msg['Subject'] = f'[Gestor de Tareas] Alertas: {len(tareas_alertas)} tarea(s) por vencer'
        msg['From'] = email_from
        msg['To'] = email_to
        msg.set_content(cuerpo)
        
        with smtplib.SMTP(email_host, email_port) as server:
            server.starttls()
            server.login(email_user, email_password)
            server.send_message(msg)
        
        print(f"✅ Alerta enviada a {email_to} ({len(tareas_alertas)} tareas)")
        return True
    except Exception as e:
        print(f"❌ Error al enviar alerta por correo: {e}")
        return False


def iniciar_scheduler_alertas(intervalo_minutos=60):
    """Inicia el scheduler de alertas en segundo plano"""
    def worker():
        while True:
            try:
                cargar_tareas()
                tareas_alertas = obtener_tareas_por_vencer(dias_antes=2)
                if tareas_alertas:
                    enviar_alerta_correo(tareas_alertas)
                else:
                    print(f"⏰ Verificación de alertas: No hay tareas por vencer")
            except Exception as e:
                print(f"❌ Error en scheduler de alertas: {e}")
            time.sleep(intervalo_minutos * 60)
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    print(f"✅ Scheduler de alertas iniciado (verificación cada {intervalo_minutos} minutos)")

# ================= RUTAS =================

@app.route('/')
@no_cache
def index():
    cargar_tareas()
    return render_template('index.html', tareas=tareas, estados=ESTADOS)


@app.route('/agregar', methods=['POST'])
def agregar():
    texto = request.form.get('texto', '').strip()
    if texto:
        agregar_tarea(
            texto,
            request.form.get('responsable', ''),
            request.form.get('centro_responsabilidad', ''),
            request.form.get('plazo', ''),
            request.form.get('observacion', ''),
            request.form.get('recursos', '')
        )
    return redirect(url_for('index'))


@app.route('/cambiar_estado/<int:id>', methods=['POST'])
def cambiar_estado_route(id):
    estado = request.form.get('situacion', '')
    cambiar_estado(id, estado)
    return redirect(url_for('index'))


@app.route('/actualizar_tarea/<int:id>', methods=['POST'])
def actualizar_tarea_route(id):
    actualizar_tarea(
        id,
        request.form.get('responsable'),
        request.form.get('centro_responsabilidad'),
        request.form.get('plazo'),
        request.form.get('observacion'),
        request.form.get('recursos')
    )
    return redirect(url_for('index'))


@app.route('/adjuntar/<int:id>', methods=['POST'])
def adjuntar(id):
    file = request.files.get('documento')
    if file and file.filename and allowed_file(file.filename):
        name, ext = os.path.splitext(secure_filename(file.filename))
        if not name:
            name = 'documento'
        filename = f"{id}_{name}_{int(time.time() * 1000)}{ext}"
        filename = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        if os.path.exists(filepath):
            agregar_documento(id, filename)
    return redirect(url_for('index'))


@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/tablero')
@no_cache
def tablero():
    cargar_tareas()
    
    # Obtener filtros de la URL
    centro_filtro = request.args.get('centro', 'Todos')
    responsable_filtro = request.args.get('responsable', 'Todos')
    estado_filtro = request.args.get('estado', 'Todos')
    plazo_filtro = request.args.get('plazo', 'Todos')
    
    # Filtrar tareas
    tareas_filtradas = filtrar_tareas(
        centro=centro_filtro if centro_filtro != 'Todos' else None,
        responsable=responsable_filtro if responsable_filtro != 'Todos' else None,
        estado=estado_filtro if estado_filtro != 'Todos' else None,
        plazo=plazo_filtro if plazo_filtro != 'Todos' else None
    )
    
    # Estadísticas
    estadisticas = obtener_estadisticas(tareas_filtradas)
    estadisticas_totales = obtener_estadisticas()
    
    # Listas únicas para filtros
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
        filtros={
            'centro': centro_filtro,
            'responsable': responsable_filtro,
            'estado': estado_filtro,
            'plazo': plazo_filtro
        }
    )


@app.route('/api/estadisticas')
def api_estadisticas():
    """API para obtener estadísticas en formato JSON (para gráficos)"""
    cargar_tareas()
    estadisticas = obtener_estadisticas()
    return jsonify(estadisticas)


@app.route('/informe')
@no_cache
def informe():
    """Genera un informe completo del estado del arte"""
    cargar_tareas()
    
    estadisticas = obtener_estadisticas()
    hoy = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Tareas vencidas
    tareas_vencidas = [t for t in tareas if t.get('plazo') and 
                      datetime.strptime(t.get('plazo'), '%Y-%m-%d').date() < datetime.now().date()]
    
    # Tareas por vencer (próximos 7 días)
    limite = datetime.now().date() + timedelta(days=7)
    tareas_por_vencer = [
        t for t in tareas 
        if t.get('plazo') and 
        datetime.now().date() <= datetime.strptime(t.get('plazo'), '%Y-%m-%d').date() <= limite
    ]
    
    return render_template(
        'informe.html',
        estadisticas=estadisticas,
        tareas=tareas,
        tareas_vencidas=tareas_vencidas,
        tareas_por_vencer=tareas_por_vencer,
        fecha_reporte=hoy,
        estados=ESTADOS
    )


@app.route('/about')
def about():
    return render_template('about.html')

# ================= INICIO =================

if __name__ == '__main__':
    cargar_tareas()
    # Iniciar scheduler de alertas (verifica cada 60 minutos)
    iniciar_scheduler_alertas(intervalo_minutos=60)
    print("\n" + "="*50)
    print("🚀 Servidor Flask iniciado")
    print("📍 URL: http://localhost:5000/")
    print("📊 Tablero: http://localhost:5000/tablero")
    print("📄 Informe: http://localhost:5000/informe")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
