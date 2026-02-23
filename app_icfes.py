from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
df = pd.read_parquet(BASE_DIR / "data" / "df_global.parquet")