"""
Módulo de Análisis de Datos para el Planificador de Tareas
Proporciona funciones para análisis estadístico y visualización de tareas
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional

# Configuración de matplotlib para español
plt.rcParams['font.size'] = 10
plt.rcParams['figure.figsize'] = (12, 6)

DATA_FILE = 'tareas.json'
OUTPUT_DIR = 'analisis_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# 1. CARGAR DATOS DESDE JSON
# ============================================================================

def cargar_tareas() -> pd.DataFrame:
    """
    Carga las tareas desde el archivo JSON y las convierte en un DataFrame de pandas.
    
    Returns:
        pd.DataFrame: DataFrame con todas las tareas
    """
    if not os.path.exists(DATA_FILE):
        print(f"⚠️  Archivo {DATA_FILE} no encontrado. Retornando DataFrame vacío.")
        return pd.DataFrame()
    
    try:
        # 1.1. Leer archivo JSON
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tareas = data.get('tareas', [])
        
        if not tareas:
            print("⚠️  No hay tareas para analizar.")
            return pd.DataFrame()
        
        # 1.2. Convertir lista de diccionarios a DataFrame
        df = pd.DataFrame(tareas)
        
        # 1.3. Procesar columnas de fecha (convertir plazo a datetime)
        if 'plazo' in df.columns:
            df['plazo_date'] = pd.to_datetime(df['plazo'], errors='coerce')
        
        # 1.4. Calcular columnas derivadas
        hoy = datetime.now().date()
        if 'plazo_date' in df.columns:
            # Calcular días restantes hasta el plazo
            df['dias_restantes'] = (df['plazo_date'].dt.date - hoy).apply(
                lambda x: x.days if pd.notna(x) else None
            )
            # Identificar tareas vencidas
            df['vencida'] = df['dias_restantes'].apply(lambda x: x < 0 if x is not None else False)
            # Identificar tareas por vencer (próximos 7 días)
            df['por_vencer'] = df['dias_restantes'].apply(
                lambda x: 0 <= x <= 7 if x is not None else False
            )
        
        # 1.5. Contar número de documentos adjuntos
        df['num_documentos'] = df['documentos'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        
        print(f"✅ Cargadas {len(df)} tareas para análisis")
        return df
    
    except Exception as e:
        print(f"❌ Error al cargar tareas: {e}")
        return pd.DataFrame()


# ============================================================================
# 2. CALCULAR ESTADÍSTICAS GENERALES
# ============================================================================

def analisis_general(df: pd.DataFrame) -> Dict:
    """
    Realiza un análisis general de las tareas.
    
    Args:
        df: DataFrame con las tareas
        
    Returns:
        dict: Diccionario con estadísticas generales
    """
    if df.empty:
        return {}
    
    # 2.1. Contar total de tareas
    total_tareas = len(df)
    
    # 2.2. Contar tareas por estado
    por_estado = df['situacion'].value_counts().to_dict() if 'situacion' in df.columns else {}
    
    # 2.3. Contar tareas por responsable
    por_responsable = df['responsable'].value_counts().to_dict() if 'responsable' in df.columns else {}
    
    # 2.4. Contar tareas por centro de responsabilidad
    por_centro = df['centro_responsabilidad'].value_counts().to_dict() if 'centro_responsabilidad' in df.columns else {}
    
    # 2.5. Calcular estadísticas de plazos
    tareas_con_plazo = df['plazo'].notna().sum() if 'plazo' in df.columns else 0
    tareas_sin_plazo = df['plazo'].isna().sum() if 'plazo' in df.columns else len(df)
    
    # 2.6. Identificar tareas vencidas y por vencer
    tareas_vencidas = df['vencida'].sum() if 'vencida' in df.columns else 0
    tareas_por_vencer = df['por_vencer'].sum() if 'por_vencer' in df.columns else 0
    
    # 2.7. Calcular estadísticas de documentos
    total_documentos = df['num_documentos'].sum() if 'num_documentos' in df.columns else 0
    promedio_documentos = df['num_documentos'].mean() if 'num_documentos' in df.columns else 0
    
    estadisticas = {
        'total_tareas': total_tareas,
        'por_estado': por_estado,
        'por_responsable': por_responsable,
        'por_centro': por_centro,
        'tareas_con_plazo': tareas_con_plazo,
        'tareas_sin_plazo': tareas_sin_plazo,
        'tareas_vencidas': tareas_vencidas,
        'tareas_por_vencer': tareas_por_vencer,
        'total_documentos': total_documentos,
        'promedio_documentos': promedio_documentos,
    }
    
    return estadisticas


def analisis_eficiencia(df: pd.DataFrame) -> Dict:
    """
    Analiza la eficiencia en la gestión de tareas.
    
    Args:
        df: DataFrame con las tareas
        
    Returns:
        dict: Métricas de eficiencia
    """
    if df.empty:
        return {}
    
    # 2.8. Calcular totales
    total = len(df)
    
    # 2.9. Contar tareas completadas y validadas
    completadas = len(df[df['situacion'].isin(['Completada', 'Validada'])]) if 'situacion' in df.columns else 0
    
    # 2.10. Contar tareas en progreso
    en_progreso = len(df[df['situacion'] == 'En Ejecución']) if 'situacion' in df.columns else 0
    
    # 2.11. Contar tareas sin ejecutar
    sin_ejecutar = len(df[df['situacion'] == 'Sin Ejecutar']) if 'situacion' in df.columns else 0
    
    # 2.12. Calcular tasas de eficiencia
    eficiencia = {
        'tasa_completacion': (completadas / total * 100) if total > 0 else 0,
        'tasa_en_progreso': (en_progreso / total * 100) if total > 0 else 0,
        'tasa_sin_ejecutar': (sin_ejecutar / total * 100) if total > 0 else 0,
        'total_completadas': completadas,
        'total_en_progreso': en_progreso,
        'total_sin_ejecutar': sin_ejecutar
    }
    
    return eficiencia


# ============================================================================
# 3. DETERMINAR RANKINGS Y TENDENCIAS
# ============================================================================

def obtener_top_responsables(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Determina los responsables con más tareas asignadas.
    
    Args:
        df: DataFrame con las tareas
        top_n: Número de responsables principales a retornar
        
    Returns:
        pd.DataFrame: DataFrame con los top responsables
    """
    if df.empty or 'responsable' not in df.columns:
        return pd.DataFrame()
    
    # 3.1. Filtrar responsables vacíos
    df_filtrado = df[df['responsable'].notna() & (df['responsable'] != '')]
    
    if df_filtrado.empty:
        return pd.DataFrame()
    
    # 3.2. Contar tareas por responsable
    responsables_count = df_filtrado['responsable'].value_counts().head(top_n)
    
    # 3.3. Convertir a DataFrame con nombre de columna
    top_responsables = responsables_count.reset_index()
    top_responsables.columns = ['responsable', 'cantidad_tareas']
    
    return top_responsables


