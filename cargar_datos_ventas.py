"""
Script para cargar datos del archivo ventas.csv usando pandas
"""

from sre_parse import BIGCHARSET
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# ============================================================================
# 1. CONFIGURACIÓN DE RUTAS
# ============================================================================

# Ruta del archivo CSV
RUTA_ARCHIVO = r"C:\Users\juan.gallardo\OneDrive - JUNAEB\DAE REMOTO 00\ÁREA GESTIÓN\CURSOS JUANMA APRENDIZAJE\Curso Python Santander University\Archivos Cursos\ventas.csv"

# ============================================================================
# 2. CARGAR DATOS CON PANDAS
# ============================================================================

def cargar_datos_ventas(ruta_archivo=None):
    """
    Carga los datos del archivo ventas.csv usando pandas.
    
    Args:
        ruta_archivo (str): Ruta completa al archivo CSV. Si es None, usa la ruta por defecto.
        
    Returns:
        pd.DataFrame: DataFrame con los datos cargados
    """
    if ruta_archivo is None:
        ruta_archivo = RUTA_ARCHIVO
    
    print("=" * 80)
    print("CARGANDO DATOS CON PANDAS")
    print("=" * 80)
    
    # 2.1. Verificar que el archivo existe
    if not os.path.exists(ruta_archivo):
        print(f"❌ Error: El archivo no existe en la ruta especificada:")
        print(f"   {ruta_archivo}")
        return None
    
    print(f"\n📁 Archivo encontrado: {ruta_archivo}")
    
    try:
        # 2.2. Leer el archivo CSV usando punto y coma como separador
        print("\n[PASO 1] Leyendo archivo CSV...")
        print("   - Separador: punto y coma (;)")
        print("   - Codificación: UTF-8")
        
        df = pd.read_csv(
            ruta_archivo,
            sep=';',              # Separador: punto y coma
            encoding='utf-8',     # Codificación UTF-8
            low_memory=False      # Evitar advertencias de tipos de datos
        )
        
        print(f"✅ Archivo cargado exitosamente")
        print(f"   - Total de filas: {len(df):,}")
        print(f"   - Total de columnas: {len(df.columns)}")
        
        # 2.3. Mostrar información básica del DataFrame
        print("\n[PASO 2] Información del DataFrame:")
        print("-" * 80)
        print(f"Dimensiones: {df.shape[0]:,} filas × {df.shape[1]} columnas")
        print(f"Uso de memoria: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        
        # 2.4. Mostrar nombres de columnas
        print("\n[PASO 3] Columnas del DataFrame:")
        print("-" * 80)
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        # 2.5. Mostrar tipos de datos
        print("\n[PASO 4] Tipos de datos:")
        print("-" * 80)
        print(df.dtypes.to_string())
        
        # 2.6. Mostrar primeras filas
        print("\n[PASO 5] Primeras 5 filas:")
        print("-" * 80)
        print(df.head().to_string())
        
        # 2.7. Verificar valores nulos
        print("\n[PASO 6] Valores nulos por columna:")
        print("-" * 80)
        valores_nulos = df.isnull().sum()
        valores_nulos_pct = (valores_nulos / len(df)) * 100
        
        nulos_df = pd.DataFrame({
            'Columna': valores_nulos.index,
            'Valores Nulos': valores_nulos.values,
            'Porcentaje': valores_nulos_pct.values
        })
        nulos_df = nulos_df[nulos_df['Valores Nulos'] > 0].sort_values('Valores Nulos', ascending=False)
        
        if len(nulos_df) > 0:
            print(nulos_df.to_string(index=False))
        else:
            print("  ✅ No se encontraron valores nulos")
        
        # 2.8. Mostrar información estadística básica
        print("\n[PASO 7] Estadísticas descriptivas (columnas numéricas):")
        print("-" * 80)
        columnas_numericas = df.select_dtypes(include=['float64', 'int64']).columns
        if len(columnas_numericas) > 0:
            print(df[columnas_numericas].describe().to_string())
        else:
            print("  ⚠️  No se encontraron columnas numéricas")
        
        print("\n" + "=" * 80)
        print("✅ DATOS CARGADOS EXITOSAMENTE")
        print("=" * 80)
        
        return df
    
    except FileNotFoundError:
        print(f"❌ Error: No se pudo encontrar el archivo en la ruta especificada")
        return None
    except pd.errors.EmptyDataError:
        print(f"❌ Error: El archivo está vacío")
        return None
    except Exception as e:
        print(f"❌ Error al cargar el archivo: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# 3. FUNCIÓN PARA LIMPIAR Y PREPARAR DATOS
# ============================================================================

def limpiar_datos(df):
    """
    Limpia y prepara los datos para análisis.
    
    Args:
        df (pd.DataFrame): DataFrame con los datos originales
        
    Returns:
        pd.DataFrame: DataFrame con datos limpios
    """
    if df is None or df.empty:
        print("❌ No hay datos para limpiar")
        return df
    
    print("\n" + "=" * 80)
    print("LIMPIANDO Y PREPARANDO DATOS")
    print("=" * 80)
    
    df_limpio = df.copy()
    
    # 3.1. Normalizar Item_Fat_Content
    if 'Item_Fat_Content' in df_limpio.columns:
        print("\n[PASO 1] Normalizando Item_Fat_Content...")
        valores_antes = df_limpio['Item_Fat_Content'].value_counts()
        print(f"   Valores antes: {valores_antes.to_dict()}")
        
        # Convertir a minúsculas y reemplazar variaciones
        df_limpio['Item_Fat_Content'] = df_limpio['Item_Fat_Content'].str.lower()
        df_limpio['Item_Fat_Content'] = df_limpio['Item_Fat_Content'].replace({
            'lf': 'low fat',
            'reg': 'regular'
        })
        # Capitalizar primera letra
        df_limpio['Item_Fat_Content'] = df_limpio['Item_Fat_Content'].str.capitalize()
        
        valores_despues = df_limpio['Item_Fat_Content'].value_counts()
        print(f"   Valores después: {valores_despues.to_dict()}")
    
    # 3.2. Convertir Outlet_Establishment_Year a fecha (opcional)
    if 'Outlet_Establishment_Year' in df_limpio.columns:
        print("\n[PASO 2] Preparando columna de fecha...")
        df_limpio['Outlet_Establishment_Date'] = pd.to_datetime(
            df_limpio['Outlet_Establishment_Year'].astype(str) + '-01-01',
            errors='coerce'
        )
        print(f"   ✅ Fecha creada: Outlet_Establishment_Date")
    
    # 3.3. Manejar valores nulos en Item_Weight (llenar con la mediana)
    if 'Item_Weight' in df_limpio.columns:
        nulos_weight = df_limpio['Item_Weight'].isnull().sum()
        if nulos_weight > 0:
            print(f"\n[PASO 3] Llenando {nulos_weight} valores nulos en Item_Weight con la mediana...")
            mediana_weight = df_limpio['Item_Weight'].median()
            df_limpio['Item_Weight'].fillna(mediana_weight, inplace=True)
            print(f"   ✅ Valores nulos llenados con: {mediana_weight:.2f}")
    
    # 3.4. Manejar valores nulos en Outlet_Size (llenar con 'Unknown')
if 'Outlet_Size' in df_limpio.columns:
    nulos_size = df_limpio['Outlet_Size'].isnull().sum()

    if nulos_size > 0:
        print(f"\n[PASO 4] Llenando {nulos_size} valores nulos en Outlet_Size con 'Unknown'...")
        df_limpio['Outlet_Size'] = df_limpio['Outlet_Size'].fillna('Unknown')
        print("   ✅ Valores nulos llenados con: 'Unknown'")
    
    print("\n" + "=" * 80)
    print("✅ DATOS LIMPIADOS EXITOSAMENTE")
    print("=" * 80)
    
    return df_limpio

# ============================================================================
# 4. CALCULAR VENTAS POR MES
# ============================================================================

def calcular_ventas_por_mes(df, columna_fecha='Fecha_Venta', columna_ventas='Item_Outlet_Sales'):
    """
    Calcula las ventas totales por mes agrupando por año-mes.
    
    Args:
        df (pd.DataFrame): DataFrame con los datos de ventas
        columna_fecha (str): Nombre de la columna de fecha. Si no existe, se crea una simulada.
        columna_ventas (str): Nombre de la columna con el monto de ventas
        
    Returns:
        pd.Series: Series con ventas totales por mes (índice: Period año-mes)
    """
    print("\n" + "=" * 80)
    print("CALCULANDO VENTAS POR MES")
    print("=" * 80)
    
    df_ventas = df.copy()
    
    # 4.1. Verificar si existe columna de fecha
    if columna_fecha not in df_ventas.columns:
        print(f"\n⚠️  No se encontró la columna '{columna_fecha}'")
        print("   Opciones:")
        print("   1. Crear fecha simulada basada en Outlet_Establishment_Year")
        print("   2. Usar Outlet_Establishment_Year para agrupar por año")
        
        # Opción: Crear fecha simulada (usando año de establecimiento + mes aleatorio)
        # O mejor: usar solo el año si no hay fecha específica
        if 'Outlet_Establishment_Year' in df_ventas.columns:
            print("\n   Usando Outlet_Establishment_Year para crear fechas estimadas...")
            # Crear fechas estimadas (año + mes aleatorio entre 1-12)
            np.random.seed(42)  # Para reproducibilidad
            df_ventas[columna_fecha] = pd.to_datetime(
                df_ventas['Outlet_Establishment_Year'].astype(str) + '-' + 
                pd.Series(np.random.randint(1, 13, len(df_ventas))).astype(str).str.zfill(2) + '-01',
                errors='coerce'
            )
            print(f"   ✅ Fechas estimadas creadas en columna '{columna_fecha}'")
        else:
            print("   ❌ No se puede calcular ventas por mes sin una columna de fecha")
            return None
    else:
        print(f"\n✅ Columna de fecha encontrada: '{columna_fecha}'")
        # Asegurar que sea datetime
        if not pd.api.types.is_datetime64_any_dtype(df_ventas[columna_fecha]):
            print(f"   Convirtiendo '{columna_fecha}' a formato datetime...")
            df_ventas[columna_fecha] = pd.to_datetime(df_ventas[columna_fecha], errors='coerce')
    
    # 4.2. Verificar columna de ventas
    if columna_ventas not in df_ventas.columns:
        print(f"❌ Error: No se encontró la columna '{columna_ventas}'")
        print(f"   Columnas disponibles: {list(df_ventas.columns)}")
        return None
    
    print(f"✅ Columna de ventas encontrada: '{columna_ventas}'")
    
    # 4.3. Eliminar filas con fechas o ventas nulas
    filas_antes = len(df_ventas)
    df_ventas = df_ventas.dropna(subset=[columna_fecha, columna_ventas])
    filas_despues = len(df_ventas)
    if filas_antes != filas_despues:
        print(f"   ⚠️  Se eliminaron {filas_antes - filas_despues} filas con valores nulos")
    
    # 4.4. Convertir fecha a periodo año-mes usando dt.to_period('M')
    print(f"\n[PASO 1] Convirtiendo fechas a periodo año-mes (YYYY-MM)...")
    df_ventas['Periodo_Mes'] = df_ventas[columna_fecha].dt.to_period('M')
    print(f"   ✅ Períodos creados: {df_ventas['Periodo_Mes'].nunique()} meses únicos")
    print(f"   Rango de períodos: {df_ventas['Periodo_Mes'].min()} a {df_ventas['Periodo_Mes'].max()}")
    
    # 4.5. Agrupar por mes y sumar las ventas
    print(f"\n[PASO 2] Agrupando por mes y calculando ventas totales...")
    ventas_por_mes = df_ventas.groupby('Periodo_Mes')[columna_ventas].sum()
    
    # Ordenar por periodo
    ventas_por_mes = ventas_por_mes.sort_index()
    
    print(f"   ✅ Ventas calculadas para {len(ventas_por_mes)} meses")
    
    # 4.6. Mostrar resultados
    print(f"\n[PASO 3] Resultados (Ventas por Mes):")
    print("-" * 80)
    
    # Convertir a DataFrame para mejor visualización
    ventas_df = ventas_por_mes.to_frame()
    ventas_df.columns = ['Ventas_Totales']
    ventas_df['Periodo'] = ventas_df.index.astype(str)
    ventas_df = ventas_df[['Periodo', 'Ventas_Totales']]
    
    # Mostrar todas las filas
    print(ventas_df.to_string(index=False))
    
    # 4.7. Estadísticas resumidas
    print(f"\n[PASO 4] Estadísticas Resumidas:")
    print("-" * 80)
    print(f"   Total de meses analizados: {len(ventas_por_mes)}")
    print(f"   Ventas totales (suma): {ventas_por_mes.sum():,.2f}")
    print(f"   Promedio de ventas por mes: {ventas_por_mes.mean():,.2f}")
    print(f"   Mes con mayor ventas: {ventas_por_mes.idxmax()} ({ventas_por_mes.max():,.2f})")
    print(f"   Mes con menor ventas: {ventas_por_mes.idxmin()} ({ventas_por_mes.min():,.2f})")
    
    print("\n" + "=" * 80)
    print("✅ VENTAS POR MES CALCULADAS EXITOSAMENTE")
    print("=" * 80)
    
    return ventas_por_mes

import os

# ================================
# 5. EXPORTAR RESULTADOS DE VENTAS POR MES A CSV Y EXCEL       
# ================================

output_dir = "output_ventas"
os.makedirs(output_dir, exist_ok=True)

# 5.1. Exportar CSV
csv_path = os.path.join(output_dir, "ventas_por_mes.csv")
ventas_por_mes.to_csv(csv_path)

# 5.2. Exportar Excel
excel_path = os.path.join(output_dir, "ventas_por_mes.xlsx")
ventas_por_mes.to_excel(excel_path)

print("\n📁 ARCHIVOS EXPORTADOS:")
print(f"   ✅ CSV: {csv_path}")
print(f"   ✅ Excel: {excel_path}")

# ============================================================================
# 6. DETERMINAR PRODUCTO MÁS VENDIDO VS. PRODUCTO CON MAYOR INGRESOS
# ============================================================================

def producto_mas_vendido_vs_mayor_ingresos(df, 
                                           columna_producto='Item_Identifier',
                                           columna_precio='Item_MRP',
                                           columna_ventas='Item_Outlet_Sales'):
    """
    Determina el producto más vendido (por cantidad) y el producto con mayor ingresos.
    
    Args:
        df (pd.DataFrame): DataFrame con los datos de ventas
        columna_producto (str): Nombre de la columna con el identificador del producto
        columna_precio (str): Nombre de la columna con el precio unitario
        columna_ventas (str): Nombre de la columna con las ventas totales
        
    Returns:
        dict: Diccionario con información de productos más vendidos y con mayor ingresos
    """
    print("\n" + "=" * 80)
    print("ANÁLISIS: PRODUCTO MÁS VENDIDO VS. PRODUCTO CON MAYOR INGRESOS")
    print("=" * 80)
    
    df_analisis = df.copy()
    
    # 6.1. Verificar que las columnas existen
    columnas_requeridas = [columna_producto, columna_precio, columna_ventas]
    columnas_faltantes = [col for col in columnas_requeridas if col not in df_analisis.columns]
    
    if columnas_faltantes:
        print(f"❌ Error: Columnas faltantes: {columnas_faltantes}")
        print(f"   Columnas disponibles: {list(df_analisis.columns)}")
        return None
    
    print(f"\n✅ Columnas identificadas:")
    print(f"   - Producto: {columna_producto}")
    print(f"   - Precio: {columna_precio}")
    print(f"   - Ventas: {columna_ventas}")
    
    # 6.2. Eliminar filas con valores nulos en las columnas necesarias
    filas_antes = len(df_analisis)
    df_analisis = df_analisis.dropna(subset=columnas_requeridas)
    filas_despues = len(df_analisis)
    if filas_antes != filas_despues:
        print(f"\n⚠️  Se eliminaron {filas_antes - filas_despues} filas con valores nulos")
    
    # 6.3. Calcular cantidad vendida para cada transacción
    # Item_Outlet_Sales es el total vendido en esa transacción
    # Cantidad = Total vendido / Precio unitario
    print(f"\n[PASO 1] Calculando cantidad vendida por transacción...")
    print(f"   Fórmula: Cantidad = {columna_ventas} / {columna_precio}")
    
    df_analisis['Cantidad_Vendida'] = df_analisis[columna_ventas] / df_analisis[columna_precio]
    
    # Validar que el cálculo tenga sentido (cantidad debe ser razonable)
    cantidades_invalidas = (df_analisis['Cantidad_Vendida'] <= 0) | (df_analisis['Cantidad_Vendida'] > 10000)
    if cantidades_invalidas.sum() > 0:
        print(f"   ⚠️  Se encontraron {cantidades_invalidas.sum()} transacciones con cantidades inválidas (>10000 o <=0)")
        print(f"      Estas serán filtradas para mantener el análisis coherente")
    
    # Filtrar cantidades válidas
    df_analisis = df_analisis[(df_analisis['Cantidad_Vendida'] > 0) & (df_analisis['Cantidad_Vendida'] <= 10000)]
    
    # Redondear a enteros (cantidad de unidades)
    df_analisis['Cantidad_Vendida'] = df_analisis['Cantidad_Vendida'].round().astype(int)
    
    print(f"   ✅ Cantidad vendida calculada para {len(df_analisis):,} transacciones válidas")
    print(f"   Rango de cantidades: {df_analisis['Cantidad_Vendida'].min()} - {df_analisis['Cantidad_Vendida'].max()} unidades por transacción")
    
    # 6.4. Agrupar por producto y calcular métricas
    print(f"\n[PASO 2] Agrupando por producto usando groupby...")
    
    # Agrupar por producto y calcular:
    # - Cantidad total vendida (suma de cantidades)
    # - Ingresos totales (suma de ventas)
    # - Número de transacciones (conteo)
    # - Precio promedio
    productos_agrupados = df_analisis.groupby(columna_producto).agg({
        'Cantidad_Vendida': 'sum',      # Cantidad total vendida
        columna_ventas: 'sum',          # Ingresos totales (suma de ventas)
        columna_precio: ['mean', 'count']  # Precio promedio y número de transacciones
    }).round(2)
    
    # Aplanar nombres de columnas
    productos_agrupados.columns = ['Cantidad_Total', 'Ingresos_Totales', 'Precio_Promedio', 'Num_Transacciones']
    productos_agrupados = productos_agrupados.reset_index()
    
    print(f"   ✅ Agrupación completada: {len(productos_agrupados)} productos únicos")
    
    # 6.5. Determinar producto más vendido (mayor cantidad total)
    print(f"\n[PASO 3] Identificando producto más vendido (por cantidad total)...")
    producto_mas_vendido = productos_agrupados.loc[productos_agrupados['Cantidad_Total'].idxmax()]
    
    print(f"\n   📦 PRODUCTO MÁS VENDIDO (por cantidad):")
    print(f"   {'-' * 76}")
    print(f"   Producto: {producto_mas_vendido[columna_producto]}")
    print(f"   Cantidad Total Vendida: {producto_mas_vendido['Cantidad_Total']:,} unidades")
    print(f"   Ingresos Totales: {producto_mas_vendido['Ingresos_Totales']:,.2f}")
    print(f"   Precio Promedio: {producto_mas_vendido['Precio_Promedio']:.2f}")
    print(f"   Número de Transacciones: {producto_mas_vendido['Num_Transacciones']}")
    
    # 6.6. Determinar producto con mayor ingresos
    print(f"\n[PASO 4] Identificando producto con mayor ingresos...")
    producto_mayor_ingresos = productos_agrupados.loc[productos_agrupados['Ingresos_Totales'].idxmax()]
    
    print(f"\n   💰 PRODUCTO CON MAYOR INGRESOS:")
    print(f"   {'-' * 76}")
    print(f"   Producto: {producto_mayor_ingresos[columna_producto]}")
    print(f"   Ingresos Totales: {producto_mayor_ingresos['Ingresos_Totales']:,.2f}")
    print(f"   Cantidad Total Vendida: {producto_mayor_ingresos['Cantidad_Total']:,} unidades")
    print(f"   Precio Promedio: {producto_mayor_ingresos['Precio_Promedio']:.2f}")
    print(f"   Número de Transacciones: {producto_mayor_ingresos['Num_Transacciones']}")
    
    #   6.7. Comparación detallada entre ambos productos
    print(f"\n[PASO 5] Comparación y Análisis:")
    print(f"   {'-' * 76}")
    
    if producto_mas_vendido[columna_producto] == producto_mayor_ingresos[columna_producto]:
        print(f"   ✅ El mismo producto es el más vendido y el que genera mayores ingresos")
        print(f"   Esto significa que tiene buen volumen Y buen precio unitario")
    else:
        print(f"   📊 IMPORTANTE: Son productos diferentes (esto es común y tiene sentido)")
        print(f"\n   Explicación:")
        print(f"   • Un producto BARATO puede vender MÁS UNIDADES pero generar MENOS DINERO")
        print(f"   • Un producto CARO puede vender MENOS UNIDADES pero generar MÁS DINERO")
        
        print(f"\n   Comparación detallada:")
        print(f"   {'-' * 76}")
        
        # Crear tabla comparativa
        comparacion_data = {
            'Métrica': ['Producto', 'Cantidad Total (unidades)', 'Ingresos Totales', 
                       'Precio Promedio', 'Ingresos por Unidad'],
            'Más Vendido': [
                producto_mas_vendido[columna_producto],
                f"{producto_mas_vendido['Cantidad_Total']:,}",
                f"{producto_mas_vendido['Ingresos_Totales']:,.2f}",
                f"{producto_mas_vendido['Precio_Promedio']:.2f}",
                f"{producto_mas_vendido['Ingresos_Totales'] / producto_mas_vendido['Cantidad_Total']:.2f}"
            ],
            'Mayor Ingresos': [
                producto_mayor_ingresos[columna_producto],
                f"{producto_mayor_ingresos['Cantidad_Total']:,}",
                f"{producto_mayor_ingresos['Ingresos_Totales']:,.2f}",
                f"{producto_mayor_ingresos['Precio_Promedio']:.2f}",
                f"{producto_mayor_ingresos['Ingresos_Totales'] / producto_mayor_ingresos['Cantidad_Total']:.2f}"
            ]
        }
        comparacion_df = pd.DataFrame(comparacion_data)
        print(comparacion_df.to_string(index=False))
        
        # Análisis de por qué son diferentes
        precio_mas_vendido = producto_mas_vendido['Precio_Promedio']
        precio_mayor_ingresos = producto_mayor_ingresos['Precio_Promedio']
        
        print(f"\n   Análisis:")
        if precio_mas_vendido < precio_mayor_ingresos:
            print(f"   • El producto más vendido es MÁS BARATO (${precio_mas_vendido:.2f} vs ${precio_mayor_ingresos:.2f})")
            print(f"   • Por eso tiene más unidades pero menos ingresos totales")
        elif precio_mas_vendido > precio_mayor_ingresos:
            print(f"   • El producto más vendido es MÁS CARO (${precio_mas_vendido:.2f} vs ${precio_mayor_ingresos:.2f})")
            print(f"   • A pesar de ser más caro, vendió más unidades")
            print(f"   • Pero el otro producto, aunque vendió menos, generó más dinero por tener más volumen total")
        else:
            print(f"   • Ambos productos tienen precios similares")
            print(f"   • La diferencia está en el volumen de transacciones o descuentos aplicados")
    
    # 6.8. Top productos por cantidad y por ingresos (con precio promedio para contexto)
    print(f"\n[PASO 6] Top 10 productos por cantidad vendida (más unidades):")
    print(f"   {'-' * 76}")
    top_cantidad = productos_agrupados.nlargest(10, 'Cantidad_Total')[
        [columna_producto, 'Cantidad_Total', 'Precio_Promedio', 'Ingresos_Totales']
    ]
    top_cantidad.columns = ['Producto', 'Cantidad Total', 'Precio Promedio', 'Ingresos Totales']
    print(top_cantidad.to_string(index=False))
    print(f"\n   💡 Nota: Productos con MÁS unidades pueden tener MENOS ingresos si son más baratos")
    
    print(f"\n[PASO 7] Top 10 productos por ingresos totales (más dinero):")
    print(f"   {'-' * 76}")
    top_ingresos = productos_agrupados.nlargest(10, 'Ingresos_Totales')[
        [columna_producto, 'Ingresos_Totales', 'Precio_Promedio', 'Cantidad_Total']
    ]
    top_ingresos.columns = ['Producto', 'Ingresos Totales', 'Precio Promedio', 'Cantidad Total']
    print(top_ingresos.to_string(index=False))
    print(f"\n   💡 Nota: Productos con MÁS ingresos pueden tener MENOS unidades si son más caros")
    
    # 6.9. Validación adicional: verificar coherencia del análisis
    print(f"\n[PASO 8] Validación del Análisis:")
    print(f"   {'-' * 76}")
    
    # Verificar que los cálculos tienen sentido
    verificacion_ok = True
    
    # Verificar que cantidad * precio promedio ≈ ingresos totales (aproximadamente)
    producto_mv_cantidad = producto_mas_vendido['Cantidad_Total']
    producto_mv_precio = producto_mas_vendido['Precio_Promedio']
    producto_mv_ingresos = producto_mas_vendido['Ingresos_Totales']
    producto_mv_calc = producto_mv_cantidad * producto_mv_precio
    diferencia_mv = abs(producto_mv_calc - producto_mv_ingresos) / producto_mv_ingresos * 100
    
    producto_mi_cantidad = producto_mayor_ingresos['Cantidad_Total']
    producto_mi_precio = producto_mayor_ingresos['Precio_Promedio']
    producto_mi_ingresos = producto_mayor_ingresos['Ingresos_Totales']
    producto_mi_calc = producto_mi_cantidad * producto_mi_precio
    diferencia_mi = abs(producto_mi_calc - producto_mi_ingresos) / producto_mi_ingresos * 100
    
    print(f"   Validación para producto más vendido:")
    print(f"      Cantidad × Precio = {producto_mv_cantidad:,} × {producto_mv_precio:.2f} = {producto_mv_calc:,.2f}")
    print(f"      Ingresos Totales = {producto_mv_ingresos:,.2f}")
    print(f"      Diferencia: {diferencia_mv:.2f}% (esperado <10% para validar coherencia)")
    
    print(f"\n   Validación para producto con mayor ingresos:")
    print(f"      Cantidad × Precio = {producto_mi_cantidad:,} × {producto_mi_precio:.2f} = {producto_mi_calc:,.2f}")
    print(f"      Ingresos Totales = {producto_mi_ingresos:,.2f}")
    print(f"      Diferencia: {diferencia_mi:.2f}% (esperado <10% para validar coherencia)")
    
    if diferencia_mv < 10 and diferencia_mi < 10:
        print(f"\n   ✅ Los cálculos son coherentes (diferencia <10% es normal por descuentos/promociones)")
    else:
        print(f"\n   ⚠️  Las diferencias son significativas (>10%)")
        print(f"      Esto puede deberse a:")
        print(f"      - Descuentos aplicados (Item_Outlet_Sales incluye descuentos)")
        print(f"      - Promociones especiales")
        print(f"      - Variaciones de precio a lo largo del tiempo")
    
    print("\n" + "=" * 80)
    print("✅ ANÁLISIS DE PRODUCTOS COMPLETADO")
    print("=" * 80)
    
    # 6.10. Retornar resultados estructurados
    resultado = {
        'producto_mas_vendido': {
            'identificador': producto_mas_vendido[columna_producto],
            'cantidad_total': int(producto_mas_vendido['Cantidad_Total']),
            'ingresos_totales': float(producto_mas_vendido['Ingresos_Totales']),
            'precio_promedio': float(producto_mas_vendido['Precio_Promedio']),
            'num_transacciones': int(producto_mas_vendido['Num_Transacciones'])
        },
        'producto_mayor_ingresos': {
            'identificador': producto_mayor_ingresos[columna_producto],
            'ingresos_totales': float(producto_mayor_ingresos['Ingresos_Totales']),
            'cantidad_total': int(producto_mayor_ingresos['Cantidad_Total']),
            'precio_promedio': float(producto_mayor_ingresos['Precio_Promedio']),
            'num_transacciones': int(producto_mayor_ingresos['Num_Transacciones'])
        },
        'productos_agrupados': productos_agrupados,
        'top_cantidad': top_cantidad,
        'top_ingresos': top_ingresos
    }
    
    return resultado

# ============================================================================
# 7. GRAFICAR VENTAS POR MES
# ============================================================================

def graficar_ventas_por_mes(ventas_por_mes, guardar=True, mostrar=False, ruta_guardado='ventas_por_mes.png'):
    """
    Grafica las ventas por mes utilizando matplotlib.
    
    Args:
        ventas_por_mes (pd.Series): Series con ventas por mes (índice: Period año-mes)
        guardar (bool): Si True, guarda el gráfico en un archivo
        mostrar (bool): Si True, muestra el gráfico en pantalla
        ruta_guardado (str): Ruta donde guardar el gráfico
        
    Returns:
        str: Ruta del archivo guardado o None
    """
    print("\n" + "=" * 80)
    print("GENERANDO GRÁFICO DE VENTAS POR MES")
    print("=" * 80)
    
    # 7.1. Validar que tenemos datos para graficar
    if ventas_por_mes is None or len(ventas_por_mes) == 0:
        print("❌ Error: No hay datos de ventas por mes para graficar")
        return None
    
    print(f"\n✅ Datos recibidos: {len(ventas_por_mes)} meses a graficar")
    print(f"   Rango: {ventas_por_mes.index[0]} a {ventas_por_mes.index[-1]}")
    
    # 7.2. Preparar datos para graficar
    print(f"\n[PASO 1] Preparando datos para graficar...")
    
    #  Convertir el índice Period a string para el eje X (o mantener como Period)
    periodos_str = ventas_por_mes.index.astype(str)
    valores_ventas = ventas_por_mes.values
    
    print(f"   ✅ Datos preparados: {len(periodos_str)} períodos")
    
    # 7.3. Crear la figura y el eje
    print(f"\n[PASO 2] Creando figura y configurando estilo...")
    
    # Configurar tamaño y estilo del gráfico
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.suptitle('Ventas por Mes', fontsize=16, fontweight='bold', y=1.02)
    
    # 7.4. Crear el gráfico de línea
    print(f"\n[PASO 3] Generando gráfico de línea...")
    
    # Gráfico de línea con marcadores
    ax.plot(periodos_str, valores_ventas, 
            marker='o',           # Marcadores circulares
            linewidth=2,          # Grosor de línea
            markersize=6,         # Tamaño de marcadores
            color='#3498db',      # Color azul
            markerfacecolor='#2980b9',  # Color de relleno de marcadores
            markeredgewidth=2,    # Grosor del borde de marcadores
            markeredgecolor='white')    # Color del borde
    
    # Agregar área sombreada bajo la línea
    ax.fill_between(periodos_str, valores_ventas, 
                    alpha=0.3,    # Transparencia
                    color='#3498db')  # Color del área
    
    print(f"   ✅ Gráfico de línea creado")
    
    # 7.5. Configurar etiquetas y título
    print(f"\n[PASO 4] Configurando etiquetas y títulos...")
    
    ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
    ax.set_ylabel('Ventas Totales', fontsize=12, fontweight='bold')
    ax.set_title('Evolución de Ventas Mensuales', fontsize=14, fontweight='bold', pad=15)
    
    # 7.6. Configurar formato de valores en el eje Y (formato monetario)
    print(f"\n[PASO 5] Formateando valores...")
    
    # Formatear eje Y para mostrar valores con separadores de miles
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
    
    # 7.7. Configurar rotación de etiquetas del eje X
    print(f"\n[PASO 6] Configurando etiquetas del eje X...")
    
    # Rotar etiquetas del eje X para mejor legibilidad
    plt.xticks(rotation=45, ha='right')
    
    # 7.8. Agregar cuadrícula para mejor lectura
    print(f"\n[PASO 7] Agregando cuadrícula...")
    
    ax.grid(True, 
            alpha=0.3,           # Transparencia de la cuadrícula
            linestyle='--',      # Estilo de línea punteada
            linewidth=0.5)       # Grosor de línea
    ax.set_axisbelow(True)      # Poner la cuadrícula detrás de los datos
    
    # 7.9. Agregar anotaciones en los puntos importantes
    print(f"\n[PASO 8] Agregando anotaciones...")
    
    # Anotar el valor máximo
    max_idx = valores_ventas.argmax()
    max_valor = valores_ventas[max_idx]
    max_periodo = periodos_str[max_idx]
    ax.annotate(f'Máximo: {max_valor:,.0f}',
                xy=(max_idx, max_valor),
                xytext=(10, 10),
                textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                fontweight='bold')
    
    # Anotar el valor mínimo (solo si es significativamente diferente)
    min_idx = valores_ventas.argmin()
    min_valor = valores_ventas[min_idx]
    if min_valor < max_valor * 0.5:  # Solo si el mínimo es menos del 50% del máximo
        ax.annotate(f'Mínimo: {min_valor:,.0f}',
                    xy=(min_idx, min_valor),
                    xytext=(10, -20),
                    textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='orange', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                    fontweight='bold')
    
    # 7.10. Agregar línea de promedio
    promedio_ventas = valores_ventas.mean()
    ax.axhline(y=promedio_ventas, 
               color='red', 
               linestyle='--', 
               linewidth=2, 
               alpha=0.7,
               label=f'Promedio: {promedio_ventas:,.0f}')
    ax.legend(loc='upper left')
    
    # 7.11. Ajustar layout y espaciado
    print(f"\n[PASO 9] Ajustando layout...")
    
    plt.tight_layout()  # Ajustar automáticamente para evitar cortes
    
    # 7.12. Guardar o mostrar el gráfico
    print(f"\n[PASO 10] Guardando/mostrando gráfico...")
    
    if guardar:
        try:
            plt.savefig(ruta_guardado, 
                       dpi=300,           # Alta resolución
                       bbox_inches='tight',  # Ajustar bordes
                       facecolor='white',    # Fondo blanco
                       edgecolor='none')
            print(f"   ✅ Gráfico guardado en: {ruta_guardado}")
            ruta_final = ruta_guardado
        except Exception as e:
            print(f"   ❌ Error al guardar gráfico: {e}")
            ruta_final = None
    else:
        ruta_final = None
    
    if mostrar:
        plt.show()
    else:
        plt.close()  # Cerrar la figura para liberar memoria
    
    print("\n" + "=" * 80)
    print("✅ GRÁFICO DE VENTAS POR MES GENERADO EXITOSAMENTE")
    print("=" * 80)
    
    return ruta_final

# ============================================================================
# 8. GRAFICAR TOP 5 PRODUCTOS POR INGRESOS
# ============================================================================

def graficar_top_5_productos_ingresos(resultado_productos,
                                      guardar=True,
                                      mostrar=True,
                                      ruta_guardado='top_5_productos_ingresos.png'):
    """
    Grafica los 5 productos con mayores ingresos.
    
    Args:
        resultado_productos (dict): Diccionario retornado por producto_mas_vendido_vs_mayor_ingresos
        guardar (bool): Guarda el gráfico como PNG
        mostrar (bool): Muestra el gráfico en pantalla
        ruta_guardado (str): Ruta del archivo PNG
    """
    print("\n" + "=" * 80)
    print("GENERANDO GRÁFICO: TOP 5 PRODUCTOS POR INGRESOS")
    print("=" * 80)

    if resultado_productos is None or 'productos_agrupados' not in resultado_productos:
        print("❌ No hay datos para graficar top 5 productos")
        return None

    df_productos = resultado_productos['productos_agrupados']

    # 8.1. Seleccionar Top 5 usando nlargest (forma óptima)
    top_5 = df_productos.nlargest(5, 'Ingresos_Totales')

    print("\n[PASO 1] Top 5 productos por ingresos:")
    print("-" * 80)
    print(top_5[['Item_Identifier', 'Ingresos_Totales', 'Cantidad_Total']].to_string(index=False))
 
    #  8.2. Crear gráfico
    print(f"\n[PASO 2] Creando gráfico...")
    plt.figure(figsize=(12, 6))
    plt.bar(
        top_5['Item_Identifier'],
        top_5['Ingresos_Totales']
    )

    plt.title('Top 5 Productos por Ingresos', fontsize=14, fontweight='bold')
    plt.xlabel('Producto', fontsize=12)
    plt.ylabel('Ingresos Totales', fontsize=12)

    #  8.3. Rotar etiquetas si son largas
    print(f"\n[PASO 3] Rotando etiquetas...")
    plt.xticks(rotation=45, ha='right')

    # Formato monetario eje Y
    plt.gca().yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f'{x:,.0f}')
    )

    plt.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    if guardar:
        plt.savefig(ruta_guardado, dpi=300, bbox_inches='tight')
        print(f"\n💾 Gráfico guardado en: {ruta_guardado}")

    if mostrar:
        plt.show()
    else:
        plt.close()

    print("\n" + "=" * 80)
    print("✅ GRÁFICO TOP 5 PRODUCTOS POR INGRESOS GENERADO")
    print("=" * 80)

    return ruta_guardado
      
