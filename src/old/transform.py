# -----------------------------------------------------------------------------
# Importation des librairies
# -----------------------------------------------------------------------------
import os       # Pour la gestion du système de fichiers (création de dossiers, etc.)
import sys      # Pour utiliser sys.exit() en cas d'erreur fatale
import time     # Pour mesurer la durée d'exécution du script
import argparse # Pour gérer les arguments en ligne de commande
import json     # Pour la sérialisation/désérialisation en JSON
from typing import Optional, Any, Dict  # Pour ajouter des annotations de type et améliorer la lisibilité du code
import pandas as pd  # Pour manipuler des DataFrame et effectuer des transformations sur les données
import numpy as np   # Pour les opérations numériques et la gestion des tableaux
from datetime import datetime  # Pour manipuler et formater les dates et heures
from dotenv import load_dotenv  # Pour charger les variables d'environnement depuis un fichier .env
from loguru import logger  # Pour la gestion avancée des logs (flexibilité, rotation, etc.)

# -----------------------------------------------------------------------------
# Chargement des variables d'environnement
# -----------------------------------------------------------------------------
load_dotenv()  # Charge les variables définies dans le fichier .env (ex: clés d'API)

# -----------------------------------------------------------------------------
# Définition des répertoires utilisés dans le traitement
# -----------------------------------------------------------------------------
INPUT_DIR = "data/backup/"       # Répertoire contenant les fichiers d'entrée (ici des fichiers Parquet)
OUTPUT_DIR = "data/processed/"   # Répertoire où seront enregistrées les données transformées
LOG_DIR = "logs/"                # Répertoire où seront stockés les fichiers de logs

# Création des dossiers de sortie et de logs s'ils n'existent pas
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Configuration des logs avec Loguru
# -----------------------------------------------------------------------------
CURRENT_TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Création d'un timestamp unique
LOG_FILE = os.path.join(LOG_DIR, f"transformation_{CURRENT_TIMESTAMP}.log")
logger.add(
    LOG_FILE,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="10 MB",  # Rotation du log si la taille dépasse 10 MB
    retention="7 days"  # Conservation des logs pendant 7 jours
)
# ---------------------------------------------------------------------
# Fonctions utilitaires pour la conversion, le nettoyage et l'enrichissement
# ---------------------------------------------------------------------

def fahrenheit_to_celsius(f: float) -> Optional[float]:
    """Convertit les degrés Fahrenheit en Celsius"""
    try:
        return round((float(f) - 32) * 5/9, 2)
    except (ValueError, TypeError):
        return None

def mph_to_kmh(mph: float) -> Optional[float]:
    """Convertit les miles par heure en km/h"""
    try:
        return round(float(mph) * 1.60934, 2)
    except (ValueError, TypeError):
        return None

def inhg_to_hpa(inhg: float) -> Optional[float]:
    """Convertit la pression atmosphérique de inHg en hPa"""
    try:
        return round(float(inhg) * 33.8639, 2)
    except (ValueError, TypeError):
        return None
def inches_to_mm(inches: float) -> Optional[float]:
    """Convertit les pouces (inches) en millimètres"""
    try:
        return round(float(inches) * 25.4, 2)
    except (ValueError, TypeError):
        return None

def cardinal_to_degrees(direction: str) -> Optional[int]:
    """Convertit une direction cardinal (ex: 'NW') en angle en degrés"""
    directions = {
        "N": 0, "NNE": 22, "NE": 45, "ENE": 67, "E": 90, "ESE": 112,
        "SE": 135, "SSE": 157, "S": 180, "SSW": 202, "SW": 225,
        "WSW": 247, "W": 270, "WNW": 292, "NW": 315, "NNW": 337
    }
    return directions.get(direction.upper()) if isinstance(direction, str) else None
# ---------------------------------------------------------------------
# Fonctions de traitement des données par source
# ---------------------------------------------------------------------

def process_weather_underground(df: pd.DataFrame, station_meta: Dict[str, Any]) -> pd.DataFrame:
    """Nettoie et convertit les données Weather Underground"""
    df_data = pd.json_normalize(df["_airbyte_data"])
    
    # Conversion des unités
    df_clean = pd.DataFrame({
        "timestamp": pd.to_datetime(df_data["Time"], errors="coerce"),
        "temperature_c": df_data["Temperature"].apply(fahrenheit_to_celsius),
        "humidity_percent": df_data["Humidity"],
        "wind_speed_kmh": df_data["Speed"].apply(mph_to_kmh),
        "wind_gust_kmh": df_data["Gust"].apply(mph_to_kmh),
        "wind_direction_deg": df_data["Wind"].apply(cardinal_to_degrees),
        "dew_point_c": df_data["Dew Point"].apply(fahrenheit_to_celsius),
        "pressure_hpa": df_data["Pressure"].apply(inhg_to_hpa),
        "precip_1h_mm": df_data["Precip. Rate."].apply(inches_to_mm),
        "precip_total_mm": df_data["Precip. Accum."].apply(inches_to_mm),
        "uv_index": df_data["UV"],
        "solar_wm2": df_data["Solar"]
    })

    # Ajout des métadonnées de station
    for key, value in station_meta.items():
        df_clean[key] = value

    return df_clean


