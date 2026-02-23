from pathlib import Path
import dash
from dash import html
import pandas as pd

# Cargar el DataFrame global desde un archivo Parquet
BASE_DIR = Path(__file__).resolve().parent
# leer el parquet con pandas
df = pd.read_parquet(BASE_DIR / "data" / "df_global.parquet")
    
# crear app
app = dash.Dash(__name__)
server = app.server  # Se usa despues para aws

# layout base (texto e info)
app.layout = html.Div([
    html.H1("ICFES BOLÍVAR - MI DASH"),
    html.H2("Dashboard Saber 11 - Bolívar"),
    html.P(f"Filas: {len(df):,}"),
    html.P(f"Columnas: {len(df.columns)}"),
    html.P("Primeras 10 columnas:"),
    html.Ul([html.Li(c) for c in df.columns[:10]])
], style={"padding": "20px"})

print("ESTOY CORRIENDO app_icfes.py - VERSION ICFES")

if __name__ == "__main__":
    app.run(debug=True, port=8051)