import json
from pathlib import Path
import dash
from dash import Input, Output, html, dcc
import pandas as pd
import plotly.express as px
import unicodedata
from src.helpers import map_sino, mean_by, apply_year_filter, brecha_genero_long, build_insight_maxmin



# Cargar el DataFrame global desde un archivo Parquet
BASE_DIR = Path(__file__).resolve().parent

# leer el parquet con pandas
df = pd.read_parquet(BASE_DIR / "data" / "df_global.parquet")

#  Cargar GeoJSON mapa y que se ajuste a los datos
GEOJSON_PATH = BASE_DIR / "data" / "mpios.json"  # <-- cambia al nombre real
with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
    geojson_mcpios = json.load(f)

geojson_mcpios = {
    "type": "FeatureCollection",
    "features": [
        f for f in geojson_mcpios["features"]
        if f["properties"]["dpt"] == "BOLIVAR"
    ]
}

# --- DF base para pintar (usa el id de cada feature) ---
rows = []
for feat in geojson_mcpios.get("features", []):
    rows.append({
        "id": str(feat.get("id")),  # IMPORTANTÍSIMO: debe coincidir con featureidkey
        "name": feat.get("properties", {}).get("name", ""),
        "z": 1
    })
df_map_base = pd.DataFrame(rows)

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

# Columnas de puntajes que queremos permitir seleccionar en el dropdown
Q2_PUNTAJES = {
    "punt_global": "Global",
    "punt_matematicas": "Matemáticas",
    "punt_lectura_critica": "Lectura Crítica",
    "punt_c_naturales": "C. Naturales",
    "punt_sociales_ciudadanas": "Sociales",
    "punt_ingles": "Inglés",
}

# Lista de años disponibles para construir el slider
anios_disponibles = sorted(df["anio"].dropna().unique().tolist())

# Creamos un valor "extra" para el slider que represente "Todos los años"
# El slider necesita valores numéricos, entonces usamos max+1
ANIO_TODOS = int(max(anios_disponibles)) + 1 if len(anios_disponibles) > 0 else 9999

# Marks del slider: cada año aparece como etiqueta y el último es "Todos"
marks_anio = {int(a): str(int(a)) for a in anios_disponibles}
marks_anio[ANIO_TODOS] = "Todos"

