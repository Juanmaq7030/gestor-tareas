# 📊 Ejemplos de Uso del Módulo de Análisis

## Instalación

Primero, instala las dependencias necesarias:

```bash
pip install -r requirements.txt
```

Esto instalará:
- pandas (análisis de datos)
- matplotlib (gráficos)
- openpyxl (exportación a Excel)

## Uso Básico

### 1. Generar Reporte Completo

La forma más simple de usar el módulo es ejecutarlo directamente:

```bash
python analisis.py
```

Esto generará:
- 📊 Todos los gráficos en formato PNG
- 📁 Archivo CSV con todas las tareas
- 📁 Archivo Excel con múltiples hojas
- Todos los archivos se guardan en la carpeta `analisis_output/`

### 2. Uso Programático

Puedes importar y usar las funciones en tu código:

```python
from analisis import (
    cargar_tareas,
    analisis_general,
    grafico_distribucion_estados,
    exportar_a_excel,
    analisis_eficiencia
)

# Cargar datos
df = cargar_tareas()

# Análisis general
estadisticas = analisis_general(df)
print(f"Total de tareas: {estadisticas['total_tareas']}")
print(f"Tareas vencidas: {estadisticas['tareas_vencidas']}")

# Generar gráfico
grafico_distribucion_estados(df, guardar=True)

# Exportar a Excel
exportar_a_excel(df, 'mi_reporte.xlsx')

# Análisis de eficiencia
eficiencia = analisis_eficiencia(df)
print(f"Tasa de completación: {eficiencia['tasa_completacion']:.2f}%")
```

## Funciones Disponibles

### Carga de Datos

#### `cargar_tareas() -> pd.DataFrame`
Carga las tareas desde `tareas.json` y las convierte en un DataFrame de pandas.

```python
df = cargar_tareas()
print(df.head())
```

### Análisis Estadístico

#### `analisis_general(df: pd.DataFrame) -> Dict`
Retorna un diccionario con estadísticas generales:
- Total de tareas
- Distribución por estado
- Distribución por responsable
- Distribución por centro
- Tareas vencidas y por vencer
- Estadísticas de documentos

```python
estadisticas = analisis_general(df)
for clave, valor in estadisticas.items():
    print(f"{clave}: {valor}")
```

#### `analisis_eficiencia(df: pd.DataFrame) -> Dict`
Analiza la eficiencia en la gestión:
- Tasa de completación
- Tasa de tareas en progreso
- Tasa de tareas sin ejecutar

```python
eficiencia = analisis_eficiencia(df)
print(f"Tasa de completación: {eficiencia['tasa_completacion']:.2f}%")
```

### Generación de Gráficos

#### `grafico_distribucion_estados(df, guardar=True) -> str`
Gráfico de barras mostrando distribución por estado.

```python
ruta = grafico_distribucion_estados(df)
# Si guardar=True: guarda en analisis_output/distribucion_estados.png
# Si guardar=False: muestra el gráfico en pantalla
```

#### `grafico_distribucion_responsables(df, top_n=10, guardar=True) -> str`
Gráfico de barras horizontales con los principales responsables.

```python
ruta = grafico_distribucion_responsables(df, top_n=5)
```

#### `grafico_distribucion_centros(df, guardar=True) -> str`
Gráfico de pastel (pie chart) con distribución por centros.

```python
ruta = grafico_distribucion_centros(df)
```

#### `grafico_linea_temporal(df, guardar=True) -> str`
Gráfico de línea temporal mostrando tareas por fecha de plazo.

```python
ruta = grafico_linea_temporal(df)
```

#### `grafico_estado_plazo(df, guardar=True) -> str`
Gráfico de barras apiladas mostrando relación entre estado y plazo.

```python
ruta = grafico_estado_plazo(df)
```

### Exportación de Datos

#### `exportar_a_excel(df, nombre_archivo='tareas_analisis.xlsx') -> str`
Exporta a Excel con múltiples hojas:
- Todas las Tareas
- Resumen por Estado
- Resumen por Responsable
- Resumen por Centro
- Tareas Vencidas

```python
ruta = exportar_a_excel(df, 'reporte_completo.xlsx')
```

