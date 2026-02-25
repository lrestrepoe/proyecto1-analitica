# src/helpers.py
import pandas as pd
from typing import Optional, List, Dict
import plotly.express as px


BINARY_SINO = {"S": "Sí", "SI": "Sí", "N": "No", "NO": "No"}

def map_sino(series: pd.Series) -> pd.Series:
    """Convierte S/SI/N/NO a Sí/No (mantiene NaN si no mapea)."""
    return series.map(BINARY_SINO)

def mean_by(dff: pd.DataFrame, group_cols, value_col: str) -> pd.DataFrame:
    """Retorna dataframe con promedio y conteo por group_cols."""
    out = (
        dff.groupby(group_cols)[value_col]
        .agg(mean="mean", n="count", std="std")
        .reset_index()
    )
    return out

def delta_yes_no(
    dff: pd.DataFrame,
    group_col: str,
    yesno_col: str,
    value_col: str,
    yes_label="Sí",
    no_label="No",
) -> pd.DataFrame:
    """
    Calcula delta = promedio(Sí) - promedio(No) por group_col.
    Devuelve columnas: group_col, yes, no, delta
    """
    g = (
        dff.groupby([group_col, yesno_col])[value_col]
        .mean()
        .reset_index()
    )
    piv = g.pivot(index=group_col, columns=yesno_col, values=value_col).reset_index()

    if yes_label in piv.columns and no_label in piv.columns:
        piv["delta"] = piv[yes_label] - piv[no_label]
    else:
        piv["delta"] = pd.NA

    return piv

# src/helpers.py
import pandas as pd

def _clean_gender(dff: pd.DataFrame, genero_col="estu_genero") -> pd.DataFrame:
    """Deja solo M/F y normaliza."""
    dff = dff.copy()
    if genero_col not in dff.columns:
        return dff.iloc[0:0]
    dff[genero_col] = dff[genero_col].astype(str).str.strip().str.upper()
    dff = dff[dff[genero_col].isin(["M", "F"])]
    return dff

def apply_year_filter(dff: pd.DataFrame, anio_slider: int, ANIO_TODOS: int) -> pd.DataFrame:
    """Filtra por año si no es 'Todos'."""
    if anio_slider is None:
        return dff
    if int(anio_slider) == int(ANIO_TODOS):
        return dff
    if "anio" not in dff.columns:
        return dff.iloc[0:0]
    return dff[dff["anio"] == int(anio_slider)]

def brecha_genero_long(
    dff: pd.DataFrame,
    pruebas_sel: list,
    Q2_PUNTAJES: dict,
    group_col: str | None = None,
    genero_col: str = "estu_genero",
) -> pd.DataFrame:
    """
    Retorna DF en formato largo con:
      - si group_col=None: columnas [prueba, brecha_M_F]
      - si group_col!=None: columnas [group_col, prueba, brecha_M_F]
    prueba ya viene mapeada a labels bonitos usando Q2_PUNTAJES.
    """
    if dff.empty:
        return pd.DataFrame()

    dff = _clean_gender(dff, genero_col=genero_col)
    if dff.empty:
        return pd.DataFrame()

    # Validar pruebas que existan
    pruebas_sel = [p for p in (pruebas_sel or ["punt_global"]) if p in dff.columns]
    if not pruebas_sel:
        return pd.DataFrame()

    if group_col is None:
        proms = dff.groupby(genero_col)[pruebas_sel].mean()
        if ("M" not in proms.index) or ("F" not in proms.index):
            return pd.DataFrame()

        out = (proms.loc["M"] - proms.loc["F"]).reset_index()
        out.columns = ["prueba", "brecha_M_F"]
        out["prueba"] = out["prueba"].map(Q2_PUNTAJES).fillna(out["prueba"])
        return out

    # group_col != None
    if group_col not in dff.columns:
        return pd.DataFrame()

    proms = dff.groupby([group_col, genero_col])[pruebas_sel].mean().unstack(genero_col)

    brechas = {}
    for p in pruebas_sel:
        if (p, "M") in proms.columns and (p, "F") in proms.columns:
            brechas[p] = proms[(p, "M")] - proms[(p, "F")]

    if not brechas:
        return pd.DataFrame()

    out = (
        pd.DataFrame(brechas)
        .reset_index()
        .melt(id_vars=group_col, var_name="prueba", value_name="brecha_M_F")
        .dropna()
    )
    out["prueba"] = out["prueba"].map(Q2_PUNTAJES).fillna(out["prueba"])
    return out

