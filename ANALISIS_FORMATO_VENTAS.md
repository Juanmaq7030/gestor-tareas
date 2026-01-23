# 📊 Análisis del Formato del Archivo ventas.csv

## Resumen Ejecutivo

- **Archivo:** `ventas.csv`
- **Ubicación:** `C:\Users\juan.gallardo\OneDrive - JUNAEB\DAE REMOTO 00\ÁREA GESTIÓN\CURSOS JUANMA APRENDIZAJE\Curso Python Santander University\Archivos Cursos`
- **Separador:** Punto y coma (`;`)
- **Total de filas:** ~8,525 filas (incluyendo encabezado)
- **Total de columnas:** 12 columnas

---

## Estructura de Columnas

| # | Nombre de Columna | Tipo de Dato | Descripción |
|---|-------------------|--------------|-------------|
| 1 | `Item_Identifier` | Texto (object) | Identificador único del producto |
| 2 | `Item_Weight` | Numérico (float) | Peso del producto (puede tener valores nulos) |
| 3 | `Item_Fat_Content` | Texto (object) | Contenido de grasa (Low Fat, Regular, LF, low fat, reg) |
| 4 | `Item_Visibility` | Numérico (float) | Visibilidad del producto (0 a 1) |
| 5 | `Item_Type` | Texto (object) | Tipo/categoría del producto |
| 6 | `Item_MRP` | Numérico (float) | Precio máximo de venta minorista (MRP) |
| 7 | `Outlet_Identifier` | Texto (object) | Identificador del punto de venta |
| 8 | `Outlet_Establishment_Year` | Numérico (int) | Año de establecimiento del punto de venta |
| 9 | `Outlet_Size` | Texto (object) | Tamaño del punto de venta (puede tener valores nulos) |
| 10 | `Outlet_Location_Type` | Texto (object) | Tipo de ubicación (Tier 1, Tier 2, Tier 3) |
| 11 | `Outlet_Type` | Texto (object) | Tipo de tienda |
| 12 | `Item_Outlet_Sales` | Numérico (float) | Ventas del producto en el punto de venta |

---

## Análisis Detallado por Tipo de Campo

### 1. Precios (Item_MRP y Item_Outlet_Sales)

**Formato:** Números decimales con punto como separador decimal

**Ejemplos:**
- `Item_MRP`: 249.8092, 48.2692, 141.618
- `Item_Outlet_Sales`: 3735.138, 443.4228, 2097.27

**Características:**
- ✅ Formato estándar: números decimales
- ✅ No contienen símbolos de moneda
- ✅ Usan punto (.) como separador decimal
- ✅ Sin separadores de miles (comas o puntos)

**Para leer en pandas:**
```python
df = pd.read_csv('ventas.csv', sep=';')
# Las columnas numéricas se leerán automáticamente como float64
```

---

### 2. Fechas (Outlet_Establishment_Year)

**Formato:** Año numérico (4 dígitos)

**Ejemplos:** 1999, 2009, 1998, 1987

**Características:**
- ✅ Formato simple: solo el año
- ✅ No es una fecha completa (solo año)
- ✅ Valores numéricos enteros

**Para convertir a fecha completa (opcional):**
```python
# Convertir año a fecha completa
df['Outlet_Establishment_Date'] = pd.to_datetime(
    df['Outlet_Establishment_Year'].astype(str) + '-01-01'
)
```

---

### 3. Productos (Item_Identifier y Item_Type)

#### Item_Identifier
**Formato:** Códigos alfanuméricos

**Ejemplos:** FDA15, DRC01, FDN15, FDX07, NCD19

**Características:**
- ✅ Códigos cortos (3-5 caracteres)
- ✅ Combinación de letras y números
- ✅ Parecen seguir un patrón (FD, DR, NC, etc.)

#### Item_Type
**Formato:** Texto descriptivo (categorías)

**Ejemplos:** 
- Dairy, Soft Drinks, Meat, Fruits and Vegetables
- Household, Baking Goods, Snack Foods
- Breakfast, Health and Hygiene, Frozen Foods
- Hard Drinks, Canned, Breads, Starchy Foods

**Características:**
- ✅ Texto en inglés
- ✅ Categorías claramente definidas
- ✅ Mayúsculas en cada palabra

