# Script para crear la Lista de SharePoint
# Ejecutar despuÃ©s de conectarse a SharePoint Online

# Instalar mÃ³dulo si no estÃ¡ instalado
# Install-Module -Name PnP.PowerShell

# Conectar a SharePoint
# Connect-PnPOnline -Url "https://tuorganizacion.sharepoint.com" -Interactive

# Crear la lista de Tareas
New-PnPList -Title "Tareas" -Template GenericList -Url "Lists/Tareas"

# Agregar columnas
Add-PnPField -List "Tareas" -DisplayName "Texto" -InternalName "Texto" -Type Text -Required
Add-PnPField -List "Tareas" -DisplayName "Situacion" -InternalName "Situacion" -Type Choice -Choices "Pendiente","En EjecuciÃ³n","Terminada","Lista Para Validar" -Required
Add-PnPField -List "Tareas" -DisplayName "Responsable" -InternalName "Responsable" -Type User -Required:False
Add-PnPField -List "Tareas" -DisplayName "CentroResponsabilidad" -InternalName "CentroResponsabilidad" -Type Text -Required:False
Add-PnPField -List "Tareas" -DisplayName "Plazo" -InternalName "Plazo" -Type DateTime -Required:False -DateTimeFieldFormat DateOnly

# Habilitar archivos adjuntos
Set-PnPList -Identity "Tareas" -EnableAttachments

Write-Host "Lista 'Tareas' creada exitosamente" -ForegroundColor Green
