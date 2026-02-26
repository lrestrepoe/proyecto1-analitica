import json
from pathlib import Path

IN_PATH  = Path("data/mpios.json")
OUT_PATH = Path("data/mpios_bolivar_fix.json")

# Coordenadas reales aprox (WGS84) para anclar la transformación
# (sirven perfecto para alinear visualmente)
T_CARTAGENA = (-75.4794, 10.3910)  # (lon, lat)
T_MAGANGUE  = (-74.7500,  9.2400)

def walk_points(coords):
    if isinstance(coords, (list, tuple)) and len(coords) == 2 and all(isinstance(v, (int, float)) for v in coords):
        yield coords
    else:
        for c in coords:
            yield from walk_points(c)

def bbox_geom(geom):
    minx = miny = 1e18
    maxx = maxy = -1e18
    for x, y in walk_points(geom["coordinates"]):
        minx = min(minx, x); maxx = max(maxx, x)
        miny = min(miny, y); maxy = max(maxy, y)
    return minx, miny, maxx, maxy

def centroid_bbox(b):
    minx, miny, maxx, maxy = b
    return ((minx + maxx) / 2, (miny + maxy) / 2)

def find_feature(gj, name):
    for ft in gj["features"]:
        if ft.get("properties", {}).get("name") == name:
            return ft
    return None

def transform_coords(coords, src_origin, tgt_origin, sx, sy):
    x0, y0 = src_origin
    lon0, lat0 = tgt_origin

    def rec(c):
        if isinstance(c, (list, tuple)) and len(c) == 2 and all(isinstance(v, (int, float)) for v in c):
            x, y = c
            return [lon0 + (x - x0) * sx, lat0 + (y - y0) * sy]
        return [rec(ci) for ci in c]

    return rec(coords)

gj = json.loads(IN_PATH.read_text(encoding="utf-8"))

# 1) Filtra SOLO Bolívar
gj_bol = {
    "type": "FeatureCollection",
    "features": [f for f in gj.get("features", []) if f.get("properties", {}).get("dpt") == "BOLIVAR"]
}

if not gj_bol["features"]:
    raise SystemExit("No encontré features con properties.dpt == 'BOLIVAR'")

# 2) Busca Cartagena y Magangué dentro de Bolívar
f_cart = find_feature(gj_bol, "CARTAGENA")
f_mag  = find_feature(gj_bol, "MAGANGUE")

if f_cart is None or f_mag is None:
    raise SystemExit("No encontré CARTAGENA o MAGANGUE en el GeoJSON de Bolívar (revisa properties.name).")

src_cart = centroid_bbox(bbox_geom(f_cart["geometry"]))
src_mag  = centroid_bbox(bbox_geom(f_mag["geometry"]))

# 3) Calcula escalas (sx, sy) usando esos dos puntos
sx = (T_MAGANGUE[0] - T_CARTAGENA[0]) / (src_mag[0] - src_cart[0])
sy = (T_MAGANGUE[1] - T_CARTAGENA[1]) / (src_mag[1] - src_cart[1])

# 4) Aplica transformación a TODO Bolívar
for ft in gj_bol["features"]:
    ft["geometry"]["coordinates"] = transform_coords(
        ft["geometry"]["coordinates"],
        src_origin=src_cart,
        tgt_origin=T_CARTAGENA,
        sx=sx,
        sy=sy,
    )

OUT_PATH.write_text(json.dumps(gj_bol, ensure_ascii=False), encoding="utf-8")
print("Listo:", OUT_PATH)
print("sx, sy:", sx, sy)