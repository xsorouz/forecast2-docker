# tests/test_clean_wu_dataframe.py
# --------------------------------------------------------------------------------
# Ce test vérifie que la fonction clean_wu_dataframe convertit correctement
# les unités des données météo et enrichit les observations avec les métadonnées
# de la station Weather Underground.
# --------------------------------------------------------------------------------

import pandas as pd
from transform_all_sources import clean_wu_dataframe, WU_METADATA

def test_clean_wu_dataframe_basic():
    """
    Vérifie que :
      - La conversion des unités est effectuée (ex: Fahrenheit → Celsius)
      - Les métadonnées de la station sont ajoutées correctement.
    """
    # Création d'un DataFrame simulé avec des données brutes
    df_raw = pd.DataFrame({
        "station_id": ["ILAMAD25"],
        "temperature": ["68°F"],
        "dew_point": ["50°F"],
        "humidity": ["70"],
        "pressure": ["29.92"],
        "speed": ["10"],
        "gust": ["15"],
        "wind": ["NE"],
        "precip_rate": ["0.1"],
        "solar": ["450"],
        "uv": ["4"],
        "timestamp_utc": ["2025-03-24 08:00:00"]
    })

    # Application de la fonction de nettoyage avec les métadonnées associées
    df_clean = clean_wu_dataframe(df_raw, WU_METADATA["ILAMAD25"])

    # Vérifications
    assert df_clean.shape[0] == 1
    assert "temperature_c" in df_clean.columns
    assert df_clean.loc[0, "temperature_c"] == 20.0, "❌ La température n’a pas été correctement convertie"
    assert df_clean.loc[0, "station_name"] == "La Madeleine"
    assert "wind_dir_deg" in df_clean.columns
