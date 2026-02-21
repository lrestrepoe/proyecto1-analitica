import pandas as pd
from pathlib import Path
import unicodedata

CARPETA_DATOS = r"C:\Users\dburg\Desktop\ActProy1"
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

Q3_COLS = [
    "fami_educacionmadre",
    "fami_educacionpadre",
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

def imprimir_reporte_faltantes(df, nombre):
    rep = pd.DataFrame({
        "columna": df.columns,
        "nulos": [df[c].isna().sum() for c in df.columns],
        "porcentaje_nulos": [round(df[c].isna().mean() * 100, 2) for c in df.columns],
    }).sort_values("porcentaje_nulos", ascending=False)
    print(f"\nREPORTE DE FALTANTES -> {nombre}")
    print(rep.to_string(index=False))
    return rep

def verificar_sin_nulos_y_conteo(df, nombre):
    n = len(df)
    conteos = df.count()
    min_c = int(conteos.min()) if len(conteos) else 0
    max_c = int(conteos.max()) if len(conteos) else 0
    nulos_total = int(df.isna().sum().sum())
    print(f"\nVERIFICACION -> {nombre}")
    print(f"Filas: {n:,} | Nulos totales: {nulos_total:,} | Non-null min: {min_c:,} | Non-null max: {max_c:,}")
    if nulos_total == 0 and min_c == n and max_c == n:
        print("OK")
    else:
        print("ALERTA")

ruta = Path(CARPETA_DATOS)
archivo = ruta / NOMBRE_ARCHIVO
if not archivo.exists() and not NOMBRE_ARCHIVO.lower().endswith(".csv"):
    archivo = ruta / f"{NOMBRE_ARCHIVO}.csv"
if not archivo.exists():
    raise FileNotFoundError(f"No encontré el archivo en: {archivo}")

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
    print("\nOJO: columnas esperadas que no existen en el CSV:")
    for c in cols_faltantes:
        print(" -", c)

df = df_raw[cols_existentes].copy()

df = df.replace({
    "": pd.NA, " ": pd.NA,
    "NA": pd.NA, "N/A": pd.NA,
    "NULL": pd.NA, "NONE": pd.NA,
    "NAN": pd.NA
})

categ_cols = set([
    "cole_bilingue",
    "cole_area_ubicacion",
    "cole_naturaleza",
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

if "cole_bilingue" in df.columns:
    df["cole_bilingue"] = df["cole_bilingue"].replace({"SI": "S", "NO": "N"})

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
    print("\nPERIODOS DONDE punt_global ESTÁ VACÍO (top 20 por % de vacíos)")
    print(resumen_periodo.head(20).to_string(index=False))

antes = len(df)
df = df[df["periodo_int"].notna() & (df["periodo_int"] >= PERIODO_MINIMO)].copy()
print(f"\nFilas después de filtrar periodo >= {PERIODO_MINIMO}: {len(df):,} (antes: {antes:,})")

antes = len(df)
df = df.dropna(subset=[COL_PUNT_GLOBAL]).copy()
print(f"Filas después de eliminar punt_global vacío: {len(df):,} (antes: {antes:,})")

antes = len(df)
df = df[(df[COL_PUNT_GLOBAL] >= 0) & (df[COL_PUNT_GLOBAL] <= 500)].copy()
print(f"Filas después de eliminar punt_global aberrante: {len(df):,} (antes: {antes:,})")

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

if COL_ID in df.columns:
    dup_exact = df.duplicated().sum()
    print(f"\nDuplicados exactos (fila idéntica): {dup_exact:,}")
    df = df.drop_duplicates(keep="first").copy()

    filas_repetidas_id = df[COL_ID].duplicated(keep=False).sum()
    print(f"Filas que pertenecen a IDs repetidos (mismo {COL_ID}) tras quitar exactos: {filas_repetidas_id:,}")

    if filas_repetidas_id > 0:
        df = df.sort_values(by=[COL_ID, COL_PUNT_GLOBAL], ascending=[True, False]).copy()
        antes = len(df)
        df = df.drop_duplicates(subset=[COL_ID], keep="first").copy()
        print(f"Filas después de quedarnos con el mayor punt_global por {COL_ID}: {len(df):,} (antes: {antes:,})")

if COL_FECHA_NAC in df.columns:
    df["fecha_nac_dt"] = pd.to_datetime(df[COL_FECHA_NAC], errors="coerce", dayfirst=True)
else:
    df["fecha_nac_dt"] = pd.NaT

df["fecha_examen_aprox"] = df[COL_PERIODO].apply(periodo_a_fecha_aprox)

df["edad"] = (df["fecha_examen_aprox"] - df["fecha_nac_dt"]).dt.days / 365.25
df["edad"] = df["edad"].apply(lambda x: int(x) if pd.notna(x) else pd.NA)

imprimir_reporte_faltantes(df, "df_base_antes_casos_completos")

cols_estudio = list(dict.fromkeys(
    [COL_ID, "edad", COL_COLE_NATURALEZA] + Q1_COLS + Q2_COLS + Q3_COLS
))
cols_estudio = [c for c in cols_estudio if c in df.columns]

antes = len(df)
df_estudio = df.dropna(subset=cols_estudio).copy()
print(f"\nFilas después de eliminar TODOS los nulos del estudio: {len(df_estudio):,} (antes: {antes:,})")

cols_global_final = [c for c in GLOBAL_COLS if c in df_estudio.columns] + ["edad"]
cols_global_final = list(dict.fromkeys(cols_global_final))
df_global = df_estudio[cols_global_final].copy()

cols_q1_final = list(dict.fromkeys([COL_ID, "edad", COL_COLE_NATURALEZA] + Q1_COLS))
cols_q1_final = [c for c in cols_q1_final if c in df_estudio.columns]
df_q1 = df_estudio[cols_q1_final].copy()

cols_q2_final = list(dict.fromkeys([COL_ID, "edad", COL_COLE_NATURALEZA] + Q2_COLS))
cols_q2_final = [c for c in cols_q2_final if c in df_estudio.columns]
df_q2 = df_estudio[cols_q2_final].copy()

cols_q3_final = list(dict.fromkeys([COL_ID, "edad", COL_COLE_NATURALEZA] + Q3_COLS))
cols_q3_final = [c for c in cols_q3_final if c in df_estudio.columns]
df_q3 = df_estudio[cols_q3_final].copy()

orden_estudiante = [
    "estu_consecutivo",
    "periodo",
    "estu_fechanacimiento",
    "edad",
    "estu_genero",
]

orden_colegio = [
    "cole_area_ubicacion",
    "cole_bilingue",
    "cole_naturaleza",
    "cole_genero",
    "cole_caracter",
]

orden_familia = [
    "fami_estratovivienda",
    "fami_tienecomputador",
    "fami_tieneinternet",
    "fami_educacionmadre",
    "fami_educacionpadre",
]

orden_puntajes = [
    "punt_ingles",
    "punt_matematicas",
    "punt_lectura_critica",
    "punt_c_naturales",
    "punt_sociales_ciudadanas",
    "punt_global",
]

ordenadas = orden_estudiante + orden_colegio + orden_familia + orden_puntajes

def reordenar_columnas(df):
    cols_base = [c for c in ordenadas if c in df.columns]
    cols_restantes = [c for c in df.columns if c not in cols_base]
    return df[cols_base + cols_restantes]

df_global = reordenar_columnas(df_global)
df_q1 = reordenar_columnas(df_q1)
df_q2 = reordenar_columnas(df_q2)
df_q3 = reordenar_columnas(df_q3)

verificar_sin_nulos_y_conteo(df_global, "df_global")
verificar_sin_nulos_y_conteo(df_q1, "df_q1")
verificar_sin_nulos_y_conteo(df_q2, "df_q2")
verificar_sin_nulos_y_conteo(df_q3, "df_q3")

print("\nPrimeras filas df_global:")
print(df_global.head())