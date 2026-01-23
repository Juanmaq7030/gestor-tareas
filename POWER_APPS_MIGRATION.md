# Guía de Migración a Power Apps

## Descripción General

Esta guía describe cómo recrear el Gestor de Tareas en Power Apps con todas las funcionalidades implementadas en Flask.

## Funcionalidades a Implementar

1. ✅ Lista de tareas con estados (Pendiente, En Ejecución, Terminada, Lista Para Validar)
2. ✅ Agregar nuevas tareas
3. ✅ Asignar Responsable
4. ✅ Asignar Centro de Responsabilidad
5. ✅ Establecer Plazo (fecha límite)
6. ✅ Cambiar estado de tareas
7. ✅ Adjuntar documentos de verificación
8. ✅ Tablero de control con filtros y estadísticas

## Arquitectura en Power Apps

### Datasource: SharePoint List o Dataverse

**Recomendación: SharePoint List** (más fácil de configurar)

### Estructura de la Lista de SharePoint

| Nombre de Columna | Tipo | Requerido | Descripción |
|------------------|------|-----------|-------------|
| ID | Número (Auto) | Sí | ID único de la tarea |
| Texto | Texto de una línea | Sí | Descripción de la tarea |
| Situacion | Elección | Sí | Estado: Pendiente, En Ejecución, Terminada, Lista Para Validar |
| Responsable | Persona | No | Responsable asignado |
| CentroResponsabilidad | Texto de una línea | No | Centro de responsabilidad |
| Plazo | Fecha | No | Fecha límite |
| Documentos | Archivos adjuntos | No | Documentos de verificación |

## Pasos de Implementación

### Paso 1: Crear la Lista de SharePoint

1. Ve a SharePoint Online
2. Crea una nueva lista llamada "Tareas"
3. Agrega las columnas según la tabla anterior
4. Para "Situacion", crea opciones:
   - Pendiente
   - En Ejecución
   - Terminada
   - Lista Para Validar

### Paso 2: Crear la Aplicación Power Apps

1. Ve a https://make.powerapps.com
2. Crea una nueva aplicación desde SharePoint
3. Selecciona la lista "Tareas"
4. Power Apps generará automáticamente una app con formularios básicos

### Paso 3: Personalizar la Aplicación

Ver archivo `POWER_APPS_FORMULAS.txt` para las fórmulas específicas.

## Pantallas Necesarias

1. **Pantalla Principal (BrowseScreen)**
   - Galería de tareas
   - Filtros
   - Botón para agregar nueva tarea

2. **Pantalla de Detalles (DetailScreen)**
   - Formulario de edición
   - Campos: Texto, Situación, Responsable, Centro, Plazo
   - Botón para adjuntar documentos
   - Lista de documentos adjuntos

3. **Pantalla de Tablero (DashboardScreen)**
   - Tarjetas de estadísticas
   - Gráficos
   - Filtros avanzados

4. **Pantalla de Nueva Tarea (NewScreen)**
   - Formulario para crear nueva tarea

## Fórmulas Clave

Ver archivo `POWER_APPS_FORMULAS.txt` para fórmulas detalladas.

## Consideraciones Importantes

1. **Permisos**: Asegúrate de que los usuarios tengan permisos en SharePoint
2. **Archivos Adjuntos**: SharePoint Lists tiene límites en archivos adjuntos
3. **Rendimiento**: Para muchas tareas, considera usar Dataverse en lugar de SharePoint
4. **Filtros**: Implementa filtros en la galería usando la propiedad Items

## Alternativa: Dataverse

Para aplicaciones más robustas, considera usar Dataverse:
- Mejor rendimiento
- Más opciones de relaciones
- Mejor manejo de archivos
- Capacidades avanzadas de seguridad














