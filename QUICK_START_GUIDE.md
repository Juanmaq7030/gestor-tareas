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