#### `exportar_a_csv(df, nombre_archivo='tareas_analisis.csv') -> str`
Exporta a CSV (formato simple de texto).

```python
ruta = exportar_a_csv(df, 'mis_tareas.csv')
```

### Función Principal

#### `generar_reporte_completo()`
Genera automáticamente todos los gráficos y exportaciones.

```python
from analisis import generar_reporte_completo

generar_reporte_completo()
```

## Ejemplos Avanzados

### Filtrar y Analizar Subconjuntos

```python
import pandas as pd
from analisis import cargar_tareas, grafico_distribucion_estados

df = cargar_tareas()

# Filtrar solo tareas vencidas
tareas_vencidas = df[df['vencida'] == True]
print(f"Tareas vencidas: {len(tareas_vencidas)}")

# Filtrar por centro específico
tareas_dae = df[df['centro_responsabilidad'] == 'DAE']
print(f"Tareas del centro DAE: {len(tareas_dae)}")

# Filtrar por responsable
tareas_juan = df[df['responsable'] == 'Juan Manuel Gallardo']
print(f"Tareas de Juan: {len(tareas_juan)}")
```

### Análisis Temporal

```python
from analisis import cargar_tareas
import pandas as pd

df = cargar_tareas()

# Tareas por mes (si tienes fechas de creación)
if 'plazo_date' in df.columns:
    df['mes'] = df['plazo_date'].dt.to_period('M')
    tareas_por_mes = df.groupby('mes').size()
    print(tareas_por_mes)
```

### Personalizar Gráficos

```python
import matplotlib.pyplot as plt
from analisis import cargar_tareas

df = cargar_tareas()

# Crear gráfico personalizado
fig, ax = plt.subplots(figsize=(10, 6))

estados = df['situacion'].value_counts()
ax.bar(estados.index, estados.values, color='#3498db')
ax.set_title('Mi Gráfico Personalizado')
ax.set_xlabel('Estado')
ax.set_ylabel('Cantidad')

plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('mi_grafico.png', dpi=300)
plt.close()
```

## Integración con Flask

Puedes integrar el análisis en tu aplicación Flask creando rutas:

```python
from flask import send_file
from analisis import cargar_tareas, exportar_a_excel, grafico_distribucion_estados

@app.route('/analisis/excel')
def descargar_analisis_excel():
    df = cargar_tareas()
    ruta = exportar_a_excel(df, 'analisis_tareas.xlsx')
    return send_file(ruta, as_attachment=True)

@app.route('/analisis/grafico-estados')
def ver_grafico_estados():
    df = cargar_tareas()
    ruta = grafico_distribucion_estados(df)
    return send_file(ruta, mimetype='image/png')
```

## Estructura de Salida

Todos los archivos generados se guardan en la carpeta `analisis_output/`:

```
analisis_output/
├── distribucion_estados.png
├── distribucion_responsables.png
├── distribucion_centros.png
├── linea_temporal.png
├── estado_plazo.png
├── tareas_analisis.csv
└── tareas_analisis.xlsx
```

## Notas Importantes

1. **Formato de Datos**: El módulo espera que las tareas estén en `tareas.json` con el formato estándar de la aplicación.

2. **Gráficos**: Los gráficos se guardan en alta resolución (300 DPI) para impresión.

3. **Excel**: Requiere `openpyxl`. Si no está instalado, la exportación a Excel fallará con un mensaje claro.

4. **Fechas**: Las fechas deben estar en formato 'YYYY-MM-DD' para ser procesadas correctamente.

5. **Memoria**: Para datasets muy grandes (>10,000 tareas), considera usar filtros antes de generar gráficos.

## Solución de Problemas

### Error: "No module named 'pandas'"
```bash
pip install pandas matplotlib openpyxl
```

### Error: "No module named 'openpyxl'"
```bash
pip install openpyxl
```

### Los gráficos no se muestran
- Si usas `guardar=False`, asegúrate de tener una interfaz gráfica disponible
- En servidores sin GUI, siempre usa `guardar=True`

### Error al exportar a Excel
- Verifica que `openpyxl` esté instalado
- Asegúrate de tener permisos de escritura en `analisis_output/`

---

Para más información, consulta los comentarios en el código fuente de `analisis.py`.













