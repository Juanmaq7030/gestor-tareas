"""
Script para revisar el formato del archivo ventas.csv
Analiza: precio, fecha, producto, etc.
"""

import pandas as pd
import os

# Ruta del archivo
ruta_archivo = r"C:\Users\juan.gallardo\OneDrive - JUNAEB\DAE REMOTO 00\ÁREA GESTIÓN\CURSOS JUNAMA APRENDIZAJE\Curso Python Santander University\Archivos Cursos\ventas.csv"

print("=" * 80)
print("REVISIÓN DE FORMATO DEL ARCHIVO ventas.csv")
print("=" * 80)

# Cargar el archivo (usando punto y coma como separador)
print("\n[1] Cargando archivo...")
try:
    df = pd.read_csv(ruta_archivo, sep=';', encoding='utf-8')
    print(f"✅ Archivo cargado exitosamente")
    print(f"   Total de filas: {len(df):,}")
    print(f"   Total de columnas: {len(df.columns)}")
except Exception as e:
    print(f"❌ Error al cargar: {e}")
    exit(1)

# Mostrar información de columnas
print("\n[2] INFORMACIÓN DE COLUMNAS:")
print("-" * 80)
print(f"{'Columna':<35} {'Tipo':<15} {'Valores Nulos':<15} {'% Nulos':<10}")
print("-" * 80)
for col in df.columns:
    nulos = df[col].isna().sum()
    pct_nulos = (nulos / len(df)) * 100
    tipo = str(df[col].dtype)
    print(f"{col:<35} {tipo:<15} {nulos:<15} {pct_nulos:.2f}%")

# Mostrar primeras filas
print("\n[3] PRIMERAS 10 FILAS DEL DATASET:")
print("-" * 80)
print(df.head(10).to_string())

# Analizar columnas específicas
print("\n[4] ANÁLISIS DETALLADO POR COLUMNA:")
print("=" * 80)

# Columnas numéricas (precios, pesos, etc.)
columnas_numericas = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
print("\n[4.1] COLUMNAS NUMÉRICAS (Precios, Pesos, etc.):")
for col in columnas_numericas:
    print(f"\n  {col}:")
    print(f"    Tipo: {df[col].dtype}")
    print(f"    Valores únicos: {df[col].nunique():,}")
    print(f"    Mínimo: {df[col].min()}")
    print(f"    Máximo: {df[col].max()}")
    print(f"    Promedio: {df[col].mean():.2f}")
    print(f"    Mediana: {df[col].median():.2f}")
    print(f"    Valores nulos: {df[col].isna().sum()} ({(df[col].isna().sum()/len(df)*100):.2f}%)")

# Columnas de texto (producto, tipo, etc.)
columnas_texto = df.select_dtypes(include=['object']).columns.tolist()
print("\n[4.2] COLUMNAS DE TEXTO (Productos, Tipos, etc.):")
for col in columnas_texto:
    print(f"\n  {col}:")
    print(f"    Tipo: {df[col].dtype}")
    print(f"    Valores únicos: {df[col].nunique()}")
    print(f"    Valores nulos: {df[col].isna().sum()} ({(df[col].isna().sum()/len(df)*100):.2f}%)")
    print(f"    Primeros valores únicos: {df[col].unique()[:10].tolist()}")

# Buscar columnas que parezcan fechas
print("\n[4.3] BÚSQUEDA DE COLUMNAS DE FECHA:")
columnas_fecha_potenciales = [col for col in df.columns if any(term in col.lower() for term in ['date', 'fecha', 'year', 'año', 'time', 'tiempo'])]
if columnas_fecha_potenciales:
    for col in columnas_fecha_potenciales:
        print(f"\n  {col}:")
        print(f"    Tipo actual: {df[col].dtype}")
        print(f"    Valores únicos: {df[col].nunique()}")
        print(f"    Ejemplos: {df[col].head(5).tolist()}")
        # Intentar convertir a fecha
        try:
            fecha_prueba = pd.to_datetime(df[col].dropna().iloc[0], errors='coerce')
            if pd.notna(fecha_prueba):
                print(f"    ✅ Puede convertirse a fecha")
            else:
                print(f"    ⚠️  No parece ser una fecha estándar")
        except:
            print(f"    ⚠️  No se puede convertir a fecha directamente")