def build_insight_maxmin(df_long: pd.DataFrame, group_col: str | None = None) -> str:
    """Texto insight: mayor y menor brecha."""
    if df_long is None or df_long.empty:
        return "No se pudo calcular la brecha con los filtros actuales."

    max_row = df_long.loc[df_long["brecha_M_F"].idxmax()]
    min_row = df_long.loc[df_long["brecha_M_F"].idxmin()]

    if group_col is None:
        return (
            f"La mayor brecha es '{max_row['prueba']}' con {max_row['brecha_M_F']:.2f} puntos. "
            f"La menor brecha es '{min_row['prueba']}' con {min_row['brecha_M_F']:.2f} puntos."
        )

    return (
        f"La mayor brecha es '{max_row[group_col]}' en '{max_row['prueba']}' con {max_row['brecha_M_F']:.2f} puntos. "
        f"La menor brecha es '{min_row[group_col]}' en '{min_row['prueba']}' con {min_row['brecha_M_F']:.2f} puntos."
    )

def build_dropdown_options(dff: pd.DataFrame, col: str, upper: bool = False) -> List[Dict[str, str]]:
    """Construye options para dropdown a partir de una columna (limpia espacios, opcional upper)."""
    if dff.empty or col not in dff.columns:
        return []
    s = dff[col].astype(str).str.strip()
    if upper:
        s = s.str.upper()
    vals = sorted(s.dropna().unique().tolist())
    return [{"label": v, "value": v} for v in vals]

def delta_yes_no(
    dff: pd.DataFrame,
    group_col: str,
    yesno_col: str,
    value_col: str,
    yes_label: str = "Sí",
    no_label: str = "No",
) -> pd.DataFrame:
    """
    Calcula delta = promedio(yes_label) - promedio(no_label) por group_col.
    Devuelve DF con columnas: group_col, Sí, No, delta (si existen).
    """
    if dff.empty:
        return pd.DataFrame()

    g = (
        dff.groupby([group_col, yesno_col])[value_col]
        .mean()
        .reset_index()
    )
    piv = g.pivot(index=group_col, columns=yesno_col, values=value_col).reset_index()

    if yes_label in piv.columns and no_label in piv.columns:
        piv["delta"] = piv[yes_label] - piv[no_label]
    else:
        piv["delta"] = pd.NA

    return piv