---

### 4. Valores Nulos y Vacíos

**Columnas con valores nulos detectados:**
- `Item_Weight`: Algunos valores vacíos (ejemplo línea 9: `FDP10;;Low Fat`)
- `Outlet_Size`: Algunos valores vacíos (ejemplo línea 5: `FDX07;...;;Tier 3`)

**Representación de valores nulos:**
- Se representan como campos vacíos entre punto y coma: `;;`
- Pandas los interpretará como `NaN`

**Manejo recomendado:**
```python
# Leer el archivo
df = pd.read_csv('ventas.csv', sep=';')

# Verificar valores nulos
print(df.isnull().sum())

# Opciones para manejar nulos:
# - Eliminar filas: df.dropna()
# - Llenar con valores por defecto: df.fillna(0) o df.fillna('Unknown')
```

---

### 5. Inconsistencias en Texto

**Item_Fat_Content:**
Se encontraron variaciones en el formato:
- ✅ "Low Fat" (mayoría)
- ⚠️ "LF" (abreviación)
- ⚠️ "low fat" (minúsculas)
- ⚠️ "Regular" (mayoría)
- ⚠️ "reg" (abreviación)

**Recomendación:** Normalizar estos valores antes del análisis:
```python
# Normalizar Item_Fat_Content
df['Item_Fat_Content'] = df['Item_Fat_Content'].str.lower()
df['Item_Fat_Content'] = df['Item_Fat_Content'].replace({
    'lf': 'low fat',
    'reg': 'regular'
})
```

---

## Ejemplo de Línea Completa

```
FDA15;9.3;Low Fat;0.016047301;Dairy;249.8092;OUT049;1999;Medium;Tier 1;Supermarket Type1;3735.138
```

**Desglose:**
- Item_Identifier: `FDA15`
- Item_Weight: `9.3`
- Item_Fat_Content: `Low Fat`
- Item_Visibility: `0.016047301`
- Item_Type: `Dairy`
- Item_MRP: `249.8092` (precio)
- Outlet_Identifier: `OUT049`
- Outlet_Establishment_Year: `1999` (año)
- Outlet_Size: `Medium`
- Outlet_Location_Type: `Tier 1`
- Outlet_Type: `Supermarket Type1`
- Item_Outlet_Sales: `3735.138` (ventas)

---

## Código de Ejemplo para Leer el Archivo

```python
import pandas as pd

# Leer el archivo
ruta_archivo = r"C:\Users\juan.gallardo\OneDrive - JUNAEB\DAE REMOTO 00\ÁREA GESTIÓN\CURSOS JUANMA APRENDIZAJE\Curso Python Santander University\Archivos Cursos\ventas.csv"

df = pd.read_csv(ruta_archivo, sep=';', encoding='utf-8')

# Verificar tipos de datos
print(df.dtypes)

# Ver primeras filas
print(df.head())

# Verificar valores nulos
print(df.isnull().sum())

# Normalizar Item_Fat_Content
df['Item_Fat_Content'] = df['Item_Fat_Content'].str.title()
df['Item_Fat_Content'] = df['Item_Fat_Content'].replace({
    'Lf': 'Low Fat',
    'Reg': 'Regular'
})
```

---

## Resumen de Recomendaciones

### ✅ Formato Correcto
1. **Separador:** Punto y coma (`;`) - usar `sep=';'` al leer
2. **Precios:** Números decimales estándar - se leen automáticamente como float
3. **Años:** Números enteros - se leen como int

### ⚠️ Atención Requerida
1. **Valores nulos:** Revisar y manejar `Item_Weight` y `Outlet_Size`
2. **Inconsistencias en texto:** Normalizar `Item_Fat_Content`
3. **Codificación:** Verificar encoding (probablemente UTF-8)

### 📝 Para Análisis
1. `Item_MRP` = Precio del producto
2. `Item_Outlet_Sales` = Ventas totales del producto
3. `Outlet_Establishment_Year` = Año (convertir a fecha si es necesario)
4. `Item_Type` = Categoría/Tipo de producto
5. No hay columna de fecha de venta directa, solo año de establecimiento

---

**Fecha de análisis:** 2024  
**Versión del documento:** 1.0