def process_infoclimat(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie et transforme les données InfoClimat"""
    df_data = pd.json_normalize(df["_airbyte_data"])

    df_clean = pd.DataFrame({
        "timestamp": pd.to_datetime(df_data["data"], errors="coerce"),
        "temperature_c": df_data["metadata.temperature"],
        "humidity_percent": df_data["metadata.humidite"],
        "wind_speed_kmh": df_data["metadata.vent_moyen"],
        "wind_gust_kmh": df_data["metadata.vent_rafales"],
        "wind_direction_deg": df_data["metadata.vent_direction"],
        "dew_point_c": df_data["metadata.point_de_rosee"],
        "pressure_hpa": df_data["metadata.pression"],
        "precip_1h_mm": df_data["metadata.pluie_1h"],
        "precip_total_mm": df_data["metadata.pluie_3h"],
        "visibility_km": df_data["metadata.visibilite"],
        "cloud_cover_okta": df_data["metadata.nebulosite"],
        "snow_on_ground_cm": df_data["metadata.neige_au_sol"],
        "weather_code_omm": df_data["metadata.temps_omm"],
        "station_id": "INFOCLIMAT",  # Métadonnées génériques
        "station_name": "Station InfoClimat",
        "city": None,
        "state": None,
        "latitude": None,
        "longitude": None,
        "elevation_m": None,
        "hardware": None,
        "software": None
    })

    return df_clean
# ---------------------------------------------------------------------
# Fusion des DataFrames et nettoyage final
# ---------------------------------------------------------------------
def unify_and_save(dfs: list, output_path: str):
    """Fusionne tous les DataFrames nettoyés, conserve uniquement les colonnes communes, et sauvegarde en JSON"""
    df_concat = pd.concat(dfs, ignore_index=True)
    logger.info(f"Nombre total de lignes avant nettoyage final : {df_concat.shape[0]}")

    # Supprimer les colonnes trop vides (>80% de NaN)
    threshold = 0.8
    df_concat = df_concat.loc[:, df_concat.isnull().mean() < threshold]

    # Supprimer les lignes trop vides (>50% de NaN)
    df_concat = df_concat[df_concat.isnull().mean(axis=1) < 0.5]

    logger.info(f"Nombre total de lignes après nettoyage final : {df_concat.shape[0]}")

    # Export
    df_concat.to_json(output_path, orient="records", lines=True, force_ascii=False)
    logger.success(f"✅ Données fusionnées sauvegardées dans : {output_path}")
# -----------------------------------------------------------------------------
# Pipeline principal
# -----------------------------------------------------------------------------
def main():
    start_time = time.time()
    logger.info("🚀 Démarrage du pipeline de transformation météo...")

    try:
        # ---------------------------------------------------------------------
        # Chargement des fichiers JSONL
        # ---------------------------------------------------------------------
        file_la_madeleine = os.path.join(INPUT_DIR, "weather_la_madeleine_2025_03_21.jsonl")
        file_ichtegem = os.path.join(INPUT_DIR, "weather_ichtegem_2025_03_21.jsonl")
        file_infoclimat = os.path.join(INPUT_DIR, "infoclimat_2025_03_21.jsonl")

        df_la_madeleine = pd.read_json(file_la_madeleine, lines=True)
        df_ichtegem = pd.read_json(file_ichtegem, lines=True)
        df_infoclimat = pd.read_json(file_infoclimat, lines=True)

        logger.info("✅ Fichiers chargés avec succès.")

        # ---------------------------------------------------------------------
        # Définition des métadonnées des stations amateurs
        # ---------------------------------------------------------------------
        meta_la_madeleine = {
            "station_id": "ILAMAD25",
            "station_name": "La Madeleine",
            "latitude": 50.659,
            "longitude": 3.07,
            "elevation_m": 23,
            "city": "La Madeleine",
            "state": "-/-",
            "hardware": "other",
            "software": "EasyWeatherPro_V5.1.6"
        }

        meta_ichtegem = {
            "station_id": "IICHTE19",
            "station_name": "WeerstationBS",
            "latitude": 51.092,
            "longitude": 2.999,
            "elevation_m": 15,
            "city": "Ichtegem",
            "state": "-/-",
            "hardware": "other",
            "software": "EasyWeatherV1.6.6"
        }

        # ---------------------------------------------------------------------
        # Traitement des fichiers individuels
        # ---------------------------------------------------------------------
        df_madeleine_clean = process_weather_underground(df_la_madeleine, meta_la_madeleine)
        df_ichtegem_clean = process_weather_underground(df_ichtegem, meta_ichtegem)
        df_infoclimat_clean = process_infoclimat(df_infoclimat)

        logger.info("🧼 Données nettoyées et harmonisées.")

        # ---------------------------------------------------------------------
        # Fusion des données et export final
        # ---------------------------------------------------------------------
        output_file = os.path.join(OUTPUT_DIR, "meteo_fusionnee.json")
        unify_and_save(
            dfs=[df_madeleine_clean, df_ichtegem_clean, df_infoclimat_clean],
            output_path=output_file
        )

    except Exception as e:
        logger.error(f"❌ Une erreur critique est survenue : {e}")
        sys.exit(1)

    elapsed = time.time() - start_time
    logger.success(f"🎉 Pipeline terminé en {elapsed:.2f} secondes.")

# -----------------------------------------------------------------------------
# Point d'entrée du script
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
