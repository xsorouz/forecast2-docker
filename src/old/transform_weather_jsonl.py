# -----------------------------------------------------------------------------
# Étape 1 – Importation des librairies, configuration, et chargement des fichiers
# -----------------------------------------------------------------------------
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any
import pandas as pd
import numpy as np
from loguru import logger

# -----------------------------------------------------------------------------
# Configuration initiale
# -----------------------------------------------------------------------------
# Répertoires d'entrée et de sortie
INPUT_FILES = {
    "weather_la_madeleine": "data/backup/weather_la_madeleine_2025_03_21.jsonl",
    "weather_ichtegem": "data/backup/weather_ichtegem_2025_03_21.jsonl",
    "infoclimat": "data/backup/infoclimat_2025_03_21.jsonl"
}
OUTPUT_DIR = "data/processed"
LOG_DIR = "logs"

# Création des dossiers si nécessaire
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Fichier de log horodaté
CURRENT_TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = os.path.join(LOG_DIR, f"fusion_meteo_{CURRENT_TIMESTAMP}.log")
logger.add(LOG_FILE, level="INFO", format="{time} | {level} | {message}")

logger.info("🚀 Démarrage du script de fusion des données météo JSONL")

# -----------------------------------------------------------------------------
# Chargement de chaque fichier JSONL dans un DataFrame
# -----------------------------------------------------------------------------
def load_jsonl_file(file_path: str) -> pd.DataFrame:
    """
    Charge un fichier JSONL en DataFrame.
    :param file_path: Chemin du fichier .jsonl
    :return: DataFrame pandas
    """
    try:
        logger.info(f"📥 Chargement du fichier : {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        df = pd.json_normalize(lines)
        logger.info(f"✅ Chargement réussi : {len(df)} lignes, {len(df.columns)} colonnes")
        return df
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement du fichier {file_path} : {e}")
        return pd.DataFrame()

# Chargement des 3 fichiers
raw_datasets: Dict[str, pd.DataFrame] = {
    name: load_jsonl_file(path)
    for name, path in INPUT_FILES.items()
}

# Vérification des fichiers bien chargés
for name, df in raw_datasets.items():
    logger.info(f"🔍 Aperçu [{name}] – {df.shape[0]} lignes, {df.shape[1]} colonnes")

# Stockage pour stats qualité futures
data_quality_report: Dict[str, Dict[str, Any]] = {}

# Bloc validé ✔️ si tout s’est bien passé

# -----------------------------------------------------------------------------
# Étape 2 – Extraction des données horaires et ajout des métadonnées
# -----------------------------------------------------------------------------
 

# Métadonnées manuelles pour les deux stations amateurs  
STATION_METADATA = {
    "weather_la_madeleine": {
        "weather_station_id": "ILAMAD25",
        "station_name": "La Madeleine",
        "latitude": 50.659,
        "longitude": 3.07,
        "elevation": 23,
        "city": "La Madeleine",
        "state": "-/-",
        "hardware": "other",
        "software": "EasyWeatherPro_V5.1.6"
    },
    "weather_ichtegem": {
        "weather_station_id": "IICHTE19",
        "station_name": "WeerstationBS",
        "latitude": 51.092,
        "longitude": 2.999,
        "elevation": 15,
        "city": "Ichtegem",
        "state": "-/-",
        "hardware": "other",
        "software": "EasyWeatherV1.6.6"
    }
}

def enrich_with_metadata(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Ajoute les métadonnées à toutes les lignes d’un DataFrame pour une station donnée.
    """
    metadata = STATION_METADATA.get(source)
    if metadata:
        for key, value in metadata.items():
            df[key] = value
        logger.info(f"🔗 Métadonnées ajoutées pour la source : {source}")
    else:
        logger.warning(f"⚠️ Aucune métadonnée définie pour la source {source}")
    return df

def extract_infoclimat_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait les données horaires du fichier Infoclimat depuis la structure :
    df['data']['weather']['hourly']
    """
    logger.info("⏳ Extraction des données horaires depuis Infoclimat")
    try:
        # Accès imbriqué
        record = df.iloc[0].to_dict()
        hourly_data = record.get("data", {}).get("weather", {}).get("hourly", {})

        if isinstance(hourly_data, str):
            hourly_data = json.loads(hourly_data)

        all_rows = []
        for station_id, observations in hourly_data.items():
            if isinstance(observations, list):
                for row in observations:
                    if isinstance(row, dict):
                        row["id_station"] = station_id
                        all_rows.append(row)

        df_hourly = pd.DataFrame(all_rows)
        logger.info(f"✅ Extraction réussie : {len(df_hourly)} lignes extraites depuis Infoclimat")
        return df_hourly

    except Exception as e:
        logger.error(f"❌ Échec de l'extraction Infoclimat : {e}")
        return pd.DataFrame()

def extract_amateur_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pour les fichiers Weather Underground (Madeleine, Ichtegem),
    extrait les données contenues dans la colonne _airbyte_data.
    """
    if "_airbyte_data" not in df.columns:
        logger.warning("⚠️ Colonne '_airbyte_data' absente, aucun traitement effectué.")
        return df
    df_flat = pd.json_normalize(df["_airbyte_data"])
    logger.info(f"🧾 Extraction de _airbyte_data terminée : {len(df_flat)} lignes, {len(df_flat.columns)} colonnes")
    return df_flat

# -----------------------------------------------------------------------------  
# Application aux fichiers chargés  
# -----------------------------------------------------------------------------  

processed_datasets = {}

# 1. Infoclimat : extraction de la structure imbriquée + métadonnées déjà dans les données
df_infoclimat_hourly = extract_infoclimat_hourly(raw_datasets["infoclimat"])
processed_datasets["infoclimat"] = df_infoclimat_hourly

# 2. Stations amateurs : extraction + ajout des métadonnées
for station in ["weather_la_madeleine", "weather_ichtegem"]:
    df_amateur = extract_amateur_data(raw_datasets[station])
    df_amateur = enrich_with_metadata(df_amateur, station)
    processed_datasets[station] = df_amateur