# crear app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

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
                dcc.Tabs(
                    id="tabs",
                    value="tab-q1",
                    children=[
                        dcc.Tab(label="Pregunta 1: Bilingüe", value="tab-q1"),
                        dcc.Tab(label="Pregunta 2: Género", value="tab-q2"),
                        dcc.Tab(label="Pregunta 3: Educación padres", value="tab-q3"),
                    ],
                ),
                html.Div(id="contenido_tabs", style={"marginTop": "12px"}),
            ],
            style={
                "maxWidth": "1500px",   # limita el ancho para mejor lectura
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

@app.callback(
    Output("contenido_tabs", "children"),
    Input("tabs", "value")
)

# función para renderizar el contenido de cada pestaña
def render_tab(tab):
    if tab == "tab-q1":
        return html.Div(
            [
                html.Div(
                    [
                        html.H3("Relación de colegio bilingüe y puntaje global"),
                        dcc.Graph(id="grafico_q1"),
                        html.Div(
                            id="insight_q1",
                            style={"marginTop": "6px", "fontSize": "13px", "lineHeight": "1.4", "color": "#555"},
                        ),
                        html.H4("Mapa (municipios)"),
                        dcc.Graph(id="mapa_q1_bilingue_delta"),

                        # 2 por fila
                        html.Div(
                            [
                                html.Div([dcc.Graph(id="grafico_q1_estrato")], style={"flex": "1"}),
                            ],
                            style={"display": "flex", "gap": "12px", "marginTop": "10px"},
                        ),

                        html.Div(
                            [
                                html.Div([dcc.Graph(id="grafico_q1_internet")], style={"flex": "1"}),
                                html.Div([dcc.Graph(id="grafico_q1_pc")], style={"flex": "1"}),
                            ],
                            style={"display": "flex", "gap": "12px", "marginTop": "10px"},
                        ),
                    ],
                    style={
                        "padding": "12px",
                        "border": "1px solid #eee",
                        "borderRadius": "12px",
                        "backgroundColor": "white",
                    },
                )
            ]
        )

    if tab == "tab-q2":
        return html.Div(
            [
                html.Div(
                    [
                        html.H3("Diferencia de desempeño entre mujeres y hombres"),
                        html.P(
                            "La diferencia se calcula como (Masculino - Femenino). "
                            
                        ),

                       
                        # GRÁFICA 1: BRECHA POR PRUEBA
                        
                        html.H4("Diferencia por prueba (Saber 11)"),

                        html.Div(
                            [
                                # Slider independiente para la gráfica 1
                                html.Div(
                                    [
                                        html.Label("Año"),
                                        dcc.Slider(
                                            id="q2_year_slider_prueba",
                                            min=int(min(anios_disponibles)) if len(anios_disponibles) > 0 else 0,
                                            max=ANIO_TODOS,
                                            value=ANIO_TODOS,
                                            marks=marks_anio,
                                            step=None,
                                        ),
                                    ],
                                    style={"flex": "1"},
                                ),
                                # Dropdown multi de pruebas para gráfica 1
                                html.Div(
                                    [
                                        html.Label("Pruebas a mostrar"),
                                        dcc.Dropdown(
                                            id="q2_pruebas",
                                            options=[{"label": v, "value": k} for k, v in Q2_PUNTAJES.items()],
                                            value=["punt_global"],
                                            multi=True,
                                            placeholder="Seleccione una o varias pruebas",
                                        ),
                                    ],
                                    style={"flex": "1"},
                                ),
                            ],
                            style={"display": "flex", "gap": "12px", "marginTop": "10px"},
                        ),

                        dcc.Graph(id="grafico_q2_brecha_pruebas"),

                        html.Div(
                            id="insight_q2_pruebas",
                            style={"marginTop": "6px", "fontSize": "13px", "lineHeight": "1.4", "color": "#555"},
                        ),

                        html.Hr(),

                        #Grafica 2
                        html.H4("Diferencia por tipo de colegio"),

                        html.Div(
                            [
                                # Slider independiente para la gráfica 2
                                html.Div(
                                    [
                                        html.Label("Año"),
                                        dcc.Slider(
                                            id="q2_year_slider_cole",
                                            min=int(min(anios_disponibles)) if len(anios_disponibles) > 0 else 0,
                                            max=ANIO_TODOS,
                                            value=ANIO_TODOS,
                                            marks=marks_anio,
                                            step=None,
                                        ),
                                    ],
                                    style={"flex": "1"},
                                ),

                                # Dropdown multi de pruebas para gráfica 2
                                html.Div(
                                    [
                                        html.Label("Pruebas a mostrar"),
                                        dcc.Dropdown(
                                            id="q2_pruebas_cole",
                                            options=[{"label": v, "value": k} for k, v in Q2_PUNTAJES.items()],
                                            value=["punt_global"],
                                            multi=True,
                                            placeholder="Seleccione una o varias pruebas",
                                        ),
                                    ],
                                    style={"flex": "1"},
                                ),

                                # Dropdown multi para filtrar tipos de colegio
                                
                                html.Div(
                                    [
                                        html.Label("Filtrar tipo de colegio"),
                                        dcc.Dropdown(
                                            id="q2_cole_filtro",
                                            options=[],          # se llena dinámicamente
                                            value=[],            # vacío = sin filtro (todos)
                                            multi=True,
                                            placeholder="Seleccione uno o varios tipos",
                                        ),
                                    ],
                                    style={"flex": "1"},
                                ),
                            ],
                            style={"display": "flex", "gap": "12px", "marginTop": "10px"},
                        ),

                        dcc.Graph(id="grafico_q2_brecha_colegio"),

                        html.Div(
                            id="insight_q2_colegio",
                            style={"marginTop": "6px", "fontSize": "13px", "lineHeight": "1.4", "color": "#555"},
                        ),

                        # BRECHA POR ESTRATO
                        
                        html.Hr(),

                        html.H4("Diferencia por estrato del hogar"),

                        html.Div(
                            [
                                # Slider independiente para la gráfica 3
                                html.Div(
                                    [
                                        html.Label("Año"),
                                        dcc.Slider(
                                            id="q2_year_slider_estrato",
                                            min=int(min(anios_disponibles)) if len(anios_disponibles) > 0 else 0,
                                            max=ANIO_TODOS,
                                            value=ANIO_TODOS,  # por defecto: Todos
                                            marks=marks_anio,
                                            step=None,
                                        ),
                                    ],
                                    style={"flex": "1"},
                                ),

                                # Dropdown multi de pruebas para gráfica 3
                                html.Div(
                                    [
                                        html.Label("Pruebas a mostrar"),
                                        dcc.Dropdown(
                                            id="q2_pruebas_estrato",
                                            options=[{"label": v, "value": k} for k, v in Q2_PUNTAJES.items()],
                                            value=["punt_global"],  # por defecto: Global
                                            multi=True,
                                            placeholder="Seleccione una o varias pruebas",
                                        ),
                                    ],
                                    style={"flex": "1"},
                                ),

                                # Dropdown multi para filtrar estratos (se llena dinámicamente)
                                html.Div(
                                    [
                                        html.Label("Filtrar estrato"),
                                        dcc.Dropdown(
                                            id="q2_estrato_filtro",
                                            options=[],   # se llena con callback
                                            value=[],     # vacío = sin filtro (todos)
                                            multi=True,
                                            placeholder="Seleccione uno o varios estratos",
                                        ),
                                    ],
                                    style={"flex": "1"},
                                ),
                            ],
                            style={"display": "flex", "gap": "12px", "marginTop": "10px"},
                        ),

                        dcc.Graph(id="grafico_q2_brecha_estrato"),

                        html.Div(
                            id="insight_q2_estrato",
                            style={"marginTop": "6px", "fontSize": "13px", "lineHeight": "1.4", "color": "#555"},
                        ),
                        html.H4("Distribución porcentual por género"),

                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Label("Año"),
                                        dcc.Slider(
                                            id="q2_year_slider_genero",
                                            min=int(min(anios_disponibles)) if len(anios_disponibles) > 0 else 0,
                                            max=ANIO_TODOS,
                                            value=ANIO_TODOS,
                                            marks=marks_anio,
                                            step=None,
                                        ),
                                    ],
                                    style={"flex": "1"},
                                ),
                            ],
                            style={"display": "flex", "gap": "12px", "marginTop": "10px"},
                        ),

                        dcc.Graph(id="grafico_q2_dist_genero"),

                        html.Div(
                            id="insight_q2_genero",
                            style={"marginTop": "6px", "fontSize": "13px", "lineHeight": "1.4", "color": "#555"},
                        ),

                        html.Hr(),

                    ],
                    style={
                        "padding": "12px",
                        "border": "1px solid #eee",
                        "borderRadius": "12px",
                        "backgroundColor": "white",
                    },
                )
            ]
        )

    if tab == "tab-q3":
        return html.Div(
            [
                html.Div(
                    [
                        html.H3("Q3: Educación padres y puntaje global"),
                        html.P("Aquí vamos a construir la relación y dónde se debilita (compensación del colegio)."),
                    ],
                    style={
                        "padding": "12px",
                        "border": "1px solid #eee",
                        "borderRadius": "12px",
                        "backgroundColor": "white",
                    },
                )
            ]
        )

    return html.Div("Selecciona una pestaña.")

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
    if dff.empty or "cole_bilingue" not in dff.columns:
        return px.bar(title="No hay datos")

    dff["bilingue_label"] = map_sino(dff["cole_bilingue"])
    dff = dff.dropna(subset=["bilingue_label", "punt_global"])

    resumen = mean_by(dff, "bilingue_label", "punt_global")

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
    if dff.empty or not {"cole_bilingue", "punt_global"}.issubset(dff.columns):
        return "No hay suficiente información para calcular la diferencia."

    dff["bilingue_label"] = map_sino(dff["cole_bilingue"])
    dff = dff.dropna(subset=["bilingue_label", "punt_global"])

    prom = dff.groupby("bilingue_label")["punt_global"].mean()
    if ("Sí" not in prom.index) or ("No" not in prom.index):
        return "Con los filtros actuales no hay datos para comparar 'Sí' vs 'No'."

    diff = prom["Sí"] - prom["No"]
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

    dff["bilingue_label"] = map_sino(dff["cole_bilingue"])
    
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

