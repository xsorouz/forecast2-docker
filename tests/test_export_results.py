# tests/test_export_results.py
# --------------------------------------------------------------------------------
# Ce test vérifie que la fonction export_results :
#   - Exporte correctement les données validées localement en formats Parquet et JSON,
#   - Lance l'export sur S3.
# --------------------------------------------------------------------------------

import os
import pandas as pd
from unittest.mock import patch
from transform_all_sources import export_results, LOCAL_OUTPUT_DIR, TODAY_STR

@patch("awswrangler.s3.to_json")
def test_export_results_local_and_s3(mock_s3_export):
    """
    Test que les données validées sont exportées localement et sur S3.
    """
    sample_data = [{
        "station_id": "S1",
        "timestamp_utc": "2025-03-24 12:00:00",
        "temperature_c": 21.0
    }]

    export_results(sample_data)

    json_path = os.path.join(LOCAL_OUTPUT_DIR, "final_weather.json")
    parquet_path = os.path.join(LOCAL_OUTPUT_DIR, "final_weather.parquet")

    # Vérifie que les fichiers locaux existent
    assert os.path.exists(json_path), "❌ Export JSON local manquant"
    assert os.path.exists(parquet_path), "❌ Export Parquet local manquant"
    # Vérifie que l'export S3 a bien été appelé
    assert mock_s3_export.called, "❌ Export S3 non déclenché"