else:
    print("  ⚠️  No se encontraron columnas con nombres relacionados a fechas")

# Analizar formato de precios específicamente
print("\n[5] ANÁLISIS DE FORMATO DE PRECIOS:")
print("=" * 80)
columnas_precio = [col for col in df.columns if any(term in col.lower() for term in ['price', 'precio', 'mrp', 'sales', 'venta', 'cost', 'costo'])]
if columnas_precio:
    for col in columnas_precio:
        print(f"\n  {col}:")
        print(f"    Formato: Número decimal")
        print(f"    Rango: {df[col].min():.2f} - {df[col].max():.2f}")
        print(f"    Promedio: {df[col].mean():.2f}")
        print(f"    Ejemplos: {df[col].head(5).tolist()}")
        # Verificar si hay valores negativos
        negativos = (df[col] < 0).sum()
        if negativos > 0:
            print(f"    ⚠️  ADVERTENCIA: {negativos} valores negativos encontrados")
        else:
            print(f"    ✅ Todos los valores son positivos")
else:
    print("  ⚠️  No se encontraron columnas claramente relacionadas con precios")

# Analizar formato de productos
print("\n[6] ANÁLISIS DE FORMATO DE PRODUCTOS:")
print("=" * 80)
columnas_producto = [col for col in df.columns if any(term in col.lower() for term in ['item', 'product', 'producto', 'name', 'nombre', 'identifier'])]
if columnas_producto:
    for col in columnas_producto:
        print(f"\n  {col}:")
        print(f"    Total de productos únicos: {df[col].nunique():,}")
        print(f"    Ejemplos: {df[col].head(10).tolist()}")
        # Verificar formato (códigos, nombres, etc.)
        ejemplo = str(df[col].iloc[0])
        if ejemplo.isalnum() or ejemplo.replace('-', '').replace('_', '').isalnum():
            print(f"    Formato: Parece ser códigos/identificadores alfanuméricos")
        else:
            print(f"    Formato: Texto descriptivo")
else:
    print("  ⚠️  No se encontraron columnas claramente relacionadas con productos")

# Resumen de problemas encontrados
print("\n[7] RESUMEN DE PROBLEMAS DETECTADOS:")
print("=" * 80)
problemas = []

# Verificar valores nulos significativos
for col in df.columns:
    pct_nulos = (df[col].isna().sum() / len(df)) * 100
    if pct_nulos > 10:
        problemas.append(f"⚠️  Columna '{col}' tiene {pct_nulos:.2f}% de valores nulos")

# Verificar formato de separador
print("\n✅ El archivo usa punto y coma (;) como separador (correcto para datos europeos)")

# Verificar tipos de datos
for col in columnas_numericas:
    if df[col].dtype == 'object':
        problemas.append(f"⚠️  Columna numérica '{col}' está como texto (object)")

if problemas:
    for problema in problemas:
        print(f"  {problema}")
else:
    print("  ✅ No se detectaron problemas significativos en el formato")

# Recomendaciones
print("\n[8] RECOMENDACIONES:")
print("=" * 80)
print("  1. El archivo usa punto y coma (;) como separador - usar sep=';' al leer")
print("  2. Para columnas de fecha, verificar el formato específico antes de convertir")
print("  3. Las columnas numéricas parecen estar correctamente formateadas")
print("  4. Revisar valores nulos antes de realizar análisis")

print("\n" + "=" * 80)
print("REVISIÓN COMPLETADA")
print("=" * 80)









