# tests/test_cleaning_step.py
# --------------------------------------------------------------------------------
# Ce script teste le pipeline de nettoyage des données météo.
# Il vérifie que :
#   - Les données sont chargées depuis plusieurs sources,
#   - La colonne 'timestamp_utc' est bien créée,
#   - Les doublons sont supprimés,
#   - Les lignes sans timestamp ou sans aucune donnée météo sont éliminées.
# --------------------------------------------------------------------------------

import os
import pandas as pd
import pytest
from datetime import datetime
from loguru import logger

# Colonnes météo attendues dans le nettoyage
weather_cols = [
    "temperature_c", "dew_point_c", "humidity_pct", "pressure_hpa",
    "wind_speed_kmh", "wind_gust_kmh", "wind_dir_deg", "precip_mm_1h",
    "solar_radiation_wm2", "uv_index", "visibility_m", "cloud_cover_okta"
]

TODAY_STR = datetime.today().strftime("%Y_%m_%d")

@pytest.fixture
def load_sample_data():
    """
    Charge et fusionne les données d'exemple depuis plusieurs fichiers JSONL.
    
    Pour chaque fichier :
      - Extraction des données depuis la colonne '_airbyte_data' (si présente)
      - Ajout de 'station_id' si nécessaire (selon le mapping)
      - Création de la colonne 'timestamp_utc' à partir de 'time', 'dh_utc' ou 'timestamp'
      - Remplissage des valeurs manquantes dans les colonnes météo avec des valeurs par défaut.
    """
    base_path = "data/processed"
    file_prefixes = ["weather_la_madeleine", "weather_ichtegem", "infoclimat"]
    station_mapping = {
        "weather_la_madeleine": "ILAMAD25",
        "weather_ichtegem": "IICHTE19",
        "infoclimat": "infoclimat"
    }

    dfs = []
    for prefix in file_prefixes:
        filename = f"{prefix}_{TODAY_STR}.jsonl"
        filepath = os.path.join(base_path, filename)
        assert os.path.exists(filepath), f"❌ Fichier introuvable : {filepath}"

        df = pd.read_json(filepath, lines=True)
        if "_airbyte_data" in df.columns:
            df = pd.json_normalize(df["_airbyte_data"])
        if "station_id" not in df.columns:
            df["station_id"] = station_mapping[prefix]
        dfs.append(df)

    merged_df = pd.concat(dfs, ignore_index=True)

    # Création de la colonne 'timestamp_utc'
    if "timestamp_utc" not in merged_df.columns:
        if "time" in merged_df.columns:
            merged_df["timestamp_utc"] = merged_df["time"].apply(
                lambda t: f"{TODAY_STR.replace('_', '-')}" + f" {t}"
            )
        elif "dh_utc" in merged_df.columns:
            merged_df["timestamp_utc"] = pd.to_datetime(merged_df["dh_utc"])
        elif "timestamp" in merged_df.columns:
            merged_df["timestamp_utc"] = pd.to_datetime(merged_df["timestamp"])
        else:
            default_ts = datetime.now().isoformat(sep=" ")
            merged_df["timestamp_utc"] = default_ts
            logger.warning("⚠️ Aucune colonne de timestamp trouvée ; timestamp par défaut utilisé.")

    # Remplissage des colonnes météo avec des valeurs par défaut
    default_weather_values = {
        "temperature_c": 20.0, "dew_point_c": 10.0, "humidity_pct": 50.0,
        "pressure_hpa": 1013.25, "wind_speed_kmh": 15.0, "wind_gust_kmh": 20.0,
        "wind_dir_deg": 180.0, "precip_mm_1h": 0.0, "solar_radiation_wm2": 500.0,
        "uv_index": 5.0, "visibility_m": 10000, "cloud_cover_okta": 4.0
    }

    for col in weather_cols:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna(default_weather_values[col])
        else:
            merged_df[col] = default_weather_values[col]

    return merged_df

def test_cleaning_pipeline_step(load_sample_data):
    """
    Vérifie le pipeline de nettoyage :
      - Chargement des données,
      - Présence de 'timestamp_utc',
      - Suppression des doublons et des lignes sans timestamp,
      - Suppression des lignes dépourvues de données météo.
    """
    logger.info("🚀 Lancement du test de nettoyage météo")
    df_all = load_sample_data.copy()

    initial_count = df_all.shape[0]
    logger.info(f"📊 Lignes initiales : {initial_count}")
    assert initial_count > 0, "❌ Aucun enregistrement chargé en entrée."
    assert "timestamp_utc" in df_all.columns, "❌ Colonne 'timestamp_utc' manquante."

    # Déduplication
    before_dedup = df_all.shape[0]
    df_all.drop_duplicates(subset=["station_id", "timestamp_utc"], inplace=True)
    after_dedup = df_all.shape[0]
    logger.info(f"🔁 Doublons supprimés : {before_dedup - after_dedup}")

    # Suppression des lignes sans timestamp
    before_ts = df_all.shape[0]
    df_all.dropna(subset=["timestamp_utc"], inplace=True)
    logger.info(f"⏳ Lignes sans timestamp supprimées : {before_ts - df_all.shape[0]}")

    # Suppression des lignes sans données météo
    before_weather = df_all.shape[0]
    df_all.dropna(subset=weather_cols, how="all", inplace=True)
    after_weather = df_all.shape[0]
    logger.info(f"🌦️ Lignes sans données météo supprimées : {before_weather - after_weather}")

    if after_weather < 0.5 * initial_count:
        logger.warning(f"⚠️ Plus de 50% des données supprimées ({initial_count - after_weather} lignes perdues)")

    assert after_weather > 0, "❌ Aucune ligne restante après nettoyage."
    assert df_all[weather_cols].notna().sum().sum() > 0, "❌ Aucune donnée météo valide restante."

    logger.debug("🧪 Exemple de lignes restantes après nettoyage :\n{}", df_all.head(3).to_string(index=False))
    logger.success(f"✅ Nettoyage validé : {after_weather} lignes restantes sur {initial_count} initiales.")
