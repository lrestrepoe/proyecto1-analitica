from pathlib import Path
import dash 
from dash import Input, Output, html, dcc
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
app.layout = html.Div(
    [
        dcc.Store(id="df_filtrado"),

        # Header
        html.Div(
            [
                html.H2("Resultados de la prueba Saber 11 en el departamento del Bolívar"),
                html.P("Análisis de resultados"),
            ],
            style={
                "padding": "12px 16px",
                "borderBottom": "1px solid #ddd",
                "backgroundColor": "#f9f9f9",
                "textAlign": "center",
            },
        ),

        # Contenedor centrado
        html.Div(
            [
                # Filtros
                html.Div(
                    [
                        html.Div([
                            html.Label("Año"),
                            dcc.Dropdown(id="f_anio", options=opciones("anio"), multi=True, placeholder="Todos"),
                        ], style={"flex": "1"}),

                        html.Div([
                            html.Label("Tipo colegio"),
                            dcc.Dropdown(id="f_naturaleza", options=opciones("cole_naturaleza"), multi=True, placeholder="Todos"),
                        ], style={"flex": "1"}),

                        html.Div([
                            html.Label("Estrato"),
                            dcc.Dropdown(id="f_estrato", options=opciones("fami_estratovivienda"), multi=True, placeholder="Todos"),
                        ], style={"flex": "1"}),

                    ],
                    style={
                        "display": "flex","gap": "12px","padding": "12px",
                        "border": "1px solid #eee","borderRadius": "12px",
                        "backgroundColor": "white","marginTop": "16px",
                    },
                ),

                # Resumen como
                html.Div(
                    [
                        html.H3("Resumen", style={"marginTop": "0px"}),
                        html.Div(id="resumen"),
                    ],
                    style={
                        "marginTop": "12px","padding": "12px","border": "1px solid #eee",
                        "borderRadius": "12px","backgroundColor": "white",
                    },
                ),

                # Q1
                html.Div(
                    [
                        html.H3("Relacion de colegio Bilingüe y puntaje global"),
                        dcc.Graph(id="grafico_q1"),
                        html.Div(id="insight_q1", style={"marginTop": "6px", "fontSize": "13px", "lineHeight": "1.4", "color": "#555"}),
                        dcc.Graph(id="grafico_q1_estrato"),
                        html.Div([dcc.Graph(id="grafico_q1_pc")], style={"flex": "1"}),
                        html.Div([dcc.Graph(id="grafico_q1_internet")], style={"flex": "1"}),
                        # luego aquí metemos pc / internet en el siguiente paso
                    ],
                    style={
                        "marginTop": "12px","padding": "12px","border": "1px solid #eee",
                        "borderRadius": "12px","backgroundColor": "white", "display": "flex", "flexDirection": "column", "gap": "12px"
                    },
                ),
            ],
            style={
                "maxWidth": "1100px",   # limita el ancho para mejor lectura
                "margin": "0 auto",     # centra
                "padding": "0 16px 40px 16px",
            },
        ),
    ]
)

# -----------
# Callbacks

# Callback para filtrar el DataFrame según los dropdowns
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

