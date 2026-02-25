# src/helpers.py
import pandas as pd

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