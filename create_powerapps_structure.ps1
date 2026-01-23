# Script PowerShell para crear estructura de Power Apps
# Este script ayuda a preparar el entorno para migrar a Power Apps

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Script de Preparación para Power Apps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si el usuario está conectado a SharePoint Online
Write-Host "PASO 1: Verificar conexión a SharePoint Online" -ForegroundColor Yellow
Write-Host "Por favor, ejecuta manualmente:" -ForegroundColor White
Write-Host "  Connect-PnPOnline -Url 'https://tuorganizacion.sharepoint.com' -Interactive" -ForegroundColor Green
Write-Host ""

# Crear script para la lista de SharePoint
$sharepointScript = @"
# Script para crear la Lista de SharePoint
# Ejecutar después de conectarse a SharePoint Online

# Instalar módulo si no está instalado
# Install-Module -Name PnP.PowerShell

# Conectar a SharePoint
# Connect-PnPOnline -Url "https://tuorganizacion.sharepoint.com" -Interactive

# Crear la lista de Tareas
New-PnPList -Title "Tareas" -Template GenericList -Url "Lists/Tareas"

# Agregar columnas
Add-PnPField -List "Tareas" -DisplayName "Texto" -InternalName "Texto" -Type Text -Required
Add-PnPField -List "Tareas" -DisplayName "Situacion" -InternalName "Situacion" -Type Choice -Choices "Pendiente","En Ejecución","Terminada","Lista Para Validar" -Required
Add-PnPField -List "Tareas" -DisplayName "Responsable" -InternalName "Responsable" -Type User -Required:$false
Add-PnPField -List "Tareas" -DisplayName "CentroResponsabilidad" -InternalName "CentroResponsabilidad" -Type Text -Required:$false
Add-PnPField -List "Tareas" -DisplayName "Plazo" -InternalName "Plazo" -Type DateTime -Required:$false -DateTimeFieldFormat DateOnly

# Habilitar archivos adjuntos
Set-PnPList -Identity "Tareas" -EnableAttachments

Write-Host "Lista 'Tareas' creada exitosamente" -ForegroundColor Green
"@

# Guardar script de SharePoint
$sharepointScript | Out-File -FilePath "create_sharepoint_list.ps1" -Encoding UTF8
Write-Host "✓ Script de SharePoint creado: create_sharepoint_list.ps1" -ForegroundColor Green
Write-Host ""

# Crear archivo de configuración JSON
$config = @{
    "AppName" = "Gestor de Tareas"
    "SharePointSite" = "https://tuorganizacion.sharepoint.com"
    "ListName" = "Tareas"
    "Columns" = @{
        "Texto" = "Text"
        "Situacion" = "Choice"
        "Responsable" = "User"
        "CentroResponsabilidad" = "Text"
        "Plazo" = "DateTime"
    }
    "Estados" = @("Pendiente", "En Ejecución", "Terminada", "Lista Para Validar")
} | ConvertTo-Json -Depth 10

$config | Out-File -FilePath "powerapps_config.json" -Encoding UTF8
Write-Host "✓ Archivo de configuración creado: powerapps_config.json" -ForegroundColor Green
Write-Host ""

# Crear checklist de implementación
$checklistContent = @'
# Checklist de Implementación en Power Apps

## Preparación
- [ ] Instalar Power Apps CLI
- [ ] Tener acceso a SharePoint Online o Dataverse
- [ ] Tener permisos de administrador o creador de apps

## Crear Datasource
- [ ] Ejecutar create_sharepoint_list.ps1
- [ ] Verificar que la lista se creó correctamente
- [ ] Agregar algunos datos de prueba

## Crear Aplicación
- [ ] Ir a https://make.powerapps.com
- [ ] Crear nueva app desde SharePoint
- [ ] Seleccionar la lista "Tareas"
- [ ] Power Apps generará automáticamente las pantallas básicas

## Personalizar Pantallas
- [ ] Pantalla Principal (BrowseScreen)
  - [ ] Personalizar galería con colores por estado
  - [ ] Agregar filtros (Centro, Responsable, Estado, Plazo)
  - [ ] Agregar botón "Nueva Tarea"
  - [ ] Agregar botón "Tablero de Control"
  
