from pathlib import Path
import dash 
from dash import Input, Input, Output, html, dcc
import pandas as pd

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
                        html.P("Aquí van las pestañas Home / Q1 / Q2 / Q3."),
                        html.Ul(
                            [
                                html.Li("Q1: Bilingüe vs puntaje global"),
                                html.Li("Q2: Brecha por género"),
                                html.Li("Q3: Educación padres y compensación"),
                            ]
                        ),
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


if __name__ == "__main__":
    app.run(debug=True, port=8051)

