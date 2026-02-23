from pathlib import Path
import dash 
from dash import html, dcc
import pandas as pd

# Cargar el DataFrame global desde un archivo Parquet
BASE_DIR = Path(__file__).resolve().parent
# leer el parquet con pandas
df = pd.read_parquet(BASE_DIR / "data" / "df_global.parquet")
    
# crear app
app = dash.Dash(__name__)
server = app.server  # Se usa despues para aws

# layout base (texto e info)
app.layout = html.Div(
    [
        # Header arriba
        html.Div(
            [
                html.H2("ICFES Bolívar – Tablero"),
                html.Div("Filtros a la izquierda, visualizaciones a la derecha."),
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
                        html.Label("Año (por ahora no funciona, es solo UI)"),
                        dcc.Dropdown(
                            options=[{"label": "2019", "value": 2019}, {"label": "2020", "value": 2020}],
                            multi=True,
                            placeholder="Selecciona año(s)",
                        ),
                        html.Label("Tipo de colegio"),
                        dcc.Dropdown(
                            options=[
                                {"label": "OFICIAL", "value": "OFICIAL"},
                                {"label": "NO OFICIAL", "value": "NO OFICIAL"},
                            ],
                            multi=True,
                            placeholder="Selecciona tipo",
                        ),
                        html.Br(),
                        html.Button("Restablecer", n_clicks=0),
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
                        html.H3("Contenido"),
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

if __name__ == "__main__":
    app.run(debug=True, port=8051)