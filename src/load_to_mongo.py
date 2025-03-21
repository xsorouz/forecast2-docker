# Importation des librairies standard et tierces nécessaires
import os            # Gestion des chemins, répertoires et opérations système
import sys           # Accès aux paramètres et fonctions système (ex: sys.exit)
import json          # Gestion des fichiers au format JSON
import pandas as pd  # Manipulation et analyse de données sous forme de DataFrame
import numpy as np   # Calculs numériques
from datetime import datetime  # Gestion des dates et heures
from dotenv import load_dotenv  # Chargement des variables d'environnement depuis un fichier .env
from loguru import logger       # Gestion avancée des logs
import pymongo       # Connexion à MongoDB Atlas
# Importation pour les annotations de types (facilite la compréhension et la maintenance)
from typing import Optional

# Chargement des variables d'environnement depuis le fichier .env
load_dotenv()

# Définition des répertoires utilisés dans le traitement
INPUT_DIR = "data/processed/"      # Répertoire contenant les fichiers à traiter
OUTPUT_DIR = "data/processed/"     # Répertoire où seront sauvegardées les données traitées
LOG_DIR = "logs/"                  # Répertoire destiné aux fichiers de logs

# Création des répertoires de sortie et de logs s'ils n'existent pas déjà
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Configuration du système de logging avec loguru
CURRENT_TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = os.path.join(LOG_DIR, f"transformation_{CURRENT_TIMESTAMP}.log")
logger.add(
    LOG_FILE,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="10 MB",
    retention="7 days"
)

# Dictionnaire de correspondance pour standardiser les noms de colonnes
# Les clés sont en minuscules pour harmoniser par rapport aux doublons (ex : pressure_hpa vs pressure_hPa)
COLUMN_MAPPING = {
    "timestamp": "timestamp",
    "temperature": "temperature_celsius",
    "pressure": "pressure_hPa",
    "pressure_hpa": "pressure_hPa",  # Gestion du doublon
    "humidity": "humidity_percent",
    "wind_speed": "wind_speed_kph",
    "wind_gust": "wind_gust_kph",
    "wind_direction": "wind_direction",
    "precip_rate": "precip_rate_mm",
    "precip_accum": "precip_accum_mm",
    "solar_radiation": "solar_radiation_wm2",
    "uv_index": "UV_index",
    "visibility": "visibility_m",
    "nebulosity": "nebulosity"
}

def load_json(file_path: str) -> Optional[pd.DataFrame]:
    """
    Charge un fichier JSON et retourne son contenu sous forme de DataFrame pandas.
    Supprime également les lignes et colonnes entièrement vides.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        # Suppression des lignes et colonnes vides
        df.dropna(how="all", inplace=True)
        df.dropna(axis=1, how="all", inplace=True)
        logger.info(f"Fichier {file_path} chargé et nettoyé (lignes/colonnes vides supprimées).")
        return df
    except Exception as e:
        logger.error(f"Erreur lors du chargement du fichier {file_path}: {e}")
        return None

def convert_units(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit les unités de mesure dans le DataFrame.
    Par exemple :
      - Température de Fahrenheit à Celsius
      - Vitesse du vent de mph à kph
      - Pression de inHg à hPa
      - Précipitations de pouces à millimètres
    """
    if "temperature_fahrenheit" in df.columns:
        df["temperature_celsius"] = (df["temperature_fahrenheit"] - 32) * 5 / 9
    if "dew_point_fahrenheit" in df.columns:
        df["dew_point_celsius"] = (df["dew_point_fahrenheit"] - 32) * 5 / 9
    if "wind_speed_mph" in df.columns:
        df["wind_speed_kph"] = df["wind_speed_mph"] * 1.60934
    if "wind_gust_mph" in df.columns:
        df["wind_gust_kph"] = df["wind_gust_mph"] * 1.60934
    if "pressure_inhg" in df.columns:
        df["pressure_hPa"] = df["pressure_inhg"] * 33.8639
    if "precip_rate_in" in df.columns:
        df["precip_rate_mm"] = df["precip_rate_in"] * 25.4
    if "precip_accum_in" in df.columns:
        df["precip_accum_mm"] = df["precip_accum_in"] * 25.4
    logger.info("Conversion des unités effectuée.")
    return df

def standardize_columns(df: pd.DataFrame, source: Optional[str] = None) -> pd.DataFrame:
    """
    Renomme les colonnes du DataFrame selon le mapping défini,
    après avoir converti les noms en minuscules, et ajoute une colonne 'source'.
    Si la source n'est pas précisée, la valeur "unknown" est utilisée.
    """
    # Harmonisation automatique : mise en minuscules des noms de colonnes
    df.columns = df.columns.str.lower()
    # Renommage des colonnes selon le mapping
    df = df.rename(columns=COLUMN_MAPPING)
    # Ajout de la colonne 'source'
    df["source"] = source if source else "unknown"
    logger.info("Standardisation des colonnes terminée.")
    return df