# Callbacks para actualizar resumen, gráficos e insights según el df filtrado
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
        dff.groupby("bilingue_label")["punt_global"]
        .agg(["mean", "count", "std"])
        .reset_index()
    )

    fig = px.bar(
        resumen,
        x="bilingue_label",
        y="mean",
        text=resumen["mean"].round(0),
        title="Promedio de puntaje global por tipo de colegio bilingüe",
        labels={"bilingue_label": "Colegio bilingüe", "mean": "Promedio puntaje global"},
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

# Grafico diferencia en puntaje global entre colegios bilingües y no bilingües dentro de cada estrato
@app.callback(
    Output("grafico_q1_estrato", "figure"),
    Input("df_filtrado", "data")
)
def q1_delta_por_estrato(data):
    dff = pd.DataFrame(data)

    if dff.empty:
        return px.bar(title="No hay datos con esos filtros")

    req = {"cole_bilingue", "fami_estratovivienda", "punt_global"}
    if not req.issubset(set(dff.columns)):
        return px.bar(title="Faltan columnas para calcular diferencia por estrato")

    # Etiquetas Sí/No
    dff["bilingue_label"] = dff["cole_bilingue"].map({
        "S": "Sí", "SI": "Sí",
        "N": "No", "NO": "No"
    })

    # Promedio por estrato y bilingüe
    g = (
        dff.groupby(["fami_estratovivienda", "bilingue_label"])["punt_global"]
        .mean()
        .reset_index()
    )

    # Pasar a formato ancho: columnas Sí/No
    piv = g.pivot(index="fami_estratovivienda", columns="bilingue_label", values="punt_global").reset_index()

    # Si falta alguna columna, no se puede calcular delta en ese estrato
    if "Sí" not in piv.columns or "No" not in piv.columns:
        return px.bar(title="Con los filtros actuales no hay comparación Sí vs No por estrato")

    piv["delta"] = piv["Sí"] - piv["No"]

    # Orden bonito de estratos
    def orden_estrato(x):
        s = str(x)
        if "ESTRATO" in s:
            try:
                return int(s.split()[-1])
            except:
                return 99
        return 100

    piv["orden"] = piv["fami_estratovivienda"].apply(orden_estrato)
    piv = piv.sort_values("orden")

    fig = px.bar(
        piv,
        x="fami_estratovivienda",
        y="delta",
        text=piv["delta"].round(1),
        title="Diferencia de promedio en puntaje global si el colegio es bilingue dentro de cada estrato",
        labels={"fami_estratovivienda": "Estrato", "delta": "Diferencia Puntaje global "}
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))

    return fig

# Grafico diferencia en puntaje global entre colegios bilingües y no bilingües dentro de si tienen computador o no
@app.callback(
    Output("grafico_q1_pc", "figure"),
    Input("df_filtrado", "data")
)
def q1_delta_pc(data):
    dff = pd.DataFrame(data)
    if dff.empty:
        return px.bar(title="No hay datos")

    req = {"cole_bilingue", "fami_tienecomputador", "punt_global"}
    if not req.issubset(dff.columns):
        return px.bar(title="Faltan columnas (computador / bilingüe / puntaje)")

    dff["bilingue_label"] = dff["cole_bilingue"].map({"S": "Sí", "SI": "Sí", "N": "No", "NO": "No"})

    g = (
        dff.groupby(["fami_tienecomputador", "bilingue_label"])["punt_global"]
        .mean()
        .reset_index()
    )
    piv = g.pivot(index="fami_tienecomputador", columns="bilingue_label", values="punt_global").reset_index()

    if "Sí" not in piv.columns or "No" not in piv.columns:
        return px.bar(title="No hay comparación suficiente Sí vs No")

    piv["delta"] = piv["Sí"] - piv["No"]

    fig = px.bar(
        piv,
        x="fami_tienecomputador",
        y="delta",
        text=piv["delta"].round(1),
        title="Diferencia de puntaje global según computador",
        labels={"fami_tienecomputador": "Tiene computador", "delta": "Diferencia puntaje global"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig

# Grafico diferencia en puntaje global entre colegios bilingües y no bilingües dentro de si tienen internet o no
@app.callback(
    Output("grafico_q1_internet", "figure"),
    Input("df_filtrado", "data")
)
def q1_delta_internet(data):
    dff = pd.DataFrame(data)
    if dff.empty:
        return px.bar(title="No hay datos")

    req = {"cole_bilingue", "fami_tieneinternet", "punt_global"}
    if not req.issubset(dff.columns):
        return px.bar(title="Faltan columnas (internet / bilingüe / puntaje)")

    dff["bilingue_label"] = dff["cole_bilingue"].map({"S": "Sí", "SI": "Sí", "N": "No", "NO": "No"})

    g = (
        dff.groupby(["fami_tieneinternet", "bilingue_label"])["punt_global"]
        .mean()
        .reset_index()
    )
    piv = g.pivot(index="fami_tieneinternet", columns="bilingue_label", values="punt_global").reset_index()

    if "Sí" not in piv.columns or "No" not in piv.columns:
        return px.bar(title="No hay comparación suficiente Sí vs No")

    piv["delta"] = piv["Sí"] - piv["No"]

    fig = px.bar(
        piv,
        x="fami_tieneinternet",
        y="delta",
        text=piv["delta"].round(1),
        title="Diferencia de puntaje global según internet",
        labels={"fami_tieneinternet": "Tiene internet", "delta": "Diferencia puntaje global"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig

if __name__ == "__main__":
    app.run(debug=True, port=8051)

