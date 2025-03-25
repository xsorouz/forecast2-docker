# tests/test_download_and_rename_from_s3.py
# --------------------------------------------------------------------------------
# Ce test vérifie que la fonction download_and_rename_from_s3 :
#   - Lit correctement un fichier JSONL depuis S3,
#   - Le renomme selon le format attendu,
#   - Sauvegarde le fichier localement.
# --------------------------------------------------------------------------------

import os
import pandas as pd
from unittest.mock import patch
from transform_all_sources import download_and_rename_from_s3, TODAY_STR, LOCAL_OUTPUT_DIR

@patch("awswrangler.s3.read_json")
def test_download_and_rename(mock_read_json):
    """
    Test que le fichier est lu depuis S3 et sauvegardé localement avec le bon nom.
    """
    # Simulation d'un DataFrame retourné par S3
    mock_df = pd.DataFrame({"col1": [1], "col2": [2]})
    mock_read_json.return_value = mock_df

    # Paramètres de test
    s3_path = "s3://fake-bucket/test.jsonl"
    file_type = "weather_la_madeleine"

    # Appel de la fonction
    output_path = download_and_rename_from_s3(s3_path, file_type)

    # Vérifications
    assert os.path.exists(output_path), "❌ Le fichier n’a pas été créé localement"
    assert output_path.endswith(f"{file_type}_{TODAY_STR}.jsonl"), "❌ Nom de fichier incorrect"
    result_df = pd.read_json(output_path, lines=True)
    pd.testing.assert_frame_equal(result_df, mock_df)
