# Limpieza y alistamiento (

import pandas as pd
from pathlib import Path
import unicodedata

#CONFIGURACIÓN
DEPARTAMENTO_OBJETIVO = "BOLIVAR"


COLUMNA_DEPTO = "COLE_DEPTO_UBICACION"

# Calculamos la edad de los estudiantes
COL_FECHA_NAC = "ESTU_FECHANACIMIENTO"
COL_PERIODO = "PERIODO"

# Pregunta 1
Q1_COLS = [
    "COLE_BILINGUE",
    "PUNT_GLOBAL",
    "FAMI_ESTRATOVIVIENDA",
    "FAMI_TIENECOMPUTADOR",
    "FAMI_TIENEINTERNET",
]

# Pregunta 2
Q2_COLS = [
    "ESTU_GENERO",
    "COLE_GENERO",
    "COLE_CARACTER",
    "FAMI_ESTRATOVIVIENDA",
    "PUNT_INGLES",
    "PUNT_MATEMATICAS",
    "PUNT_LECTURA_CRITICA",
    "PUNT_C_NATURALES",
    "PUNT_SOCIALES_CIUDADANAS",
]

# Pregunta 3
Q3_COLS = [
    "FAMI_EDUCACIONMADRE",
    "FAMI_EDUCACIONPADRE",
    "PUNT_GLOBAL",
]


