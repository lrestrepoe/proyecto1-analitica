# Limpieza y alistamiento para análisis 

import pandas as pd
from pathlib import Path
import unicodedata


CARPETA_DATOS = r"/Users/macbook/Desktop/Andes/Semestre 8/Analitica/Proyecto1/proyecto1-analitica"   
NOMBRE_ARCHIVO = "DatosSaber11_Bolivar.csv"          

PERIODO_MINIMO = 20141

# Llave para duplicados
COL_ID = "estu_consecutivo"

# Edad
COL_FECHA_NAC = "estu_fechanacimiento"
COL_PERIODO = "periodo"

# Puntaje gGLOBAL
COL_PUNT_GLOBAL = "punt_global"

# Pregunta 1
Q1_COLS = [
    "cole_bilingue",
    "fami_estratovivienda",
    "fami_tienecomputador",
    "fami_tieneinternet",
    "punt_global",
]

# Pregunta 2 
Q2_COLS = [
    "estu_genero",
    "cole_genero",
    "cole_caracter",
    "fami_estratovivienda",
    "punt_ingles",
    "punt_matematicas",
    "punt_lectura_critica",
    "punt_c_naturales",
    "punt_sociales_ciudadanas",
    "punt_global",
]

# Pregunta 3
Q3_COLS = [
    "fami_educacionmadre",
    "fami_educacionpadre",
    "punt_global",
]

GLOBAL_COLS = list(dict.fromkeys(
    [COL_ID, COL_PERIODO, COL_FECHA_NAC] + Q1_COLS + Q2_COLS + Q3_COLS
))


def normalizar_texto(x):
    """
    Deja el texto consistente:
    - quita espacios
    - pasa a mayúsculas
    - quita tildes
    """
    if pd.isna(x):
        return pd.NA
    x = str(x).strip().upper()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(c for c in x if not unicodedata.combining(c))
    return x


def periodo_a_fecha_aprox(periodo):

    if pd.isna(periodo):
        return pd.NaT

    p = str(periodo).strip()
    if len(p) < 5:
        return pd.NaT

    try:
        anio = int(p[:4])
        trimestre = int(p[-1])
    except:
        return pd.NaT

    if trimestre not in [1, 2, 3, 4]:
        return pd.NaT

    mes_por_trimestre = {1: 2, 2: 5, 3: 8, 4: 11}
    return pd.Timestamp(year=anio, month=mes_por_trimestre[trimestre], day=15)


def imprimir_reporte_faltantes(df, nombre):
    rep = pd.DataFrame({
        "columna": df.columns,
        "nulos": [df[c].isna().sum() for c in df.columns],
        "porcentaje_nulos": [round(df[c].isna().mean() * 100, 2) for c in df.columns],
    }).sort_values("porcentaje_nulos", ascending=False)

    print(f"\nREPORTE DE FALTANTES -> {nombre}")
    print(rep.to_string(index=False))
    return rep


# 3) CARGA DEL ARCHIVO 
ruta = Path(CARPETA_DATOS)

archivo = ruta / NOMBRE_ARCHIVO
if not archivo.exists() and not NOMBRE_ARCHIVO.lower().endswith(".csv"):
    archivo = ruta / f"{NOMBRE_ARCHIVO}.csv"

if not archivo.exists():
    raise FileNotFoundError(
        f"No encontré el archivo en: {archivo}\n"
        "Revisa CARPETA_DATOS y NOMBRE_ARCHIVO al inicio del script."
    )

print(f"Leyendo archivo: {archivo}")

df_raw = pd.read_csv(
    archivo,
    dtype=str,
    low_memory=False,
    encoding_errors="replace"
)

print(f"Filas totales leídas: {len(df_raw):,}")

cols_existentes = [c for c in GLOBAL_COLS if c in df_raw.columns]
cols_faltantes = [c for c in GLOBAL_COLS if c not in df_raw.columns]

if cols_faltantes:
    for c in cols_faltantes:
        print(" -", c)

df = df_raw[cols_existentes].copy()


# 4) LIMPIEZA DE NULOS

df = df.replace({
    "": pd.NA, " ": pd.NA,
    "NA": pd.NA, "N/A": pd.NA,
    "NULL": pd.NA, "NONE": pd.NA,
    "NAN": pd.NA
})

