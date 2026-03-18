# 📋 Planificador de Tareas - Instrucciones de Uso

## ✅ Funcionalidades Implementadas

### 1. Gestión de Tareas
- ✅ Crear tareas con descripción completa
- ✅ Asignar responsables a las tareas
- ✅ Asignar centros de responsabilidad
- ✅ Establecer plazos de entrega
- ✅ Añadir observaciones
- ✅ Especificar recursos necesarios
- ✅ Adjuntar documentos (Medios de Verificación)

### 2. Estados de Tareas
Las tareas pueden tener los siguientes estados:
- **Sin Ejecutar** - Tarea creada pero no iniciada
- **En Ejecución** - Tarea actualmente en progreso
- **Pendiente de** - Esperando validación o aprobación
- **Completada** - Tarea finalizada
- **Validada** - Tarea verificada y aprobada

### 3. Tablero de Control
- 📊 Estadísticas generales (total, vencidas, por vencer, etc.)
- 📈 Gráficos interactivos con Chart.js:
  - Distribución por Estado (gráfico de dona)
  - Distribución por Responsable (gráfico de barras)
  - Distribución por Centro de Responsabilidad (gráfico de barras)
- 🔍 Filtros avanzados:
  - Por Centro de Responsabilidad
  - Por Responsable
  - Por Estado
  - Por Plazo (vencidas, por vencer, sin plazo)

### 4. Sistema de Alertas por Correo
- ⏰ Verificación automática cada 60 minutos
- 📧 Notificaciones para tareas que vencen en los próximos 2 días
- ⚠️ Solo alerta tareas no completadas ni validadas

### 5. Informe del Estado del Arte
- 📄 Resumen ejecutivo con estadísticas clave
- 📊 Distribución por Estado, Responsable y Centro
- ⚠️ Listado de tareas vencidas
- ⏰ Listado de tareas por vencer (próximos 7 días)
- 📋 Listado completo de todas las tareas
- 💡 Análisis y recomendaciones automáticas

## 🚀 Inicio Rápido

### 1. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar Alertas por Correo (Opcional)
Antes de ejecutar la aplicación, configura las variables de entorno. Ver `config_email_example.txt` para más detalles.

**Windows PowerShell:**
```powershell
$env:EMAIL_HOST = "smtp.gmail.com"
$env:EMAIL_PORT = "587"
$env:EMAIL_USER = "tu_correo@gmail.com"
$env:EMAIL_PASSWORD = "tu_contraseña"
$env:EMAIL_FROM = "tu_correo@gmail.com"
$env:EMAIL_TO = "destinatario@dominio.com"
```

**Linux/Mac:**
```bash
export EMAIL_HOST="smtp.gmail.com"
export EMAIL_PORT="587"
export EMAIL_USER="tu_correo@gmail.com"
export EMAIL_PASSWORD="tu_contraseña"
export EMAIL_FROM="tu_correo@gmail.com"
export EMAIL_TO="destinatario@dominio.com"
```

### 3. Ejecutar la Aplicación
```bash
python app.py
```

La aplicación estará disponible en: `http://localhost:5000/`

## 📍 Rutas Disponibles

- `/` - Página principal (Lista de tareas y formulario)
- `/tablero` - Tablero de control con estadísticas y gráficos
- `/informe` - Informe completo del estado del arte
- `/about` - Información sobre la aplicación

## 📝 Uso de la Aplicación

### Crear una Nueva Tarea
1. En la página principal, completa el formulario:
   - Descripción de la tarea (obligatorio)
   - Responsable (opcional)
   - Centro de Responsabilidad (opcional)
   - Plazo (opcional)
   - Observaciones (opcional)
   - Recursos (opcional)
2. Haz clic en "Agregar Tarea"

### Modificar una Tarea
1. En cada tarea, puedes:
   - Cambiar el estado usando el menú desplegable
   - Actualizar responsable, centro, plazo, observaciones y recursos
   - Adjuntar documentos (Medios de Verificación)
2. Los cambios se guardan automáticamente

### Usar el Tablero de Control
1. Accede a "Tablero de Control" desde el menú
2. Usa los filtros para ver tareas específicas
3. Visualiza las estadísticas y gráficos
4. Haz clic en "Aplicar Filtros" para actualizar la vista

### Generar Informe
1. Accede a "Informe" desde el menú
2. El informe se genera automáticamente con todos los datos
3. Usa el botón "Imprimir Informe" para generar una versión imprimible

## 🔧 Configuración Avanzada

### Cambiar Intervalo de Verificación de Alertas
En `app.py`, línea final del archivo, modifica:
```python
iniciar_scheduler_alertas(intervalo_minutos=60)  # Cambia 60 por el valor deseado
```

### Cambiar Días de Anticipación para Alertas
En `app.py`, función `obtener_tareas_por_vencer()`, modifica:
```python
tareas_alertas = obtener_tareas_por_vencer(dias_antes=2)  # Cambia 2 por el valor deseado
```

## 📦 Estructura de Datos

Las tareas se guardan en `tareas.json` con la siguiente estructura:
```json
{
  "id": 1,
  "texto": "Descripción de la tarea",
  "situacion": "Sin Ejecutar",
  "responsable": "Nombre del responsable",
  "centro_responsabilidad": "Nombre del centro",
  "plazo": "2024-12-31",
  "observacion": "Observaciones adicionales",
  "recursos": "Recursos necesarios",
  "documentos": ["archivo1.pdf", "archivo2.docx"]
}
```

## 🛠️ Solución de Problemas

### Las alertas por correo no se envían
- Verifica que todas las variables de entorno estén configuradas
- Asegúrate de que las credenciales sean correctas
- Para Gmail, es posible que necesites usar una "Contraseña de aplicación"
- Revisa los logs de la consola para ver mensajes de error

### Los gráficos no se muestran
- Verifica tu conexión a internet (Chart.js se carga desde CDN)
- Revisa la consola del navegador para errores de JavaScript

### Las tareas no se guardan
- Verifica que tengas permisos de escritura en el directorio
- Revisa que `tareas.json` exista y sea accesible

## 📞 Soporte

Para más información, consulta:
- La página "Acerca de" en la aplicación
- Los comentarios en el código fuente
- Los archivos de documentación incluidos

---

**Versión:** 2.0  
**Última actualización:** 2024