# ============================================================================
# 9. FUNCIÓN PRINCIPAL
# ============================================================================

if __name__ == '__main__':
    # 9.1. Cargar datos
    print(f"\n[PASO 1] Cargando datos...")
    df = cargar_datos_ventas()
    
    if df is not None:
        # 9.2. Limpiar datos
        print(f"\n[PASO 2] Limpiando datos...")
        df_limpio = limpiar_datos(df)
        
        # 9.3. Mostrar resumen final
        print(f"\n[PASO 3] Mostrando resumen final...")
        print("\n" + "=" * 80)
        print("RESUMEN FINAL")
        print("=" * 80)
        print(f"\n📊 DataFrame original:")
        print(f"   - Filas: {len(df):,}")
        print(f"   - Columnas: {len(df.columns)}")
        
        if df_limpio is not None:
            print(f"\n📊 DataFrame limpio:")
            print(f"   - Filas: {len(df_limpio):,}")
            print(f"   - Columnas: {len(df_limpio.columns)}")
            print(f"\n✅ Los datos están listos para análisis")
        
        # 9.4. Calcular ventas por mes       
        print(f"\n[PASO 4] Calculando ventas por mes...")
        ventas_por_mes = calcular_ventas_por_mes(
            df_limpio, 
            columna_fecha='Fecha_Venta',  # Ajustar si tu CSV tiene otra columna de fecha
            columna_ventas='Item_Outlet_Sales'
        )
        
        if ventas_por_mes is not None:
            print("\n📊 Series de ventas por mes disponible para graficar o analizar")
            
            # 9.5. Mostrar ejemplos de uso
            print(f"\n[PASO 5] Mostrando ejemplos de uso...")
            print("\n" + "=" * 80)
            print("EJEMPLOS DE USO DE ventas_por_mes")
            print("=" * 80)
            
            print("\n[Ejemplo 1] Mostrar la Series directamente:")
            print("-" * 80)
            print(ventas_por_mes)
            
            print("\n[Ejemplo 2] Convertir a DataFrame para mejor visualización:")
            print("-" * 80)
            ventas_df_ejemplo = ventas_por_mes.to_frame()
            ventas_df_ejemplo.columns = ['Ventas_Totales']
            print(ventas_df_ejemplo)
            
            print("\n[Ejemplo 3] Acceder a valores específicos:")
            print("-" * 80)
            print(f"   Primer mes: {ventas_por_mes.index[0]} = {ventas_por_mes.iloc[0]:,.2f}")
            print(f"   Último mes: {ventas_por_mes.index[-1]} = {ventas_por_mes.iloc[-1]:,.2f}")
        
        # 9.6. Analizar productos más vendidos y con mayor ingresos
        print(f"\n[PASO 6] Analizando productos más vendidos y con mayor ingresos...")
        resultado_productos = producto_mas_vendido_vs_mayor_ingresos(
            df_limpio,
            columna_producto='Item_Identifier',
            columna_precio='Item_MRP',
            columna_ventas='Item_Outlet_Sales'
        )

        if resultado_productos is not None:
            print("\n📊 Resultados de análisis de productos disponibles en el diccionario 'resultado_productos'")
        
        # 9.7. Graficar ventas por mes
        print(f"\n[PASO 7] Graficando ventas por mes...")
        if ventas_por_mes is not None:
            print("\n" + "=" * 80)
            print("GENERANDO GRÁFICOS")
            print("=" * 80)
            
            ruta_grafico = graficar_ventas_por_mes(
                ventas_por_mes,
                guardar=True,
                mostrar=False,  # Cambiar a True si quieres ver el gráfico
                ruta_guardado='ventas_por_mes.png'
            )
            
            if ruta_grafico:
                print(f"\n💾 Gráfico disponible en: {ruta_grafico}")
            
            # Guardar DataFrame limpio (opcional)
            # df_limpio.to_csv('ventas_limpio.csv', index=False, sep=';')
            # print(f"\n💾 DataFrame limpio guardado en: ventas_limpio.csv")

# 10. RESUMEN FINAL DE RESULTADOS
# ============================================================================

        print("\n" + "=" * 80)
        print("EJECUCIÓN Y ANÁLISIS DE RESULTADOS")
        print("=" * 80)

        print("\n📌 Resumen clave:")
        print(f"   - Producto más vendido (unidades): {resultado_productos['producto_mas_vendido']['identificador']}")
        print(f"   - Producto con mayores ingresos: {resultado_productos['producto_mayor_ingresos']['identificador']}")

        if resultado_productos['producto_mas_vendido']['identificador'] != resultado_productos['producto_mayor_ingresos']['identificador']:
            print("   ✔️ Son productos distintos: tiene sentido económico (volumen vs precio)")
        else:
            print("   ⚠️ El mismo producto lidera en unidades e ingresos")

# 11      . FIN DEL PROGRAMA    
# ============================================================================