categ_cols = set([
    "cole_bilingue",
    "fami_estratovivienda",
    "fami_tienecomputador",
    "fami_tieneinternet",
    "estu_genero",
    "cole_genero",
    "cole_caracter",
    "fami_educacionmadre",
    "fami_educacionpadre",
    "desemp_ingles",
])

for c in df.columns:
    if c in categ_cols:
        df[c] = df[c].apply(normalizar_texto)

# Normalización pequeña para bilingüe
if "cole_bilingue" in df.columns:
    df["cole_bilingue"] = df["cole_bilingue"].replace({"SI": "S", "NO": "N"})

# 5) CONSULTA: PERIODOS punt_global VACÍO

if COL_PUNT_GLOBAL in df.columns:
    df[COL_PUNT_GLOBAL] = pd.to_numeric(df[COL_PUNT_GLOBAL], errors="coerce")

if COL_PERIODO in df.columns:
    df["periodo_int"] = pd.to_numeric(df[COL_PERIODO], errors="coerce")
else:
    df["periodo_int"] = pd.NA

if COL_PERIODO in df.columns and COL_PUNT_GLOBAL in df.columns:
    resumen_periodo = (
        df.groupby(COL_PERIODO)[COL_PUNT_GLOBAL]
        .agg(total="size", nulos=lambda s: s.isna().sum())
        .reset_index()
    )
    resumen_periodo["pct_nulos"] = (resumen_periodo["nulos"] / resumen_periodo["total"] * 100).round(2)

    resumen_periodo = resumen_periodo.sort_values("pct_nulos", ascending=False)

    print("\nPERIODOS DONDE punt_global ESTÁ VACÍO (ordenados por % de vacíos)")
    print(resumen_periodo.head(20).to_string(index=False))

    periodos_todos_vacios = resumen_periodo[resumen_periodo["pct_nulos"] == 100][COL_PERIODO].tolist()
    if periodos_todos_vacios:
        print("\nPeriodos donde punt_global está 100% vacío:")
        print(periodos_todos_vacios)

# 6) PERIODOS EN ADELANTE CON PUNTAJE GLOBAL

antes = len(df)
df = df[df["periodo_int"].notna() & (df["periodo_int"] >= PERIODO_MINIMO)].copy()
despues = len(df)
print(f"\nFilas después de filtrar periodo >= {PERIODO_MINIMO}: {despues:,} (antes: {antes:,})")

antes = len(df)
df = df.dropna(subset=[COL_PUNT_GLOBAL]).copy()
despues = len(df)
print(f"Filas después de eliminar punt_global vacío: {despues:,} (antes: {antes:,})")


# 7) ELIMINACIÓN DE ABERRANTES

antes = len(df)
df = df[(df[COL_PUNT_GLOBAL] >= 0) & (df[COL_PUNT_GLOBAL] <= 500)].copy()
despues = len(df)
print(f"Filas después de eliminar punt_global aberrante: {despues:,} (antes: {antes:,})")

# Puntajes por prueba:
pruebas_0_100 = [
    "punt_ingles",
    "punt_matematicas",
    "punt_lectura_critica",
    "punt_c_naturales",
    "punt_sociales_ciudadanas",
]

for col in pruebas_0_100:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        
        df = df[(df[col].isna()) | ((df[col] >= 0) & (df[col] <= 100))].copy()

# 8) DUPLICADOS POR estu_consecutivo

if COL_ID in df.columns:
    duplicados = df.duplicated(subset=[COL_ID]).sum()
    print(f"\nDuplicados detectados por {COL_ID}: {duplicados:,}")

    antes = len(df)
    df = df.drop_duplicates(subset=[COL_ID], keep="first").copy()
    despues = len(df)
    print(f"Filas después de quitar duplicados: {despues:,} (antes: {antes:,})")

# 9) CREAR EDAD

if COL_FECHA_NAC in df.columns:
    df["fecha_nac_dt"] = pd.to_datetime(df[COL_FECHA_NAC], errors="coerce", dayfirst=True)
else:
    df["fecha_nac_dt"] = pd.NaT

# Fecha examen aproximada desde periodo
df["fecha_examen_aprox"] = df[COL_PERIODO].apply(periodo_a_fecha_aprox)