def fig_delta_bar(piv: pd.DataFrame, x_col: str, title: str, x_label: str) -> "px.Figure":
    """Figura estándar para delta."""
    if piv is None or piv.empty or "delta" not in piv.columns:
        return px.bar(title="No hay datos para graficar")

    fig = px.bar(
        piv,
        x=x_col,
        y="delta",
        text=piv["delta"].round(1),
        title=title,
        labels={x_col: x_label, "delta": "Diferencia (Sí - No)"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig

def order_estrato_like(piv: pd.DataFrame, col: str) -> pd.DataFrame:
    """Ordena estrato tipo 'ESTRATO 1..6' si aplica."""
    if piv is None or piv.empty or col not in piv.columns:
        return piv

    def _ord(x):
        s = str(x).upper()
        if "ESTRATO" in s:
            try:
                return int(s.split()[-1])
            except Exception:
                return 99
        return 100

    piv = piv.copy()
    piv["_orden"] = piv[col].apply(_ord)
    piv = piv.sort_values("_orden").drop(columns=["_orden"])
    return piv

def edu_to_num(x):
    """
    Convierte educación (texto) a escala 0..5.
    Ajusta patrones si tus categorías son distintas.
    """
    if x is None:
        return pd.NA

    s = str(x).strip().upper()

    if s == "" or "NO SABE" in s:
        return pd.NA

    if "NINGUNO" in s or "NO ESTUDIO" in s:
        return 0
    if "PRIMARIA" in s:
        return 1
    if "SECUNDARIA" in s or "BACHILLER" in s or "MEDIA" in s:
        return 2
    if "TECNIC" in s or "TECNOLOG" in s:
        return 3
    if "UNIVERS" in s or "PROFES" in s:
        return 4
    if "POSTGR" in s or "MAESTR" in s or "DOCTOR" in s or "ESPECIAL" in s:
        return 5

    return pd.NA


def edu_bucket(x):
    """Agrupa educación en categorías simplificadas."""
    n = edu_to_num(x)
    if pd.isna(n):
        return pd.NA

    n = int(n)

    if n <= 1:
        return "Baja"
    if n == 2:
        return "Media"
    if n == 3:
        return "Tecnica"
    return "Superior"


def build_q3_features(dff):
    """
    Crea:
        - edu_madre_n
        - edu_padre_n
        - capital_educativo
        - edu_madre_bucket
        - edu_padre_bucket
    """

    dff = dff.copy()

    madre_candidates = [
        "fami_educacionmadre",
        "edu_madre",
        "educ_madre"
    ]

    padre_candidates = [
        "fami_educacionpadre",
        "edu_padre",
        "educ_padre"
    ]

    col_m = next((c for c in madre_candidates if c in dff.columns), None)
    col_p = next((c for c in padre_candidates if c in dff.columns), None)

    if col_m is None or col_p is None:
        return dff, None, None

    dff["edu_madre_n"] = dff[col_m].apply(edu_to_num)
    dff["edu_padre_n"] = dff[col_p].apply(edu_to_num)

    dff["capital_educativo"] = dff[["edu_madre_n", "edu_padre_n"]].mean(axis=1)

    dff["edu_madre_bucket"] = dff[col_m].apply(edu_bucket)
    dff["edu_padre_bucket"] = dff[col_p].apply(edu_bucket)

    return dff, col_m, col_p


def brecha_alto_bajo_por(dff, by_col, thr_alto=4, thr_bajo=1):
    """
    Brecha = promedio(punt_global | capital>=thr_alto)
           - promedio(punt_global | capital<=thr_bajo)
    por categoría (by_col)
    """

    if by_col not in dff.columns:
        return pd.DataFrame()

    tmp = dff.dropna(
        subset=["capital_educativo", "punt_global", by_col]
    ).copy()

    if tmp.empty:
        return pd.DataFrame()

    tmp["grupo_capital"] = pd.NA
    tmp.loc[tmp["capital_educativo"] >= thr_alto, "grupo_capital"] = "ALTO"
    tmp.loc[tmp["capital_educativo"] <= thr_bajo, "grupo_capital"] = "BAJO"

    tmp = tmp.dropna(subset=["grupo_capital"])

    if tmp.empty:
        return pd.DataFrame()

    g = (
        tmp.groupby([by_col, "grupo_capital"])["punt_global"]
        .mean()
        .reset_index()
    )

    piv = g.pivot(index=by_col,
                  columns="grupo_capital",
                  values="punt_global").reset_index()

    if "ALTO" in piv.columns and "BAJO" in piv.columns:
        piv["brecha"] = piv["ALTO"] - piv["BAJO"]
    else:
        piv["brecha"] = pd.NA

    return piv

#Cosas para hacer en helpers.py:

#reduce líneas es sacar el bloque de geojson_norm fuera del callback del mapa (para no reconstruirlo en cada interacción). Te digo cómo dejarlo cacheado arriba (se nota en velocidad también).