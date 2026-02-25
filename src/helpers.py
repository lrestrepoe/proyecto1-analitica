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