def obtener_top_centros(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Determina los centros de responsabilidad con más tareas.
    
    Args:
        df: DataFrame con las tareas
        top_n: Número de centros principales a retornar
        
    Returns:
        pd.DataFrame: DataFrame con los top centros
    """
    if df.empty or 'centro_responsabilidad' not in df.columns:
        return pd.DataFrame()
    
    # 3.4. Filtrar centros vacíos
    df_filtrado = df[df['centro_responsabilidad'].notna() & (df['centro_responsabilidad'] != '')]
    
    if df_filtrado.empty:
        return pd.DataFrame()
    
    # 3.5. Contar tareas por centro
    centros_count = df_filtrado['centro_responsabilidad'].value_counts().head(top_n)
    
    # 3.6. Convertir a DataFrame
    top_centros = centros_count.reset_index()
    top_centros.columns = ['centro_responsabilidad', 'cantidad_tareas']
    
    return top_centros


def obtener_tareas_criticas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Determina las tareas críticas (vencidas o por vencer).
    
    Args:
        df: DataFrame con las tareas
        
    Returns:
        pd.DataFrame: DataFrame con tareas críticas ordenadas por prioridad
    """
    if df.empty:
        return pd.DataFrame()
    
    # 3.7. Filtrar tareas con plazo
    df_con_plazo = df[df['plazo_date'].notna()].copy()
    
    if df_con_plazo.empty:
        return pd.DataFrame()
    
    # 3.8. Identificar tareas críticas (vencidas o por vencer)
    tareas_criticas = df_con_plazo[
        (df_con_plazo['vencida'] == True) | (df_con_plazo['por_vencer'] == True)
    ].copy()
    
    # 3.9. Ordenar por días restantes (más críticas primero)
    tareas_criticas = tareas_criticas.sort_values('dias_restantes', na_position='last')
    
    return tareas_criticas


# ============================================================================
# 4. GRAFICAR DISTRIBUCIÓN POR ESTADO
# ============================================================================

def grafico_distribucion_estados(df: pd.DataFrame, guardar: bool = True) -> Optional[str]:
    """
    Genera un gráfico de barras mostrando la distribución de tareas por estado.
    
    Args:
        df: DataFrame con las tareas
        guardar: Si True, guarda el gráfico en un archivo
        
    Returns:
        str: Ruta del archivo guardado o None
    """
    if df.empty or 'situacion' not in df.columns:
        print("⚠️  No hay datos suficientes para generar el gráfico")
        return None
    
    # 4.1. Contar tareas por estado
    estados = df['situacion'].value_counts()
    
    # 4.2. Definir colores para cada estado
    colores = {
        'Sin Ejecutar': '#ffc107',
        'En Ejecución': '#0d6efd',
        'Pendiente de': '#e67e22',
        'Completada': '#27ae60',
        'Validada': '#8e44ad'
    }
    colores_lista = [colores.get(estado, '#95a5a6') for estado in estados.index]
    
    # 4.3. Crear figura y eje
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 4.4. Generar gráfico de barras
    ax.bar(estados.index, estados.values, color=colores_lista)
    ax.set_xlabel('Estado', fontweight='bold')
    ax.set_ylabel('Cantidad de Tareas', fontweight='bold')
    ax.set_title('Distribución de Tareas por Estado', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    # 4.5. Rotar etiquetas para mejor legibilidad
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # 4.6. Guardar o mostrar
    if guardar:
        ruta = os.path.join(OUTPUT_DIR, 'distribucion_estados.png')
        plt.savefig(ruta, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico guardado en: {ruta}")
        plt.close()
        return ruta
    else:
        plt.show()
        return None


# ============================================================================
# 5. GRAFICAR TOP 5 RESPONSABLES POR CANTIDAD DE TAREAS
# ============================================================================

def grafico_distribucion_responsables(df: pd.DataFrame, top_n: int = 5, guardar: bool = True) -> Optional[str]:
    """
    Genera un gráfico de barras horizontales con los principales responsables.
    
    Args:
        df: DataFrame con las tareas
        top_n: Número de responsables principales a mostrar
        guardar: Si True, guarda el gráfico en un archivo
        
    Returns:
        str: Ruta del archivo guardado o None
    """
    if df.empty or 'responsable' not in df.columns:
        print("⚠️  No hay datos suficientes para generar el gráfico")
        return None
    
    # 5.1. Filtrar responsables vacíos
    df_filtrado = df[df['responsable'].notna() & (df['responsable'] != '')]
    
    if df_filtrado.empty:
        print("⚠️  No hay responsables asignados")
        return None
    
    # 5.2. Obtener top N responsables
    responsables = df_filtrado['responsable'].value_counts().head(top_n)
    
    # 5.3. Crear figura y eje
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 5.4. Generar gráfico de barras horizontales
    ax.barh(responsables.index, responsables.values, color='#3498db')
    ax.set_xlabel('Cantidad de Tareas', fontweight='bold')
    ax.set_ylabel('Responsable', fontweight='bold')
    ax.set_title(f'Top {top_n} Responsables por Cantidad de Tareas', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    # 5.5. Guardar o mostrar
    if guardar:
        ruta = os.path.join(OUTPUT_DIR, 'distribucion_responsables.png')
        plt.savefig(ruta, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico guardado en: {ruta}")
        plt.close()
        return ruta
    else:
        plt.show()
        return None


# ============================================================================
# 6. GRAFICAR DISTRIBUCIÓN POR CENTROS DE RESPONSABILIDAD
# ============================================================================

def grafico_distribucion_centros(df: pd.DataFrame, guardar: bool = True) -> Optional[str]:
    """
    Genera un gráfico de pastel (pie chart) con la distribución por centros.
    
    Args:
        df: DataFrame con las tareas
        guardar: Si True, guarda el gráfico en un archivo
        
    Returns:
        str: Ruta del archivo guardado o None
    """
    if df.empty or 'centro_responsabilidad' not in df.columns:
        print("⚠️  No hay datos suficientes para generar el gráfico")
        return None
    
    # 6.1. Filtrar centros vacíos
    df_filtrado = df[df['centro_responsabilidad'].notna() & (df['centro_responsabilidad'] != '')]
    
    if df_filtrado.empty:
        print("⚠️  No hay centros asignados")
        return None
    
    # 6.2. Contar tareas por centro
    centros = df_filtrado['centro_responsabilidad'].value_counts()
    
    # 6.3. Crear figura y eje
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 6.4. Generar gráfico de pastel
    ax.pie(centros.values, labels=centros.index, autopct='%1.1f%%', startangle=90)
    ax.set_title('Distribución de Tareas por Centro de Responsabilidad', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    # 6.5. Guardar o mostrar
    if guardar:
        ruta = os.path.join(OUTPUT_DIR, 'distribucion_centros.png')
        plt.savefig(ruta, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico guardado en: {ruta}")
        plt.close()
        return ruta
    else:
        plt.show()
        return None


# ============================================================================
# 7. GRAFICAR LÍNEA TEMPORAL DE TAREAS POR PLAZO
# ============================================================================

def grafico_linea_temporal(df: pd.DataFrame, guardar: bool = True) -> Optional[str]:
    """
    Genera un gráfico de línea temporal mostrando tareas por fecha de plazo.
    
    Args:
        df: DataFrame con las tareas
        guardar: Si True, guarda el gráfico en un archivo
        
    Returns:
        str: Ruta del archivo guardado o None
    """
    if df.empty or 'plazo_date' not in df.columns:
        print("⚠️  No hay datos suficientes para generar el gráfico")
        return None
    
    # 7.1. Filtrar tareas con plazo válido
    df_filtrado = df[df['plazo_date'].notna()].copy()
    
    if df_filtrado.empty:
        print("⚠️  No hay tareas con plazo asignado")
        return None
    
    # 7.2. Agrupar por fecha y contar tareas
    df_filtrado['fecha'] = df_filtrado['plazo_date'].dt.date
    tareas_por_fecha = df_filtrado.groupby('fecha').size().reset_index(name='cantidad')
    tareas_por_fecha = tareas_por_fecha.sort_values('fecha')
    
    # 7.3. Crear figura y eje
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # 7.4. Generar gráfico de línea
    ax.plot(tareas_por_fecha['fecha'], tareas_por_fecha['cantidad'], 
            marker='o', linewidth=2, markersize=8, color='#3498db')
    ax.set_xlabel('Fecha de Plazo', fontweight='bold')
    ax.set_ylabel('Cantidad de Tareas', fontweight='bold')
    ax.set_title('Distribución Temporal de Tareas por Plazo', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 7.5. Formatear fechas en el eje X
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    # 7.6. Guardar o mostrar
    if guardar:
        ruta = os.path.join(OUTPUT_DIR, 'linea_temporal.png')
        plt.savefig(ruta, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico guardado en: {ruta}")
        plt.close()
        return ruta
    else:
        plt.show()
        return None


# ============================================================================
# 8. GRAFICAR RELACIÓN ENTRE ESTADO Y PLAZO
# ============================================================================

def grafico_estado_plazo(df: pd.DataFrame, guardar: bool = True) -> Optional[str]:
    """
    Genera un gráfico de barras apiladas mostrando la relación entre estado y plazo.
    
    Args:
        df: DataFrame con las tareas
        guardar: Si True, guarda el gráfico en un archivo
        
    Returns:
        str: Ruta del archivo guardado o None
    """
    if df.empty or 'situacion' not in df.columns or 'dias_restantes' not in df.columns:
        print("⚠️  No hay datos suficientes para generar el gráfico")
        return None
    
    # 8.1. Filtrar tareas con plazo
    df_filtrado = df[df['dias_restantes'].notna()].copy()
    
    if df_filtrado.empty:
        print("⚠️  No hay tareas con plazo asignado")
        return None
    
    # 8.2. Crear grupos de días restantes
    bins = [-float('inf'), 0, 7, 30, 90, float('inf')]
    labels = ['Vencidas', '0-7 días', '8-30 días', '31-90 días', 'Más de 90 días']
    df_filtrado['grupo_plazo'] = pd.cut(df_filtrado['dias_restantes'], bins=bins, labels=labels)
    
    # 8.3. Crear tabla cruzada (estado vs grupo de plazo)
    tabla_cruzada = pd.crosstab(df_filtrado['situacion'], df_filtrado['grupo_plazo'])
    
    # 8.4. Crear figura y eje
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 8.5. Generar gráfico de barras apiladas
    tabla_cruzada.plot(kind='bar', stacked=True, ax=ax, colormap='Set3')
    ax.set_xlabel('Estado', fontweight='bold')
    ax.set_ylabel('Cantidad de Tareas', fontweight='bold')
    ax.set_title('Distribución de Tareas por Estado y Plazo', fontsize=14, fontweight='bold')
    ax.legend(title='Plazo', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # 8.6. Guardar o mostrar
    if guardar:
        ruta = os.path.join(OUTPUT_DIR, 'estado_plazo.png')
        plt.savefig(ruta, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico guardado en: {ruta}")
        plt.close()
        return ruta
    else:
        plt.show()
        return None


# ============================================================================
# 9. EXPORTAR DATOS A DIFERENTES FORMATOS
# ============================================================================

def exportar_a_csv(df: pd.DataFrame, nombre_archivo: str = 'tareas_analisis.csv') -> Optional[str]:
    """
    Exporta el DataFrame a un archivo CSV.
    
    Args:
        df: DataFrame con las tareas
        nombre_archivo: Nombre del archivo CSV a crear
        
    Returns:
        str: Ruta del archivo creado o None
    """
    if df.empty:
        print("⚠️  No hay datos para exportar")
        return None
    
    # 9.1. Construir ruta completa
    ruta = os.path.join(OUTPUT_DIR, nombre_archivo)
    
    try:
        # 9.2. Exportar a CSV con codificación UTF-8
        df.to_csv(ruta, index=False, encoding='utf-8-sig')
        print(f"✅ Archivo CSV exportado: {ruta}")
        return ruta
    except Exception as e:
        print(f"❌ Error al exportar a CSV: {e}")
        return None


def exportar_a_excel(df: pd.DataFrame, nombre_archivo: str = 'tareas_analisis.xlsx') -> Optional[str]:
    """
    Exporta el DataFrame a un archivo Excel con múltiples hojas.
    
    Args:
        df: DataFrame con las tareas
        nombre_archivo: Nombre del archivo Excel a crear
        
    Returns:
        str: Ruta del archivo creado o None
    """
    if df.empty:
        print("⚠️  No hay datos para exportar")
        return None
    
    # 9.3. Construir ruta completa
    ruta = os.path.join(OUTPUT_DIR, nombre_archivo)
    
    try:
        # 9.4. Crear archivo Excel con múltiples hojas
        with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
            # Hoja 1: Todas las tareas
            df.to_excel(writer, sheet_name='Todas las Tareas', index=False)
            
            # Hoja 2: Resumen por estado
            if 'situacion' in df.columns:
                resumen_estado = df['situacion'].value_counts().reset_index()
                resumen_estado.columns = ['Estado', 'Cantidad']
                resumen_estado.to_excel(writer, sheet_name='Resumen por Estado', index=False)
            
            # Hoja 3: Resumen por responsable
            if 'responsable' in df.columns:
                df_resp = df[df['responsable'].notna() & (df['responsable'] != '')]
                if not df_resp.empty:
                    resumen_resp = df_resp['responsable'].value_counts().reset_index()
                    resumen_resp.columns = ['Responsable', 'Cantidad']
                    resumen_resp.to_excel(writer, sheet_name='Resumen por Responsable', index=False)
            
            # Hoja 4: Resumen por centro
            if 'centro_responsabilidad' in df.columns:
                df_centro = df[df['centro_responsabilidad'].notna() & (df['centro_responsabilidad'] != '')]
                if not df_centro.empty:
                    resumen_centro = df_centro['centro_responsabilidad'].value_counts().reset_index()
                    resumen_centro.columns = ['Centro de Responsabilidad', 'Cantidad']
                    resumen_centro.to_excel(writer, sheet_name='Resumen por Centro', index=False)
            
            # Hoja 5: Tareas vencidas
            if 'vencida' in df.columns:
                tareas_vencidas = df[df['vencida'] == True]
                if not tareas_vencidas.empty:
                    tareas_vencidas.to_excel(writer, sheet_name='Tareas Vencidas', index=False)
        
        print(f"✅ Archivo Excel exportado: {ruta}")
        return ruta
    
    except Exception as e:
        print(f"❌ Error al exportar a Excel: {e}")
        print("💡 Instala openpyxl: pip install openpyxl")
        return None


# ============================================================================
# 10. FUNCIÓN PRINCIPAL: GENERAR REPORTE COMPLETO
# ============================================================================

def generar_reporte_completo():
    """
    Genera un reporte completo con todos los análisis y gráficos.
    Esta función ejecuta todos los pasos del análisis en secuencia.
    """
    print("=" * 60)
    print("📊 GENERANDO REPORTE COMPLETO DE ANÁLISIS")
    print("=" * 60)
    
    # Paso 1: Cargar datos
    print("\n[PASO 1] Cargando datos...")
    df = cargar_tareas()
    
    if df.empty:
        print("❌ No hay datos para analizar")
        return
    
    # Paso 2: Calcular estadísticas generales
    print("\n[PASO 2] Calculando estadísticas generales...")
    estadisticas = analisis_general(df)
    print("  • Total de tareas:", estadisticas.get('total_tareas', 0))
    print("  • Tareas vencidas:", estadisticas.get('tareas_vencidas', 0))
    print("  • Tareas por vencer:", estadisticas.get('tareas_por_vencer', 0))
    
    # Paso 3: Determinar rankings
    print("\n[PASO 3] Determinando rankings...")
    top_responsables = obtener_top_responsables(df, top_n=5)
    if not top_responsables.empty:
        print("  • Top 5 Responsables:")
        for _, row in top_responsables.iterrows():
            print(f"    - {row['responsable']}: {row['cantidad_tareas']} tareas")
    
    top_centros = obtener_top_centros(df, top_n=5)
    if not top_centros.empty:
        print("  • Top 5 Centros:")
        for _, row in top_centros.iterrows():
            print(f"    - {row['centro_responsabilidad']}: {row['cantidad_tareas']} tareas")
    
    tareas_criticas = obtener_tareas_criticas(df)
    if not tareas_criticas.empty:
        print(f"  • Tareas críticas encontradas: {len(tareas_criticas)}")
    
    # Paso 4: Graficar distribución por estado
    print("\n[PASO 4] Generando gráfico de distribución por estado...")
    grafico_distribucion_estados(df)
    
    # Paso 5: Graficar top 5 responsables
    print("\n[PASO 5] Generando gráfico de top 5 responsables...")
    grafico_distribucion_responsables(df, top_n=5)
    
    # Paso 6: Graficar distribución por centros
    print("\n[PASO 6] Generando gráfico de distribución por centros...")
    grafico_distribucion_centros(df)
    
    # Paso 7: Graficar línea temporal
    print("\n[PASO 7] Generando gráfico de línea temporal...")
    grafico_linea_temporal(df)
    
    # Paso 8: Graficar estado vs plazo
    print("\n[PASO 8] Generando gráfico de estado vs plazo...")
    grafico_estado_plazo(df)
    
    # Paso 9: Exportar datos
    print("\n[PASO 9] Exportando datos...")
    exportar_a_csv(df)
    exportar_a_excel(df)
    
    # Resumen final
    print("\n" + "=" * 60)
    print("✅ REPORTE COMPLETO GENERADO")
    print(f"📂 Archivos guardados en: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)


if __name__ == '__main__':
    # Ejecutar reporte completo si se ejecuta directamente
    generar_reporte_completo()
    
    # Ejemplo de uso individual
    print("\n" + "=" * 60)
    print("EJEMPLO DE USO INDIVIDUAL")
    print("=" * 60)
    
    df = cargar_tareas()
    if not df.empty:
        print("\n📊 Análisis de Eficiencia:")
        eficiencia = analisis_eficiencia(df)
        for clave, valor in eficiencia.items():
            if isinstance(valor, float):
                print(f"  • {clave}: {valor:.2f}%")
            else:
                print(f"  • {clave}: {valor}")
