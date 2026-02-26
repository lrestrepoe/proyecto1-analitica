import json
from pathlib import Path


# ESTE SCRIPT ES SOLO PARA CORREGIR EL GEOJSON DE LOS MUNICIPIOS DE COLOMBIA
# UNA SOLA VEZ, PARA QUE LOS COORDENADAS ESTEN EN WGS84 Y NO EN OTRO SISTEMA DE REFERENCIA

IN_PATH = Path("data/mpios.json")
OUT_PATH = Path("data/mpios_fix_colombia.json")

# BBOX objetivo aproximado de Colombia en WGS84 (lon/lat)
# (puedes ajustarlo fino después si quieres)
TARGET_MINX = -75.7
TARGET_MINY = 7.6
TARGET_MAXX = -73.3
TARGET_MAXY = 10.9

def geojson_bbox(gj):
    minx = miny = 1e18
    maxx = maxy = -1e18

    def walk(coords):
        if isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
            return [coords]
        out = []
        for c in coords:
            out.extend(walk(c))
        return out

    for ft in gj["features"]:
        coords = ft["geometry"]["coordinates"]
        for x, y in walk(coords):
            minx = min(minx, x); maxx = max(maxx, x)
            miny = min(miny, y); maxy = max(maxy, y)

    return minx, miny, maxx, maxy

def transform_bbox(coords, src_bbox, tgt_bbox):
    src_minx, src_miny, src_maxx, src_maxy = src_bbox
    tgt_minx, tgt_miny, tgt_maxx, tgt_maxy = tgt_bbox

    # factores escala (no-uniforme, x y y por separado)
    sx = (tgt_maxx - tgt_minx) / (src_maxx - src_minx)
    sy = (tgt_maxy - tgt_miny) / (src_maxy - src_miny)

    def rec(c):
        if isinstance(c[0], (int, float)) and isinstance(c[1], (int, float)):
            x, y = c
            x2 = tgt_minx + (x - src_minx) * sx
            y2 = tgt_miny + (y - src_miny) * sy
            return [x2, y2]
        return [rec(ci) for ci in c]

    return rec(coords), sx, sy


gj = json.loads(IN_PATH.read_text(encoding="utf-8"))

src_bbox = geojson_bbox(gj)
tgt_bbox = (TARGET_MINX, TARGET_MINY, TARGET_MAXX, TARGET_MAXY)

sx = sy = None
for ft in gj["features"]:
    new_coords, sx, sy = transform_bbox(ft["geometry"]["coordinates"], src_bbox, tgt_bbox)
    ft["geometry"]["coordinates"] = new_coords

# -------------------------------
# AJUSTE FINO: mover por centro
# -------------------------------

TARGET_CENTER_LON = -74.6
TARGET_CENTER_LAT = 9.2

def iter_coords(geom):
    coords = []
    def walk(c):
        if isinstance(c[0], (int, float)):
            coords.append(c)
        else:
            for ci in c:
                walk(ci)
    walk(geom["coordinates"])
    return coords

def centroid_of_features(features):
    xs, ys = [], []
    for f in features:
        geom = f["geometry"]
        for x, y in iter_coords(geom):
            xs.append(x)
            ys.append(y)
    return sum(xs)/len(xs), sum(ys)/len(ys)

def shift_geom(geom, dx, dy):
    def rec(c):
        if isinstance(c[0], (int, float)):
            return [c[0] + dx, c[1] + dy]
        return [rec(ci) for ci in c]
    geom["coordinates"] = rec(geom["coordinates"])

# calcular centro actual
cx, cy = centroid_of_features(gj["features"])

# cuánto mover
dx = TARGET_CENTER_LON - cx
dy = TARGET_CENTER_LAT - cy

# aplicar desplazamiento
for f in gj["features"]:
    shift_geom(f["geometry"], dx, dy)

OUT_PATH.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")

print("Listo:", OUT_PATH)
print("SRC BBOX:", src_bbox)
print("TGT BBOX:", tgt_bbox)
print("Escalas sx, sy:", sx, sy)