#Callback Q2

# Gráfica 1: Brecha (M - F) por prueba y año
@app.callback(
    Output("grafico_q2_brecha_pruebas", "figure"),
    Output("insight_q2_pruebas", "children"),
    Input("df_filtrado", "data"),
    Input("q2_year_slider_prueba", "value"),
    Input("q2_pruebas", "value"),
)
def actualizar_q2_brecha_por_prueba(data, anio_slider, pruebas_sel):
    dff = pd.DataFrame(data)
    if dff.empty:
        return px.bar(title="Sin datos"), "No hay datos para mostrar con los filtros actuales."

    dff = apply_year_filter(dff, anio_slider, ANIO_TODOS)
    titulo_anio = "todos los años" if int(anio_slider) == int(ANIO_TODOS) else f"el año {int(anio_slider)}"
    if dff.empty:
        return px.bar(title="Sin datos"), f"No hay datos para {titulo_anio} con los filtros actuales."

    brecha = brecha_genero_long(dff, pruebas_sel, Q2_PUNTAJES, group_col=None)
    if brecha.empty:
        return px.bar(title="No se pudo calcular brecha"), "No se encuentran ambos géneros (M y F) o pruebas válidas."

    fig = px.bar(
        brecha, x="prueba", y="brecha_M_F",
        title=f"Diferencia (Masculino - Femenino) por prueba | {titulo_anio}",
        labels={"prueba": "Prueba", "brecha_M_F": "Diferencia (M - F)"},
    )
    fig.update_layout(xaxis_tickangle=-45)

    insight = f"En {titulo_anio}, " + build_insight_maxmin(brecha, group_col=None)
    return fig, insight