- [ ] Pantalla de Detalles (DetailScreen)
  - [ ] Personalizar formulario de edición
  - [ ] Agregar control de archivos adjuntos
  - [ ] Agregar validaciones
  
- [ ] Pantalla de Nueva Tarea (NewScreen)
  - [ ] Configurar formulario con todos los campos
  - [ ] Agregar validaciones
  
- [ ] Pantalla de Tablero (DashboardScreen)
  - [ ] Crear tarjetas de estadísticas
  - [ ] Agregar gráficos (opcional)
  - [ ] Implementar filtros avanzados

## Fórmulas
- [ ] Copiar fórmulas de POWER_APPS_FORMULAS.txt
- [ ] Aplicar a controles correspondientes
- [ ] Probar cada funcionalidad

## Pruebas
- [ ] Crear nueva tarea
- [ ] Editar tarea existente
- [ ] Cambiar estado
- [ ] Adjuntar documento
- [ ] Filtrar tareas
- [ ] Ver tablero de control
- [ ] Probar en dispositivo móvil

## Publicación
- [ ] Guardar aplicación
- [ ] Publicar aplicación
- [ ] Compartir con usuarios
- [ ] Configurar permisos

## Documentación
- [ ] Documentar para usuarios finales
- [ ] Crear guía de uso
- [ ] Capacitar usuarios
'@

$checklistContent | Out-File -FilePath "IMPLEMENTATION_CHECKLIST.md" -Encoding UTF8
Write-Host "✓ Checklist creado: IMPLEMENTATION_CHECKLIST.md" -ForegroundColor Green
Write-Host ""

# Crear guía rápida
$quickGuideContent = @'
# Guía Rápida: Crear App en Power Apps

## Opción 1: Desde SharePoint (Recomendado para empezar)

1. Ve a https://make.powerapps.com
2. Click en "Crear" > "Aplicación desde datos"
3. Selecciona "SharePoint"
4. Elige tu sitio y la lista "Tareas"
5. Power Apps creará automáticamente:
   - Pantalla de exploración (lista)
   - Pantalla de detalles (edición)
   - Pantalla de nuevo elemento

## Opción 2: App en blanco

1. Ve a https://make.powerapps.com
2. Click en "Crear" > "Aplicación en blanco"
3. Agrega conexión a SharePoint
4. Crea las pantallas manualmente
5. Usa las fórmulas de POWER_APPS_FORMULAS.txt

## Personalización Rápida

### Cambiar color de fondo según estado:
1. Selecciona el control de la galería
2. En la propiedad Fill, usa la fórmula del archivo POWER_APPS_FORMULAS.txt

### Agregar filtros:
1. Agrega controles Dropdown
2. En la propiedad Items de la galería, usa Filter() con los dropdowns

### Agregar tablero:
1. Crea nueva pantalla "DashboardScreen"
2. Agrega controles Label para estadísticas
3. Usa fórmulas CountRows() y Filter()

## Recursos Útiles

- Documentación: https://docs.microsoft.com/powerapps
- Comunidad: https://powerusers.microsoft.com
- Fórmulas: Ver POWER_APPS_FORMULAS.txt
'@

$quickGuideContent | Out-File -FilePath "QUICK_START_GUIDE.md" -Encoding UTF8
Write-Host "✓ Guía rápida creada: QUICK_START_GUIDE.md" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Archivos creados exitosamente:" -ForegroundColor Green
Write-Host "  1. create_sharepoint_list.ps1" -ForegroundColor White
Write-Host "  2. powerapps_config.json" -ForegroundColor White
Write-Host "  3. IMPLEMENTATION_CHECKLIST.md" -ForegroundColor White
Write-Host "  4. QUICK_START_GUIDE.md" -ForegroundColor White
Write-Host "  5. POWER_APPS_FORMULAS.txt" -ForegroundColor White
Write-Host "  6. POWER_APPS_MIGRATION.md" -ForegroundColor White
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "  1. Revisa POWER_APPS_MIGRATION.md para la guía completa" -ForegroundColor White
Write-Host "  2. Ejecuta create_sharepoint_list.ps1 para crear la lista" -ForegroundColor White
Write-Host "  3. Sigue QUICK_START_GUIDE.md para crear la app" -ForegroundColor White
Write-Host "  4. Usa POWER_APPS_FORMULAS.txt para las fórmulas" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan

