# tests/test_validate_records.py
# --------------------------------------------------------------------------------
# Ce test vérifie que la fonction validate_records :
#   - Ne conserve que les lignes valides selon le schéma Pydantic WeatherObservation,
#   - Ignore les lignes invalides.
# --------------------------------------------------------------------------------

import pandas as pd
from transform_all_sources import validate_records

def test_validate_records_only_valid_rows():
    """
    Vérifie que seules les lignes valides sont conservées après validation Pydantic.
    """
    # Création d'un DataFrame avec une ligne valide et une ligne invalide
    df = pd.DataFrame([
        {
            "station_id": "S1",
            "timestamp_utc": "2025-03-24T10:00:00",
            "station_name": "TestStation",
            "latitude": 50.0,
            "longitude": 3.0,
            "elevation_m": 15,
            "temperature_c": 20.0,
            "dew_point_c": 10.0,
            "humidity_pct": 50,
            "pressure_hpa": 1015,
            "wind_speed_kmh": 10,
            "wind_gust_kmh": 15,
            "wind_dir_deg": 90,
            "precip_mm_1h": 0,
            "solar_radiation_wm2": 500,
            "uv_index": 3,
            "visibility_m": 10000,
            "cloud_cover_okta": 4,
            "source": "mock"
        },
        {
            "station_id": "S2",
            "timestamp_utc": "2025-03-24T11:00:00",
            "temperature_c": "not_a_number"  # Ligne invalide
        }
    ])

    validated = validate_records(df)

    assert isinstance(validated, list), "❌ Le résultat doit être une liste"
    assert len(validated) == 1, "❌ Une ligne invalide a été acceptée"
    assert validated[0]["station_id"] == "S1", "❌ La ligne valide n'a pas été correctement validée"