# Edad en años
df["edad"] = (df["fecha_examen_aprox"] - df["fecha_nac_dt"]).dt.days / 365.25
df["edad"] = df["edad"].apply(lambda x: int(x) if pd.notna(x) else pd.NA)


# 10) REPORTE DE FALTANTES 

imprimir_reporte_faltantes(df, "df_base_limpio")

# 11)  DATAFRAMES 

# 11.1 Dataframe global 
cols_global_final = [c for c in GLOBAL_COLS if c in df.columns] + ["edad"]
cols_global_final = list(dict.fromkeys(cols_global_final))
df_global = df[cols_global_final].copy()

print(f"\nDataframe global: df_global | filas: {len(df_global):,} | columnas: {len(df_global.columns)}")

# 11.3 Pregunta 2 
cols_q2 = [c for c in Q2_COLS if c in df.columns] + ["edad"]
df_q2 = df[cols_q2].copy()

df_q2 = df_q2.dropna(subset=[c for c in Q2_COLS if c in df_q2.columns]).copy()
print(f"Dataframe P2: df_q2 | filas: {len(df_q2):,} | columnas: {len(df_q2.columns)}")

# 12) ENCABEZADOS

print("\nPrimeras filas df_q2:")
print(df_q2.head())

#Análisis de Datos Pregunta 2.

# 1. ESTADÍSTICAS DESCRIPTIVAS POR GÉNERO
# Calculamos estadísticas descriptivas (media, std, min, etc.) de puntajes
# separadas por género del estudiante (estu_genero)

import matplotlib.pyplot as plt
import seaborn as sns

cols_puntajes = [
    "punt_ingles",
    "punt_matematicas",
    "punt_lectura_critica",
    "punt_c_naturales",
    "punt_sociales_ciudadanas",
    "punt_global"
]


# TABLA FORMATEADA 
import matplotlib.pyplot as plt
import numpy as np

cols_puntajes = [
    "punt_ingles",
    "punt_matematicas",
    "punt_lectura_critica",
    "punt_c_naturales",
    "punt_sociales_ciudadanas",
    "punt_global"
]

# Nombres bonitos
nombres_pruebas = [
    "INGLÉS",
    "MATEMÁTICAS",
    "LECTURA CRÍTICA",
    "C. NATURALES",
    "SOCIALES",
    "GLOBAL"
]

# Calcular estadísticas
stats = df_q2.groupby("estu_genero")[cols_puntajes].agg(["mean","std","count"]).round(2)

# Extraemos N (es el mismo para todas las pruebas dentro de cada género)
N_genero = stats[cols_puntajes[0]]["count"]

# Construimos columnas solo con Media y Std
columnas = []
for prueba in nombres_pruebas:
    columnas.extend([f"{prueba}\nMedia", f"{prueba}\nStd"])

# Agregamos columna final N
columnas.append("N")

# Construimos matriz manualmente
valores = []

for genero in stats.index:
    fila = []
    for col in cols_puntajes:
        fila.append(stats.loc[genero, (col, "mean")])
        fila.append(stats.loc[genero, (col, "std")])
    
    # Agregamos N una sola vez
    fila.append(int(N_genero.loc[genero]))
    
    valores.append(fila)

# Crear figura
fig, ax = plt.subplots(figsize=(16,6))
ax.axis('off')

tabla = ax.table(
    cellText=valores,
    colLabels=columnas,
    rowLabels=stats.index,
    loc='center'
)

tabla.auto_set_font_size(False)
tabla.set_fontsize(8)
tabla.scale(1.1, 1.4)

plt.title("Estadísticas Descriptivas por Género\n(Media, Desviación Estándar y Tamaño de Muestra)")
plt.tight_layout()
plt.show()

# Contar cuántos estudiantes hay por género
conteo_genero = df_q2["estu_genero"].value_counts()

# Crear figura
fig, ax = plt.subplots()

# Gráfico de pastel
ax.pie(
    conteo_genero.values,                 # valores numéricos
    labels=conteo_genero.index,           # etiquetas (M, F)
    autopct='%1.1f%%',                    # formato porcentaje
    startangle=90                         # rota el gráfico
)