def convert_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit explicitement les colonnes de dates pour éviter les warnings,
    en spécifiant un format explicite.
    """
    if "timestamp" in df.columns:
        try:
            df["timestamp"] = pd.to_datetime(
                df["timestamp"],
                format="%Y-%m-%d %H:%M:%S",
                errors="coerce"
            )
            logger.info("Conversion des timestamps effectuée sans infer_datetime_format.")
        except Exception as e:
            logger.warning(f"Erreur lors de la conversion de 'timestamp': {e}")
    return df


def process_files() -> None:
    """
    Fonction principale de traitement :
      - Recherche des fichiers sources (infoclimat et weatherunderground) basés sur la date du jour.
      - Charge les fichiers trouvés.
      - Convertit les unités, standardise les colonnes et convertit les dates.
      - Fusionne les données de différentes sources, réinitialise les index,
        convertit les dictionnaires en chaînes, et supprime les doublons.
      - Enregistre le résultat dans un fichier JSON.
    """
    # Obtention de la date du jour au format "YYYY_MM_DD"
    today_date = datetime.today().strftime("%Y_%m_%d")
    logger.info(f"Date du jour: {today_date}")

    # Recherche des fichiers pour la source infoclimat
    infoclimat_files = [
        f for f in os.listdir(INPUT_DIR)
        if f.startswith("infoclimat_") and today_date in f and f.endswith(".json")
    ]
    # Recherche des fichiers pour la source weatherunderground
    weatherunderground_files = [
        f for f in os.listdir(INPUT_DIR)
        if f.startswith("weatherunderground_") and today_date in f and f.endswith(".json")
    ]
    
    # Vérification qu'au moins un fichier a été trouvé
    if not infoclimat_files and not weatherunderground_files:
        logger.critical("🚨 Alerte : Aucun fichier détecté pour aujourd'hui pour les sources 'infoclimat' et 'weatherunderground'.")
        sys.exit(1)
    
    dataframes = []
    
    # Traitement des données de la source infoclimat
    if infoclimat_files:
        infoclimat_files.sort(reverse=True)
        infoclimat_file = os.path.join(INPUT_DIR, infoclimat_files[0])
        logger.info(f"✅ Fichier infoclimat sélectionné : {infoclimat_files[0]}")
        df_infoclimat = load_json(infoclimat_file)
        if df_infoclimat is not None:
            df_infoclimat = convert_units(df_infoclimat)
            df_infoclimat = standardize_columns(df_infoclimat, "infoclimat")
            df_infoclimat = convert_dates(df_infoclimat)
            dataframes.append(df_infoclimat)
            logger.info("Traitement complet des données infoclimat effectué.")
    else:
        logger.warning("Aucun fichier infoclimat détecté pour aujourd'hui.")
    
    # Traitement des données de la source weatherunderground
    if weatherunderground_files:
        weatherunderground_files.sort(reverse=True)
        weatherunderground_file = os.path.join(INPUT_DIR, weatherunderground_files[0])
        logger.info(f"✅ Fichier weatherunderground sélectionné : {weatherunderground_files[0]}")
        df_weatherunderground = load_json(weatherunderground_file)
        if df_weatherunderground is not None:
            df_weatherunderground = convert_units(df_weatherunderground)
            df_weatherunderground = standardize_columns(df_weatherunderground, "weatherunderground")
            df_weatherunderground = convert_dates(df_weatherunderground)
            dataframes.append(df_weatherunderground)
            logger.info("Traitement complet des données weatherunderground effectué.")
    else:
        logger.warning("Aucun fichier weatherunderground détecté pour aujourd'hui.")
    
    if not dataframes:
        logger.error("Aucune donnée n'a été chargée. Arrêt du processus.")
        return
    
    # Fusion des DataFrames et réinitialisation des index
    df_combined = pd.concat(dataframes, ignore_index=True)
    df_combined.reset_index(drop=True, inplace=True)
    logger.info("Fusion des DataFrames réalisée et index réinitialisé.")

    # Conversion des colonnes contenant des dictionnaires en chaîne JSON
    for col in df_combined.columns:
        if df_combined[col].apply(lambda x: isinstance(x, dict)).any():
            df_combined[col] = df_combined[col].apply(lambda x: json.dumps(x, sort_keys=True) if isinstance(x, dict) else x)
    logger.info("Conversion des colonnes contenant des dictionnaires en chaînes JSON réalisée.")

    # Suppression des doublons
    df_combined.drop_duplicates(inplace=True)
    logger.info("Suppression des doublons effectuée.")

    # Enregistrement du résultat
    output_file = os.path.join(OUTPUT_DIR, f"weather_data_combined_{today_date}.json")
    df_combined.to_json(output_file, orient="records", indent=4)
    logger.info(f"✅ Données fusionnées et enregistrées dans {output_file}")
 
# --------------------
# Chargement des données dans MongoDB Atlas
# --------------------
# Configuration MongoDB Atlas
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/{MONGO_DB}?retryWrites=true&w=majority"
DATABASE_NAME = "weather_data"
COLLECTION_NAME = "forecasts"

# Connexion à MongoDB Atlas
def connect_to_mongo():
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        logger.info("✅ Connexion réussie à MongoDB Atlas.")
        return collection
    except Exception as e:
        logger.error(f"🚨 Erreur de connexion à MongoDB Atlas: {e}")
        sys.exit(1)

# Chargement et insertion des données dans MongoDB
def load_data_to_mongo():
    collection = connect_to_mongo()
    today_date = datetime.today().strftime("%Y_%m_%d")
    output_file = os.path.join(OUTPUT_DIR, f"weather_data_combined_{today_date}.json")
    
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            records = json.load(f)
        if records:
            result = collection.insert_many(records)
            logger.info(f"✅ {len(result.inserted_ids)} enregistrements insérés dans MongoDB.")
    except Exception as e:
        logger.error(f"🚨 Erreur lors de l'insertion des données dans MongoDB : {e}")

# Point d'entrée principal
if __name__ == "__main__":
    process_files()
    load_data_to_mongo()
