# GRAFICOS VENTAS POWWER BI

import pandas as pd
import matplotlib.pyplot as plt
import os

# ==============================
# CONFIGURACIÓN
# ==============================
RUTA_CSV = r"C:\Users\juan.gallardo\OneDrive - JUNAEB\DAE REMOTO 00\ÁREA GESTIÓN\CURSOS JUANMA APRENDIZAJE\Curso Python Santander University\Archivos Cursos\ventas.csv"

OUTPUT_DIR = "output_graficos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================
# CARGA DE DATOS
# ==============================
df = pd.read_csv(RUTA_CSV, sep=";")

# ==============================
# 1️⃣ VENTAS POR MES
# ==============================
df['Fecha_Venta'] = pd.to_datetime(df['Outlet_Establishment_Year'], format='%Y')
ventas_mes = df.groupby(df['Fecha_Venta'].dt.to_period('M'))['Item_Outlet_Sales'].sum()

ventas_mes.plot(figsize=(10,5))
plt.title("Ventas por Mes")
plt.xlabel("Periodo")
plt.ylabel("Ventas")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/ventas_por_mes.png")
plt.close()

# ==============================
# 2️⃣ VENTAS POR TIPO DE PRODUCTO
# ==============================
ventas_producto = df.groupby('Item_Type')['Item_Outlet_Sales'].sum().sort_values(ascending=False)

ventas_producto.plot(kind='bar', figsize=(12,5))
plt.title("Ventas por Tipo de Producto")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/ventas_por_producto.png")
plt.close()

# ==============================
# 3️⃣ VENTAS POR TIPO DE TIENDA
# ==============================
ventas_tienda = df.groupby('Outlet_Type')['Item_Outlet_Sales'].sum()

ventas_tienda.plot(kind='bar', figsize=(8,5))
plt.title("Ventas por Tipo de Tienda")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/ventas_por_tienda.png")
plt.close()

# ==============================
# 4️⃣ TOP 10 PRODUCTOS POR INGRESOS
# ==============================
top_productos = df.groupby('Item_Identifier')['Item_Outlet_Sales'].sum().sort_values(ascending=False).head(10)

top_productos.plot(kind='bar', figsize=(10,5))
plt.title("Top 10 Productos por Ingresos")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/top_10_productos.png")
plt.close()

# ==============================
# 5️⃣ DISTRIBUCIÓN TAMAÑO DE TIENDA
# ==============================
df['Outlet_Size'].value_counts().plot(kind='pie', autopct='%1.1f%%', figsize=(6,6))
plt.title("Distribución Tamaño de Tienda")
plt.ylabel("")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/distribucion_tamano_tienda.png")
plt.close()

print("✅ 5 gráficos generados correctamente en carpeta output_graficos")

df.to_csv("output_ventas/ventas_limpias.csv", index=False)

print("✅ CSV y Excel exportados")