plt.title("Distribución porcentual por género (estu_genero)")
plt.show()

# 2. BRECHA PROMEDIO POR PRUEBA (Hombre - Mujer)
# Calculamos el promedio por género en cada prueba
promedios = df_q2.groupby("estu_genero")[cols_puntajes].mean()

# Calculamos brecha (Hombres - Mujeres)
# OJO: aquí asumimos que en estu_genero: 'M' = Masculino y 'F' = Femenino.
# Si en tus datos aparecen como 'H'/'Mujer'/'Hombre', me avisas y lo ajusto.
brecha_pruebas = promedios.loc["M"] - promedios.loc["F"]

print("Brecha promedio por prueba (Masculino - Femenino):")
print(brecha_pruebas)

# Gráfico de barras de brecha por prueba
brecha_pruebas.plot(kind="bar")

plt.title("Brecha promedio por prueba (Masculino - Femenino)")
plt.xlabel("Prueba")
plt.ylabel("Brecha de puntaje")
plt.show()

# 3. HISTOGRAMA - GLOBAL POR GÉNERO
# Comparamos la distribución de global entre hombres y mujeres

plt.figure(figsize=(8,5))

plt.hist(df_q2[df_q2["estu_genero"]=="M"]["punt_global"],
         bins=30, alpha=0.5, label="Masculino")

plt.hist(df_q2[df_q2["estu_genero"]=="F"]["punt_global"],
         bins=30, alpha=0.5, label="Femenino")

plt.title("Distribución de puntaje en Global por género")
plt.xlabel("Puntaje Global")
plt.ylabel("Frecuencia")
plt.legend()
plt.show()

# 4. DIAGRAMA DE CAJA - GLOBAL POR GÉNERO

# Sirve para ver mediana, dispersión y posibles outliers por género

plt.figure(figsize=(6,5))
df_q2.boxplot(column="punt_global", by="estu_genero")

plt.title("Diagrama de caja - Global por género")
plt.suptitle("")  # Quita el título automático de pandas
plt.xlabel("Género (estu_genero)")
plt.ylabel("Puntaje Global")
plt.show()

# 5. BRECHA EN EL PUNTAJE GLOBAL SEGÚN TIPO DE COLEGIO (cole_caracter)
# Calculamos promedio de matemáticas por (tipo de colegio, género)
tabla_caracter = df_q2.groupby(["cole_caracter", "estu_genero"])["punt_global"].mean().unstack()

# Calculamos brecha (M - F)
tabla_caracter["brecha_M_F"] = tabla_caracter["M"] - tabla_caracter["F"]

print(tabla_caracter)

# Gráfico de barras de la brecha por tipo de colegio
tabla_caracter["brecha_M_F"].plot(kind="bar")

plt.title("Brecha (Masculino - Femenino) en puntaje Global según tipo de colegio")
plt.xlabel("Tipo de colegio")
plt.ylabel("Brecha de puntaje")

# Rotamos etiquetas para que quepan y no se monten
plt.xticks(rotation=45, ha="right")
# Ajusta márgenes automáticamente para que no se corten los labels
plt.tight_layout()
plt.show()

# 7. BRECHA EN PUNTAJE GLOBAL SEGÚN ESTRATO (fami_estratovivienda)

tabla_estrato = df_q2.groupby(["fami_estratovivienda", "estu_genero"])["punt_global"].mean().unstack()
tabla_estrato["brecha_M_F"] = tabla_estrato["M"] - tabla_estrato["F"]

print(tabla_estrato)

tabla_estrato["brecha_M_F"].plot(kind="bar")

plt.title("Brecha (M - F) en Puntaje Global según estrato del hogar")
plt.xlabel("Estrato")
plt.ylabel("Brecha de puntaje")
plt.show()

# 8. MAPA DE CALOR - BRECHA POR PRUEBA (M - F)
promedios_heat = df_q2.groupby("estu_genero")[cols_puntajes].mean()
brecha_heat = (promedios_heat.loc["M"] - promedios_heat.loc["F"]).to_frame(name="brecha_M_F")

sns.heatmap(brecha_heat, annot=True, cmap="coolwarm")
plt.title("Mapa de calor - Brecha (M - F) por prueba")
plt.show()
