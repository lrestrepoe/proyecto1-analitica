# Limpieza y alistamiento para análisis 

import pandas as pd
from pathlib import Path
import unicodedata


CARPETA_DATOS = r"C:\Users\dburg\Desktop\ActProy1"   
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

    # Duplicados exactos
    antes = len(df)

    duplicados_exactos = df.duplicated().sum()
    print(f"\nDuplicados exactos (fila idéntica en todas las columnas): {duplicados_exactos:,}")

    df = df.drop_duplicates(keep="first").copy()

    despues = len(df)
    print(f"Filas después de quitar duplicados exactos: {despues:,} (antes: {antes:,})")

    #Mismo estu_consecutivo pero con puntaje global diferente
    filas_en_ids_repetidos = df[COL_ID].duplicated(keep=False).sum()

    if filas_en_ids_repetidos > 0:

        df = df.sort_values(by=[COL_ID, COL_PUNT_GLOBAL], ascending=[True, False]).copy()

        antes = len(df)
        df = df.drop_duplicates(subset=[COL_ID], keep="first").copy()
        despues = len(df)

        print(f"Filas después de quedarnos con el mayor punt_global por {COL_ID}: {despues:,} (antes: {antes:,})")

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

# 11.2 Pregunta 1
cols_q1 = [c for c in Q1_COLS if c in df.columns] + ["edad"]
df_q1 = df[cols_q1].copy()

df_q1 = df_q1.dropna(subset=[c for c in Q1_COLS if c in df_q1.columns]).copy()
print(f"Dataframe P1: df_q1 | filas: {len(df_q1):,} | columnas: {len(df_q1.columns)}")

# 11.3 Pregunta 2 
cols_q2 = [c for c in Q2_COLS if c in df.columns] + ["edad"]
df_q2 = df[cols_q2].copy()

df_q2 = df_q2.dropna(subset=[c for c in Q2_COLS if c in df_q2.columns]).copy()
print(f"Dataframe P2: df_q2 | filas: {len(df_q2):,} | columnas: {len(df_q2.columns)}")

# 11.4 Pregunta 3 
cols_q3 = [c for c in Q3_COLS if c in df.columns] + ["edad"]
df_q3 = df[cols_q3].copy()

df_q3 = df_q3.dropna(subset=[c for c in Q3_COLS if c in df_q3.columns]).copy()
print(f"Dataframe P3: df_q3 | filas: {len(df_q3):,} | columnas: {len(df_q3.columns)}")

# 12) ENCABEZADOS

print("\nPrimeras filas df_global:")
print(df_global.head())

print("\nPrimeras filas df_q1:")
print(df_q1.head())

print("\nPrimeras filas df_q2:")
print(df_q2.head())

print("\nPrimeras filas df_q3:")
print(df_q3.head())