#Opciones dropdown tipo de colegio (dinámico)
@app.callback(
    Output("q2_cole_filtro", "options"),
    Input("df_filtrado", "data"),
)
def actualizar_opciones_colegio(data):
    """
    Construye las opciones del dropdown de tipo de colegio con base en los datos
    ya filtrados globalmente.
    """
    dff = pd.DataFrame(data)

    if dff.empty or "cole_caracter" not in dff.columns:
        return []

    # Limpieza mínima de texto para evitar duplicados por espacios
    cole = dff["cole_caracter"].astype(str).str.strip().str.upper()

    opciones = sorted(cole.dropna().unique().tolist())
    return [{"label": c, "value": c} for c in opciones]



#Grafica 2: Brecha por tipo de colegio, año y pruebas
@app.callback(
    Output("grafico_q2_brecha_colegio", "figure"),
    Output("insight_q2_colegio", "children"),
    Input("df_filtrado", "data"),
    Input("q2_year_slider_cole", "value"),
    Input("q2_pruebas_cole", "value"),
    Input("q2_cole_filtro", "value"),
)
def actualizar_q2_brecha_por_colegio(data, anio_slider, pruebas_sel, colegios_sel):
    dff = pd.DataFrame(data)
    if dff.empty:
        return px.bar(title="Sin datos"), "No hay datos para mostrar con los filtros actuales."

    # limpieza de colegio (como ya hacías)
    if "cole_caracter" in dff.columns:
        dff["cole_caracter"] = dff["cole_caracter"].astype(str).str.strip().str.upper()

    dff = apply_year_filter(dff, anio_slider, ANIO_TODOS)
    titulo_anio = "todos los años" if int(anio_slider) == int(ANIO_TODOS) else f"el año {int(anio_slider)}"
    if dff.empty:
        return px.bar(title="Sin datos"), f"No hay datos para {titulo_anio} con los filtros actuales."

    # filtro opcional
    if colegios_sel:
        colegios_sel_clean = [str(c).strip().upper() for c in colegios_sel]
        dff = dff[dff["cole_caracter"].isin(colegios_sel_clean)]
        if dff.empty:
            return px.bar(title="Sin datos"), "No hay datos para esos tipos de colegio con los filtros actuales."

    df_long = brecha_genero_long(dff, pruebas_sel, Q2_PUNTAJES, group_col="cole_caracter")
    if df_long.empty:
        return px.bar(title="No se pudo calcular brecha"), "No se pudo calcular la brecha: faltan M/F o grupos."

    fig = px.bar(
        df_long,
        x="cole_caracter",
        y="brecha_M_F",
        color="prueba",
        barmode="group",
        title=f"Diferencia (Masculino - Femenino) por tipo de colegio | {titulo_anio}",
        labels={"cole_caracter": "Tipo de colegio", "brecha_M_F": "Diferencia (M - F)", "prueba": "Prueba"},
    )
    fig.update_layout(xaxis_tickangle=-45)

    insight = f"En {titulo_anio}, " + build_insight_maxmin(df_long, group_col="cole_caracter")
    return fig, insight

