# tests/test_main_pipeline.py
# --------------------------------------------------------------------------------
# Ce test vérifie l'exécution complète du pipeline de transformation et d'export
# (transform_all_sources.py) en simulant (mock) les interactions avec S3 et
# les fonctions critiques du pipeline.
#
# Il s'assure que le pipeline va jusqu'à l'export final sans erreurs et
# que l'export est bien déclenché.
#
# De plus, il vérifie que le fichier final exporté (final_weather.json)
# ne contient aucun doublon strict.
# --------------------------------------------------------------------------------

from unittest.mock import patch, MagicMock
import pandas as pd
import os
import pytest

# Importation de la fonction main du pipeline
from transform_all_sources import main

@patch("transform_all_sources.find_latest_s3_file")
@patch("transform_all_sources.download_and_rename_from_s3")
@patch("transform_all_sources.load_infoclimat_from_file")
@patch("transform_all_sources.clean_wu_dataframe")
@patch("transform_all_sources.export_results")
@patch("transform_all_sources.validate_records")
@patch("pandas.read_json")
@patch("pandas.json_normalize")
def test_main_pipeline_mocked(
    mock_normalize, mock_read_json, mock_validate, mock_export,
    mock_clean, mock_load_ic, mock_download, mock_find
):
    """
    Teste l'exécution complète du pipeline avec mocks.
    On simule les appels aux fonctions S3 et aux fonctions de nettoyage pour vérifier
    que le pipeline s'exécute jusqu'à l'export final.
    """
    # Simulation des chemins S3 et des fichiers locaux
    mock_find.return_value = "s3://fake-bucket/fake-file.jsonl"
    mock_download.return_value = "data/processed/fake_file.jsonl"

    # Simulation d'un DataFrame brut (données Weather Underground)
    mock_df_raw = pd.DataFrame({
        "_airbyte_data": [{
            "station_id": "ILAMAD25",
            "time": "08:00:00",
            "temperature": 68,
            "dew_point": 50,
            "humidity": 70,
            "pressure": 29.92,
            "speed": 10,
            "gust": 15,
            "wind": "N",
            "precip_rate": 0.1,
            "solar": "500",
            "uv": 5
        }]
    })
    mock_read_json.return_value = mock_df_raw
    mock_normalize.return_value = pd.DataFrame(mock_df_raw["_airbyte_data"].tolist())

    # Simulation du nettoyage pour Weather Underground
    mock_clean.return_value = pd.DataFrame([{
        "station_id": "ILAMAD25",
        "timestamp_utc": "2025-03-24 08:00:00",
        "station_name": "WU",
        "latitude": 50.0,
        "longitude": 3.0,
        "elevation_m": 10,
        "temperature_c": 20.0,
        "dew_point_c": 10.0,
        "humidity_pct": 60.0,
        "pressure_hpa": 1015.0,
        "wind_speed_kmh": 12.0,
        "wind_gust_kmh": 20.0,
        "wind_dir_deg": 90,
        "precip_mm_1h": 0.0,
        "solar_radiation_wm2": 500.0,
        "uv_index": 3,
        "visibility_m": 10000,
        "cloud_cover_okta": 4,
        "source": "weather_underground"
    }])

    # Simulation des données InfoClimat
    mock_load_ic.return_value = pd.DataFrame([{
        "station_id": "infoclimat",
        "timestamp_utc": "2025-03-24 08:00:00",
        "temperature_c": 15.0
    }])

    # Simulation de la validation des enregistrements
    mock_validate.return_value = [{"station_id": "ILAMAD25", "timestamp_utc": "2025-03-24", "temperature_c": 20}]

    # Appel réel du pipeline
    main()

    # Vérifie que l'export a été appelé
    assert mock_export.called, "❌ L’export n’a pas été appelé à la fin"

def test_no_strict_duplicates_final_output():
    """
    Vérifie qu’après le traitement complet, le fichier final 'final_weather.json'
    ne contient aucun doublon strict (lignes identiques sur toutes les colonnes).
    """
    path = "data/processed/final_weather.json"
    if not os.path.exists(path):
        pytest.skip(f"⏭️ Fichier {path} manquant, test ignoré.")

    df = pd.read_json(path, lines=True)
    df.columns = df.columns.str.lower().str.strip()

    # Sélectionne uniquement les colonnes contenant des types hashables
    hashable_cols = [
        col for col in df.columns
        if df[col].map(type).isin([str, int, float, type(None)]).all()
    ]
    df_hashable = df[hashable_cols]

    nb_total = df_hashable.shape[0]
    nb_uniques = df_hashable.drop_duplicates().shape[0]
    nb_dups = nb_total - nb_uniques

    if nb_dups > 0:
        print(f"🚨 {nb_dups} doublons stricts détectés dans la sortie finale")

    assert nb_dups == 0, f"❌ {nb_dups} doublons stricts détectés dans `final_weather.json`"
