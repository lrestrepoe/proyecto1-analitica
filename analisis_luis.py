# Limpieza y alistamiento para análisis (enfocado a Q3, manteniendo limpieza completa)

import pandas as pd
from pathlib import Path
import unicodedata

CARPETA_DATOS = r"C:\Users\Krest\OneDrive\Escritorio\Uniandes\8\analitica\Proyecto1"
NOMBRE_ARCHIVO = "DatosSaber11_Bolivar.csv"

PERIODO_MINIMO = 20141

COL_ID = "estu_consecutivo"
COL_FECHA_NAC = "estu_fechanacimiento"
COL_PERIODO = "periodo"
COL_PUNT_GLOBAL = "punt_global"
COL_COLE_NATURALEZA = "cole_naturaleza"

Q1_COLS = [
    "cole_bilingue",
    "cole_naturaleza",
    "fami_estratovivienda",
    "fami_tienecomputador",
    "fami_tieneinternet",
    "punt_global",
]

Q2_COLS = [
    "estu_genero",
    "cole_genero",
    "cole_caracter",
    "cole_naturaleza",
    "fami_estratovivienda",
    "punt_ingles",
    "punt_matematicas",
    "punt_lectura_critica",
    "punt_c_naturales",
    "punt_sociales_ciudadanas",
    "punt_global",
]

# ✅ Q3: agregamos variables necesarias para análisis por colegio
Q3_COLS = [
    "fami_educacionmadre",
    "fami_educacionpadre",
    "cole_codigo_icfes",              # ✅ necesario
    "cole_nombre_establecimiento",    # ✅ útil para reportes
    "cole_jornada",                   # ✅ segmento
    "cole_area_ubicacion",
    "cole_caracter",
    "cole_naturaleza",
    "punt_ingles",
    "punt_matematicas",
    "punt_lectura_critica",
    "punt_c_naturales",
    "punt_sociales_ciudadanas",
    "punt_global",
]

GLOBAL_COLS = list(dict.fromkeys(
    [COL_ID, COL_PERIODO, COL_FECHA_NAC] + Q1_COLS + Q2_COLS + Q3_COLS
))

def normalizar_texto(x):
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

ruta = Path(CARPETA_DATOS)
archivo = ruta / NOMBRE_ARCHIVO
if not archivo.exists() and not NOMBRE_ARCHIVO.lower().endswith(".csv"):
    archivo = ruta / f"{NOMBRE_ARCHIVO}.csv"
if not archivo.exists():
    raise FileNotFoundError(f"No encontré el archivo en: {archivo}")

df_raw = pd.read_csv(
    archivo,
    dtype=str,
    low_memory=False,
    encoding_errors="replace"
)

# ✅ blindaje por espacios raros en headers
df_raw.columns = df_raw.columns.str.strip()

cols_existentes = [c for c in GLOBAL_COLS if c in df_raw.columns]
cols_faltantes = [c for c in GLOBAL_COLS if c not in df_raw.columns]

# (print corto y útil)
if cols_faltantes:
    print("\nOJO: columnas esperadas que no existen en el CSV (se omiten):")
    for c in cols_faltantes:
        print(" -", c)

df = df_raw[cols_existentes].copy()

# estandarización de valores faltantes
df = df.replace({
    "": pd.NA, " ": pd.NA,
    "NA": pd.NA, "N/A": pd.NA,
    "NULL": pd.NA, "NONE": pd.NA,
    "NAN": pd.NA
})

# Normalización de categóricas
categ_cols = set([
    "cole_bilingue",
    "cole_area_ubicacion",
    "cole_naturaleza",
    "cole_jornada",
    "cole_caracter",
    "cole_genero",
    "estu_genero",
    "fami_estratovivienda",
    "fami_tienecomputador",
    "fami_tieneinternet",
    "fami_educacionmadre",
    "fami_educacionpadre",
    "desemp_ingles",
    "cole_nombre_establecimiento",
])

for c in df.columns:
    if c in categ_cols:
        df[c] = df[c].apply(normalizar_texto)

if "cole_bilingue" in df.columns:
    df["cole_bilingue"] = df["cole_bilingue"].replace({"SI": "S", "NO": "N"})

# Puntaje global numérico
if COL_PUNT_GLOBAL in df.columns:
    df[COL_PUNT_GLOBAL] = pd.to_numeric(df[COL_PUNT_GLOBAL], errors="coerce")

# Periodo numérico
if COL_PERIODO in df.columns:
    df["periodo_int"] = pd.to_numeric(df[COL_PERIODO], errors="coerce")
else:
    df["periodo_int"] = pd.NA

# Filtrar periodo
df = df[df["periodo_int"].notna() & (df["periodo_int"] >= PERIODO_MINIMO)].copy()

# Filtrar punt_global válido
df = df.dropna(subset=[COL_PUNT_GLOBAL]).copy()
df = df[(df[COL_PUNT_GLOBAL] >= 0) & (df[COL_PUNT_GLOBAL] <= 500)].copy()

# Pruebas 0-100
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

# Duplicados por ID
if COL_ID in df.columns:
    df = df.drop_duplicates(keep="first").copy()

    filas_repetidas_id = df[COL_ID].duplicated(keep=False).sum()
    if filas_repetidas_id > 0:
        df = df.sort_values(by=[COL_ID, COL_PUNT_GLOBAL], ascending=[True, False]).copy()
        df = df.drop_duplicates(subset=[COL_ID], keep="first").copy()

# Edad
if COL_FECHA_NAC in df.columns:
    df["fecha_nac_dt"] = pd.to_datetime(df[COL_FECHA_NAC], errors="coerce", dayfirst=True)
else:
    df["fecha_nac_dt"] = pd.NaT