# Opciones dropdown estrato 
@app.callback(
    Output("q2_estrato_filtro", "options"),
    Input("df_filtrado", "data"),
)
def actualizar_opciones_estrato(data):
    """
    Construye las opciones del dropdown de estrato con base en los datos ya filtrados
    globalmente (df_filtrado).
    """
    dff = pd.DataFrame(data)

    # Si no hay datos o no existe la columna de estrato, devolvemos lista vacía
    if dff.empty or "fami_estratovivienda" not in dff.columns:
        return []

    # Tomamos estratos únicos, limpiando espacios
    estratos = dff["fami_estratovivienda"].astype(str).str.strip()

    # Ordenamos alfabéticamente (si quieres orden numérico, lo hacemos luego)
    opciones = sorted(estratos.dropna().unique().tolist())

    # Formato que espera Dash Dropdown
    return [{"label": e, "value": e} for e in opciones]

#Grafica 3: Brecha por estrato, año y pruebas

@app.callback(
    Output("grafico_q2_brecha_estrato", "figure"),
    Output("insight_q2_estrato", "children"),
    Input("df_filtrado", "data"),
    Input("q2_year_slider_estrato", "value"),
    Input("q2_pruebas_estrato", "value"),
    Input("q2_estrato_filtro", "value"),
)
def actualizar_q2_brecha_por_estrato(data, anio_slider, pruebas_sel, estratos_sel):
    dff = pd.DataFrame(data)
    if dff.empty:
        return px.bar(title="Sin datos"), "No hay datos para mostrar con los filtros actuales."

    if "fami_estratovivienda" in dff.columns:
        dff["fami_estratovivienda"] = dff["fami_estratovivienda"].astype(str).str.strip()

    dff = apply_year_filter(dff, anio_slider, ANIO_TODOS)
    titulo_anio = "todos los años" if int(anio_slider) == int(ANIO_TODOS) else f"el año {int(anio_slider)}"
    if dff.empty:
        return px.bar(title="Sin datos"), f"No hay datos para {titulo_anio} con los filtros actuales."

    if estratos_sel:
        estratos_sel_clean = [str(e).strip() for e in estratos_sel]
        dff = dff[dff["fami_estratovivienda"].isin(estratos_sel_clean)]
        if dff.empty:
            return px.bar(title="Sin datos"), "No hay datos para esos estratos con los filtros actuales."

    df_long = brecha_genero_long(dff, pruebas_sel, Q2_PUNTAJES, group_col="fami_estratovivienda")
    if df_long.empty:
        return px.bar(title="No se pudo calcular brecha"), "No se pudo calcular la brecha: faltan M/F o grupos."

    fig = px.bar(
        df_long,
        x="fami_estratovivienda",
        y="brecha_M_F",
        color="prueba",
        barmode="group",
        title=f"Diferencia (Masculino - Femenino) por estrato | {titulo_anio}",
        labels={"fami_estratovivienda": "Estrato del hogar", "brecha_M_F": "Diferencia (M - F)", "prueba": "Prueba"},
    )
    fig.update_layout(xaxis_tickangle=-45)

    insight = f"En {titulo_anio}, " + build_insight_maxmin(df_long, group_col="fami_estratovivienda")
    return fig, insight