def elegir_csv_en_carpeta(carpeta: Path) -> Path:
    """Busca archivos .csv en la carpeta. Si hay varios, escoge el más grande."""
    csvs = list(carpeta.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError("No encontré ningún .csv en la carpeta del script.")
    if len(csvs) == 1:
        return csvs[0]
    return sorted(csvs, key=lambda p: p.stat().st_size, reverse=True)[0]


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


def reporte_faltantes(df, nombre="df"):
    rep = pd.DataFrame({
        "columna": df.columns,
        "nulos": [df[c].isna().sum() for c in df.columns],
        "porcentaje_nulos": [round(df[c].isna().mean() * 100, 2) for c in df.columns],
    }).sort_values("porcentaje_nulos", ascending=False)

    print(f"\nREPORTE DE FALTANTES ({nombre})")
    print(rep.to_string(index=False))
    return rep

# 2) CARGA Y SELECCIÓN

carpeta_script = Path(__file__).resolve().parent
ruta_csv = elegir_csv_en_carpeta(carpeta_script)
print(f"Leyendo: {ruta_csv.name}")


df_raw = pd.read_csv(
    ruta_csv,
    dtype=str,
    low_memory=False,
    encoding_errors="replace"
)

print(f"Filas totales: {len(df_raw):,}")


cols_necesarias = list(dict.fromkeys(
    [COLUMNA_DEPTO, COL_FECHA_NAC, COL_PERIODO] + Q1_COLS + Q2_COLS + Q3_COLS
))


cols_existentes = [c for c in cols_necesarias if c in df_raw.columns]
cols_faltantes = [c for c in cols_necesarias if c not in df_raw.columns]

if cols_faltantes:
    print("\nOJO: Estas columnas no aparecieron en el CSV (revisa nombres exactos):")
    for c in cols_faltantes:
        print(" -", c)

df = df_raw[cols_existentes].copy()


# 3) NORMALIZAR TEXTO


# Normalizamos todas las columnas que quedaron como texto
for col in df.columns:
    df[col] = df[col].apply(normalizar_texto)



# 4) SELECCIONAMOS  BOLIVAR

if COLUMNA_DEPTO in df.columns:
    df = df[df[COLUMNA_DEPTO] == DEPARTAMENTO_OBJETIVO].copy()
    print(f"Filas tras filtrar {DEPARTAMENTO_OBJETIVO}: {len(df):,}")
else:
    print(f"Advertencia: No existe {COLUMNA_DEPTO}, no se filtró por departamento.")


# 
# 5) CALCULAMOS EDAD

# Convertimos fecha nacimiento (DD/MM/YYYY)
if COL_FECHA_NAC in df.columns:
    df["FECHA_NAC_DT"] = pd.to_datetime(df[COL_FECHA_NAC], errors="coerce", dayfirst=True)
else:
    df["FECHA_NAC_DT"] = pd.NaT

# Fecha aproximada del examen desde PERIODO
if COL_PERIODO in df.columns:
    df["FECHA_EXAMEN_APROX"] = df[COL_PERIODO].apply(periodo_a_fecha_aprox)
else:
    df["FECHA_EXAMEN_APROX"] = pd.NaT

# Edad en años
df["EDAD"] = (df["FECHA_EXAMEN_APROX"] - df["FECHA_NAC_DT"]).dt.days / 365.25
df["EDAD"] = df["EDAD"].apply(lambda x: int(x) if pd.notna(x) else pd.NA)


# 6) LIMPIEZA DE PUNTAJES Y ABERRANTES


# Puntaje global a numérico y filtro 0 a 500 
if "PUNT_GLOBAL" in df.columns:
    df["PUNT_GLOBAL"] = pd.to_numeric(df["PUNT_GLOBAL"], errors="coerce")
    df = df[(df["PUNT_GLOBAL"].isna()) | ((df["PUNT_GLOBAL"] >= 0) & (df["PUNT_GLOBAL"] <= 500))].copy()

# Puntajes por prueba 
pruebas_0_100 = [
    "PUNT_INGLES",
    "PUNT_MATEMATICAS",
    "PUNT_LECTURA_CRITICA",
    "PUNT_C_NATURALES",
    "PUNT_SOCIALES_CIUDADANAS",
]
for col in pruebas_0_100:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df[(df[col].isna()) | ((df[col] >= 0) & (df[col] <= 100))].copy()


# 7) REPORTE GENERAL

reporte_faltantes(df, nombre="df_base_filtrado_bolivar")


# 8) CREACIÓN DATAFRAMES PARA ANÁLISIS

# ---- Pregunta 1 ----
cols_q1 = [c for c in Q1_COLS if c in df.columns] + ["EDAD"]
df_q1 = df[cols_q1].copy()

if "COLE_BILINGUE" in df_q1.columns:
    df_q1["COLE_BILINGUE"] = df_q1["COLE_BILINGUE"].replace({
        "SI": "S", "NO": "N"
    })

req_q1 = [c for c in Q1_COLS if c in df_q1.columns]
df_q1 = df_q1.dropna(subset=req_q1).copy()

print(f"\nDataframe pregunta 1 listo: df_q1 | filas: {len(df_q1):,} | columnas: {len(df_q1.columns)}")


# ---- Pregunta 2 ----
cols_q2 = [c for c in Q2_COLS if c in df.columns] + ["EDAD"]
df_q2 = df[cols_q2].copy()


req_q2 = [c for c in Q2_COLS if c in df_q2.columns]
df_q2 = df_q2.dropna(subset=req_q2).copy()

print(f"Dataframe pregunta 2 listo: df_q2 | filas: {len(df_q2):,} | columnas: {len(df_q2.columns)}")


# ---- Pregunta 3 ----
cols_q3 = [c for c in Q3_COLS if c in df.columns] + ["EDAD", "FAMI_ESTRATOVIVIENDA"]
cols_q3 = [c for c in cols_q3 if c in df.columns or c == "EDAD"]
df_q3 = df[cols_q3].copy()

req_q3 = [c for c in Q3_COLS if c in df_q3.columns]
df_q3 = df_q3.dropna(subset=req_q3).copy()

print(f"Dataframe pregunta 3 listo: df_q3 | filas: {len(df_q3):,} | columnas: {len(df_q3.columns)}")


# 9) ENCABEZADOS


print("\nVista rápida df_q1:")
print(df_q1.head())

print("\nVista rápida df_q2:")
print(df_q2.head())

print("\nVista rápida df_q3:")
print(df_q3.head())
