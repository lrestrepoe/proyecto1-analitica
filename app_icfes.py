from pathlib import Path
import dash 
from dash import Input, Input, Output, html, dcc
import pandas as pd
import plotly.express as px

# Cargar el DataFrame global desde un archivo Parquet
BASE_DIR = Path(__file__).resolve().parent

# leer el parquet con pandas
df = pd.read_parquet(BASE_DIR / "data" / "df_global.parquet")

# Dropdowns con valores del dataset (para esto se necesita el df global, asi que lo dejo despues de cargar el parquet)
def opciones(col):
    if col not in df.columns:
        return []
    vals = df[col].dropna().unique().tolist()
    # ordena, y si hay mezcla de tipos, convierte a string
    try:
        vals = sorted(vals)
    except Exception:
        vals = sorted([str(v) for v in vals])
    return [{"label": str(v), "value": v} for v in vals]

# se asegura de que se tiene el año creado
df["anio"] = (pd.to_numeric(df["periodo"], errors="coerce") // 10).astype("Int64")

# crear app
app = dash.Dash(__name__)
server = app.server  # Se usa despues para aws

# layout base (texto e info)
app.layout = html.Div([
    dcc.Store(id="df_filtrado"),
    
        # Header arriba
        html.Div(
            [
                html.H2("ICFES Bolívar – Tablero"),
                html.P("Análisis de resultados del examen Saber 11 en el departamento de Bolívar."),
            ],
            style={"padding": "12px 16px", "borderBottom": "1px solid #ddd"},
        ),

        # Cuerpo: sidebar + contenido
        html.Div(
            [
                # Sidebar
                html.Div(
                    [
                        html.H4("Filtros"),
                        html.Label("Año"),
                        dcc.Dropdown(
                            id="f_anio",
                            options=opciones("anio"),
                            multi=True,
                            placeholder="Selecciona año(s)",
                        ),
                        html.Label("Tipo de colegio"),
                        dcc.Dropdown(
                            id="f_naturaleza",
                            options=opciones("cole_naturaleza"),
                            multi=True,
                            placeholder="Selecciona tipo de colegio",
                        ),
                        html.Label("Estrato"),
                        dcc.Dropdown(
                            id="f_estrato",
                            options=opciones("fami_estratovivienda"),
                            multi=True,
                            placeholder="Selecciona estrato(s)",
),

                    ],
                    style={
                        "width": "25%",
                        "padding": "16px",
                        "borderRight": "1px solid #ddd",
                        "minHeight": "80vh",
                    },
                ),

                # Contenido principal
                html.Div(
                    [
                        html.H3("Resumen"),
                        html.Div(id="resumen"),

                        html.H3("Puntaje global por colegio bilingüe"),
                        dcc.Graph(id="grafico_q1"),
                        html.Div(id="insight_q1", style={"marginTop": "8px", "fontSize": "16px"}),
                        html.P("Aquí van las pestañas Home / Q1 / Q2 / Q3."),
                    ],
                    style={"width": "75%", "padding": "16px"},
                ),
            ],
            style={"display": "flex"},
        ),
    ]
)

@app.callback(
    Output("df_filtrado", "data"),
    Input("f_anio", "value"),
    Input("f_naturaleza", "value"),
    Input("f_estrato", "value"),
)
def filtrar_df(anios, naturalezas, estratos):
    dff = df.copy()

    if anios:
        dff = dff[dff["anio"].isin(anios)]
    if naturalezas:
        dff = dff[dff["cole_naturaleza"].isin(naturalezas)]
    if estratos:
        dff = dff[dff["fami_estratovivienda"].isin(estratos)]

    return dff.to_dict("records")

@app.callback(
    Output("resumen", "children"),
    Input("df_filtrado", "data")
)
def mostrar_resumen(data):
    dff = pd.DataFrame(data)
    if dff.empty:
        return "No hay datos"

    return f"Filas: {len(dff):,} | Promedio: {dff['punt_global'].mean():.2f}"

#Grafico Q1: puntaje global por colegio bilingüe
@app.callback(
    Output("grafico_q1", "figure"),
    Input("df_filtrado", "data")
)
def actualizar_q1(data):
    dff = pd.DataFrame(data)

    if dff.empty:
        return px.bar(title="No hay datos")

    if "cole_bilingue" not in dff.columns:
        return px.bar(title="No existe columna cole_bilingue")

    dff["bilingue_label"] = dff["cole_bilingue"].map({
        "S": "Sí",
        "N": "No",
        "SI": "Sí",
        "NO": "No"
    })
    # Agrupar por bilingüe
    resumen = (
        dff.groupby("cole_bilingue")["punt_global"]
        .agg(["mean", "count", "std"])
        .reset_index()
    )

    resumen["mean"] = resumen["mean"].round(2)

    fig = px.bar(
        resumen,
        x="cole_bilingue",
        y="mean",
        text="mean",
        title="Promedio de puntaje global por tipo de colegio bilingüe",
        labels={"cole_bilingue": "Colegio bilingüe", "mean": "Promedio puntaje global"},
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis_range=[0, 500])

    return fig

# Insight Q1: diferencia en puntaje global entre colegios bilingües y no bilingües
@app.callback(
    Output("insight_q1", "children"),
    Input("df_filtrado", "data")
)
def insight_q1(data):
    dff = pd.DataFrame(data)
    if dff.empty or "cole_bilingue" not in dff.columns or "punt_global" not in dff.columns:
        return "No hay suficiente información para calcular la diferencia."

    # Etiquetas Sí/No
    dff["bilingue_label"] = dff["cole_bilingue"].map({
        "S": "Sí",
        "N": "No",
        "SI": "Sí",
        "NO": "No"
    })

    # Promedios
    prom = dff.groupby("bilingue_label")["punt_global"].mean()

    if ("Sí" not in prom.index) or ("No" not in prom.index):
        return "Con los filtros actuales no hay datos para comparar 'Sí' vs 'No'."

    diff = prom["Sí"] - prom["No"]

    # Conteos
    n_si = (dff["bilingue_label"] == "Sí").sum()
    n_no = (dff["bilingue_label"] == "No").sum()

    signo = "más" if diff >= 0 else "menos"
    return (
        f"Los estudiantes de colegios bilingües obtienen en promedio "
        f"{abs(diff):.1f} puntos {signo} en puntaje global que los de colegios no bilingües "
        f"(Sí: n={n_si:,} | No: n={n_no:,})."
    )

if __name__ == "__main__":
    app.run(debug=True, port=8051)