def norm_txt(x: str) -> str:
    """Mayúsculas + sin tildes + sin dobles espacios"""
    if x is None:
        return ""
    x = str(x).strip().upper()
    x = "".join(c for c in unicodedata.normalize("NFKD", x) if not unicodedata.combining(c))
    x = " ".join(x.split())
    return x

# --- lista de municipios del GEOJSON (Bolívar) normalizada ---
MPIOS_BOLIVAR = sorted({
    norm_txt(f["properties"].get("name", ""))
    for f in geojson_mcpios.get("features", [])
})

@app.callback(
    Output("mapa_q1_bilingue_delta", "figure"),
    Input("df_filtrado", "data"),
)

    
def mapa_delta_bilingue_por_mpio(data):
    dff = pd.DataFrame(data)
    if dff.empty:
        return px.choropleth_mapbox(title="Sin datos")

    req = {"cole_mcpio_ubicacion", "cole_bilingue", "punt_global"}
    if not req.issubset(dff.columns):
        return px.choropleth_mapbox(title=f"Faltan columnas: {req - set(dff.columns)}")

    # 1) normaliza mpio del dataset
    dff["mpio_norm"] = dff["cole_mcpio_ubicacion"].apply(norm_txt)

    # 2) filtra SOLO municipios que existen en el geojson de Bolívar
    dff = dff[dff["mpio_norm"].isin(MPIOS_BOLIVAR)]
    if dff.empty:
        return px.choropleth_mapbox(title="Con esos filtros no quedaron municipios de Bolívar")

    # 3) bilingüe Sí/No
    dff["bilingue_label"] = dff["cole_bilingue"].map({"S": "Sí", "SI": "Sí", "N": "No", "NO": "No"})

    # promedios por mpio y bilingüe
    g = (
        dff.groupby(["mpio_norm", "bilingue_label"])["punt_global"]
        .mean()
        .reset_index()
    )

    piv = g.pivot(index="mpio_norm", columns="bilingue_label", values="punt_global").reset_index()

    piv["delta"] = piv.get("Sí") - piv.get("No")
    
    # 4) delta seguro (no revienta si falta Sí o No)
    if "Sí" in piv.columns and "No" in piv.columns:
        piv["delta"] = piv["Sí"] - piv["No"]
    else:
        piv["delta"] = None

    # 5) asegúrate de tener TODOS los municipios del geojson (merge con base)
    base = pd.DataFrame({"mpio_norm": MPIOS_BOLIVAR})
    piv = base.merge(piv, on="mpio_norm", how="left")

    # 6) mapa (featureidkey usa el NAME del geojson, pero normalizado!)
    #    como el geojson tiene properties.name con tildes? (en tu ejemplo no)
    #    nosotros normalizamos el "locations" para empatar con properties.name normalizado;
    #    entonces necesitamos crear una copia del geojson con name normalizado:

    geojson_norm = {"type": "FeatureCollection", "features": []}
    for f in geojson_mcpios.get("features", []):
        ff = dict(f)
        props = dict(ff.get("properties", {}))
        props["name_norm"] = norm_txt(props.get("name", ""))
        ff["properties"] = props
        geojson_norm["features"].append(ff)

    prom = (
        dff.groupby("mpio_norm")["punt_global"]
        .mean()
        .reset_index()
        .rename(columns={"punt_global": "promedio_total"})
    )