df["fecha_examen_aprox"] = df[COL_PERIODO].apply(periodo_a_fecha_aprox)
df["edad"] = (df["fecha_examen_aprox"] - df["fecha_nac_dt"]).dt.days / 365.25
df["edad"] = df["edad"].apply(lambda x: int(x) if pd.notna(x) else pd.NA)

# ==========================================================
# DATASET FINAL SOLO PARA PREGUNTA 3
# ==========================================================
cols_q3a = [
    "punt_global",
    "fami_educacionmadre",
    "fami_educacionpadre",
    "cole_codigo_icfes",
    "cole_nombre_establecimiento",
    "cole_area_ubicacion",
    "cole_caracter",
    "cole_naturaleza",
    "cole_jornada",
]
cols_q3a = [c for c in cols_q3a if c in df.columns]
df_q3a = df[cols_q3a].copy()

# Reporte corto de faltantes solo Q3
rep_q3 = pd.DataFrame({
    "columna": df_q3a.columns,
    "pct_nulos": (df_q3a.isna().mean() * 100).round(2),
    "nulos": df_q3a.isna().sum()
}).sort_values("pct_nulos", ascending=False)
print("\nFaltantes (solo variables Q3):")
print(rep_q3.to_string(index=False))

# Requeridas para análisis
df_q3a = df_q3a.dropna(subset=[
    "punt_global", "fami_educacionmadre", "fami_educacionpadre", "cole_codigo_icfes"
]).copy()

print(f"\nQ3 listo: filas = {len(df_q3a):,} | colegios = {df_q3a['cole_codigo_icfes'].nunique():,}")

# EDA ENFOCADO A PREGUNTA 3
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

edu_map = {
    "NINGUNO": 0,
    "PRIMARIA INCOMPLETA": 1,
    "PRIMARIA COMPLETA": 1,
    "SECUNDARIA (BACHILLERATO) INCOMPLETA": 2,
    "SECUNDARIA (BACHILLERATO) COMPLETA": 2,
    "TECNICA O TECNOLOGICA INCOMPLETA": 3,
    "TECNICA O TECNOLOGICA COMPLETA": 3,
    "PROFESIONAL INCOMPLETA": 4,
    "PROFESIONAL COMPLETA": 4,
    "POSTGRADO": 5,
    "MAESTRIA": 5,
    "DOCTORADO": 5,
}

df_q3a["edu_madre_n"] = df_q3a["fami_educacionmadre"].map(edu_map)
df_q3a["edu_padre_n"] = df_q3a["fami_educacionpadre"].map(edu_map)
df_q3a = df_q3a.dropna(subset=["edu_madre_n", "edu_padre_n"]).copy()

df_q3a["capital_educativo"] = df_q3a[["edu_madre_n", "edu_padre_n"]].mean(axis=1)

corr_global = df_q3a["capital_educativo"].corr(df_q3a["punt_global"])
print(f"\nCorrelación global capital educativo vs puntaje: {corr_global:.3f}")

# Distribución puntaje
plt.figure()
df_q3a["punt_global"].hist(bins=40)
plt.title("Distribución Puntaje Global")
plt.xlabel("punt_global"); plt.ylabel("frecuencia")
plt.show()

# Relación (boxplot)
plt.figure()
sns.boxplot(data=df_q3a, x="capital_educativo", y="punt_global")
plt.title("Puntaje Global vs Capital Educativo Familiar")
plt.show()

# Dispersión
plt.figure()
sns.scatterplot(
    data=df_q3a.sample(min(len(df_q3a), 5000), random_state=1),
    x="capital_educativo", y="punt_global", alpha=0.3
)
plt.title("Capital Educativo vs Puntaje Global (muestra)")
plt.show()

# Heatmap correlación
corr = df_q3a[["punt_global", "edu_madre_n", "edu_padre_n", "capital_educativo"]].corr()
plt.figure()
sns.heatmap(corr, annot=True, fmt=".2f", cmap="Blues")
plt.title("Heatmap correlaciones")
plt.show()

# Segmentos: dónde se debilita
segmentos = ["cole_naturaleza", "cole_area_ubicacion", "cole_caracter", "cole_jornada"]
for seg in segmentos:
    if seg in df_q3a.columns:
        tabla = (
            df_q3a.groupby(seg)
            .apply(lambda g: g["capital_educativo"].corr(g["punt_global"]) if len(g) >= 200 else np.nan)
            .dropna()
            .sort_values()
        )
        print(f"\nCorrelación por {seg} (min n=200):")
        print(tabla.round(3))

# Colegios: brecha ALTO vs BAJO capital educativo
df_q3a["cap_bin"] = pd.qcut(df_q3a["capital_educativo"], q=2, labels=["BAJO", "ALTO"])

brecha = (
    df_q3a.groupby(["cole_codigo_icfes", "cap_bin"])["punt_global"].mean()
    .unstack()
    .dropna()
)
brecha["gap_alto_bajo"] = brecha["ALTO"] - brecha["BAJO"]
brecha = brecha.sort_values("gap_alto_bajo")

print("\nTop 10 colegios con menor brecha (posible compensación):")
print(brecha.head(10)[["gap_alto_bajo"]].round(2))

top10_ids = brecha.head(10).index.tolist()
plt.figure(figsize=(12, 5))
sns.boxplot(
    data=df_q3a[df_q3a["cole_codigo_icfes"].isin(top10_ids)],
    x="cole_codigo_icfes", y="punt_global", hue="cap_bin"
)
plt.xticks(rotation=45, ha="right")
plt.title("Top 10 colegios con menor brecha: puntaje por capital educativo")
plt.tight_layout()
plt.show()