# merge con piv
    piv = piv.merge(prom, on="mpio_norm", how="left")
    
    fig = px.choropleth_mapbox(
        piv,
        geojson=geojson_norm,
        locations="mpio_norm",
        featureidkey="properties.name_norm",
        color="promedio_total",
        mapbox_style="carto-positron",
        zoom=7,
        center={"lat": 9.2, "lon": -74.8},
        opacity=0.65,
        hover_name="mpio_norm",
        hover_data={"Sí": True, "No": True, "delta": True},
        title="Mapa: Δ puntaje global (Bilingüe Sí - No) por municipio | Bolívar",
    )

    fig.update_layout(margin=dict(l=0, r=0, t=45, b=0))
    return fig

@app.callback(
    Output("grafico_q2_dist_genero", "figure"),
    Output("insight_q2_genero", "children"),
    Input("df_filtrado", "data"),
    Input("q2_year_slider_genero", "value"),
)
def q2_dist_genero(data, anio_slider):
    dff = pd.DataFrame(data)

    if dff.empty or "estu_genero" not in dff.columns or "anio" not in dff.columns:
        fig = px.pie(title="Sin datos para mostrar")
        return fig, "No hay datos suficientes."

    # filtrar por año si no es "Todos"
    if anio_slider is not None and int(anio_slider) != int(ANIO_TODOS):
        dff = dff[dff["anio"] == int(anio_slider)]

    if dff.empty:
        fig = px.pie(title="Sin datos para ese año")
        return fig, "No hay datos para ese año con los filtros actuales."

    # limpiar/normalizar géneros (por si vienen espacios o minúsculas)
    dff["estu_genero"] = dff["estu_genero"].astype(str).str.strip().str.upper()
    dff = dff[dff["estu_genero"].isin(["M", "F"])]

    if dff.empty:
        fig = px.pie(title="Sin datos de género M/F")
        return fig, "No se encuentran categorías M y F con los filtros actuales."

    conteo = dff["estu_genero"].value_counts().rename_axis("genero").reset_index(name="n")
    total = conteo["n"].sum()
    conteo["pct"] = (conteo["n"] / total) * 100

    # labels bonitos
    conteo["genero_label"] = conteo["genero"].map({"M": "M", "F": "F"})

    titulo_anio = "todos los años" if int(anio_slider) == int(ANIO_TODOS) else f"el año {int(anio_slider)}"

    fig = px.pie(
        conteo,
        names="genero_label",
        values="pct",
        title=f"Distribución porcentual por género | {titulo_anio}",
        hole=0,  # si quieres dona: hole=0.35
    )
    fig.update_traces(textinfo="percent", textposition="inside")

    pct_f = float(conteo.loc[conteo["genero"] == "F", "pct"].iloc[0]) if (conteo["genero"] == "F").any() else 0.0
    pct_m = float(conteo.loc[conteo["genero"] == "M", "pct"].iloc[0]) if (conteo["genero"] == "M").any() else 0.0

    insight = f"En {titulo_anio}: F = {pct_f:.1f}% | M = {pct_m:.1f}% (n={total:,})."

    return fig, insight

if __name__ == "__main__":
    app.run(debug=True, port=8051)

