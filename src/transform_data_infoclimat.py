# -----------------------------------------------------------------------------
# Importation des librairies
# -----------------------------------------------------------------------------
import os       # Pour la gestion du système de fichiers (création de dossiers, etc.)
import sys      # Pour utiliser sys.exit() en cas d'erreur fatale
import time     # Pour mesurer la durée d'exécution du script
import argparse # Pour gérer les arguments en ligne de commande
import json     # Pour la sérialisation/désérialisation en JSON
from io import BytesIO  # Pour gérer les fichiers en mémoire (si besoin pour S3)
from typing import Optional, Any, Dict  # Pour ajouter des annotations de type et améliorer la lisibilité
import pandas as pd  # Pour manipuler des DataFrame et effectuer des transformations sur les données
import numpy as np   # Pour les opérations numériques et la gestion des tableaux
from datetime import datetime  # Pour manipuler et formater les dates et heures
from dotenv import load_dotenv  # Pour charger les variables d'environnement depuis un fichier .env
from loguru import logger  # Pour la gestion avancée des logs (flexibilité, rotation, etc.)

# -----------------------------------------------------------------------------
# Chargement des variables d'environnement
# -----------------------------------------------------------------------------
load_dotenv()  # Charge les variables définies dans le fichier .env

# -----------------------------------------------------------------------------
# Définition des répertoires utilisés dans le traitement
# -----------------------------------------------------------------------------
INPUT_DIR = "data/backup/"       # Répertoire contenant les fichiers d'entrée (ici des fichiers JSONL)
OUTPUT_DIR = "data/processed/"   # Répertoire où seront enregistrées les données transformées
LOG_DIR = "logs/"                # Répertoire où seront stockés les fichiers de logs
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
    rotation="10 MB",  # Rotation si le fichier dépasse 10 MB
    retention="7 days"  # Conservation des logs pendant 7 jours
)

# -----------------------------------------------------------------------------
# Définition du mapping pour renommer les colonnes du DataFrame
# -----------------------------------------------------------------------------
COLUMN_MAPPING = {
    "Time": "timestamp",
    "Temperature": "temperature_fahrenheit",
    "Dew Point": "dew_point_fahrenheit",
    "Humidity": "humidity_percent",
    "Speed": "wind_speed_mph",
    "Gust": "wind_gust_mph",
    "Pressure": "pressure_inHg",
    "Precip. Rate.": "precip_rate_in",
    "Precip. Accum.": "precip_accum_in",
    "Solar": "solar_radiation_wm2",
    "Wind": "wind_direction"
}

# -----------------------------------------------------------------------------
# Liste des colonnes critiques attendues après transformation
# -----------------------------------------------------------------------------
CRITICAL_COLUMNS = ["timestamp", "temperature_fahrenheit", "temperature_celsius"]

# -----------------------------------------------------------------------------
# Fonctions auxiliaires pour la conversion d'objets non sérialisables
# -----------------------------------------------------------------------------
def safe_convert(x: Any) -> Any:
    """
    Convertit récursivement les objets non sérialisables (dict, list, ndarray)
    en objets simples pouvant être sérialisés en JSON.
    """
    if isinstance(x, dict):
        return {k: safe_convert(v) for k, v in x.items()}
    elif isinstance(x, list):
        return [safe_convert(v) for v in x]
    elif isinstance(x, np.ndarray):
        return safe_convert(x.tolist())
    else:
        return x

def serialize_value(x: Any) -> Any:
    """
    Sérialise une valeur en chaîne JSON après l'avoir convertie avec safe_convert.
    Permet de transformer des objets complexes (dict, list, ndarray) en chaînes.
    """
    if isinstance(x, (dict, list, np.ndarray)):
        try:
            return json.dumps(safe_convert(x), sort_keys=True)
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sérialisation de {x}: {e}")
            return x
    return x

# -----------------------------------------------------------------------------
# Fonction de chargement des données (format JSONL)
# -----------------------------------------------------------------------------
def load_data(file_path: str) -> Optional[pd.DataFrame]:
    """
    Charge un fichier JSONL et le convertit en DataFrame pandas.
    
    :param file_path: Chemin du fichier JSONL à charger.
    :return: DataFrame ou None en cas d'erreur.
    """
    logger.info(f"📥 Début du chargement du fichier JSONL : {file_path}")
    try:
        df = pd.read_json(file_path, lines=True)
        # Normaliser les données imbriquées sous "_airbyte_data" si présentes
        if "_airbyte_data" in df.columns:
            df = pd.json_normalize(df["_airbyte_data"], errors="ignore")
        logger.info(f"✅ Fichier JSONL chargé avec {len(df)} lignes et {len(df.columns)} colonnes")
        return df
    except Exception as e:
        logger.exception(f"❌ Erreur lors du chargement du fichier {file_path} : {e}")
        return None

# -----------------------------------------------------------------------------
# Extraction des données horaires
# -----------------------------------------------------------------------------
def extract_hourly_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait les observations horaires depuis le fichier JSONL.
    Si la clé 'hourly' existe dans le premier enregistrement, on l'utilise.
    Sinon, on recherche dans les colonnes celles commençant par 'hourly.' (sauf "hourly._params")
    et on les combine en ajoutant le champ 'id_station' pour chaque observation.
    """
    logger.info("⏳ Extraction des données horaires.")
    record = df.iloc[0].to_dict()
    extracted = []
    if "hourly" in record:
        # Cas où 'hourly' est présent comme clé unique
        hourly_data = record["hourly"]
        if isinstance(hourly_data, str):
            try:
                hourly_data = json.loads(hourly_data)
            except Exception as e:
                logger.error(f"❌ Erreur de parsing JSON dans 'hourly': {e}")
                return pd.DataFrame()
        if isinstance(hourly_data, dict):
            for station_id, observations in hourly_data.items():
                if isinstance(observations, list):
                    for entry in observations:
                        if isinstance(entry, dict):
                            entry_copy = entry.copy()
                            entry_copy["id_station"] = station_id
                            extracted.append(entry_copy)
    else:
        logger.warning("⚠️ Clé 'hourly' non trouvée dans le record. Recherche des colonnes commençant par 'hourly.'")
        # Recherche de colonnes dont le nom commence par "hourly." (excluant "hourly._params")
        hourly_cols = [col for col in df.columns if col.startswith("hourly.") and col != "hourly._params"]
        if not hourly_cols:
            logger.warning("⚠️ Aucune colonne 'hourly.*' trouvée.")
        else:
            for col in hourly_cols:
                station_id = col.split(".")[1]
                value = df.at[0, col]
                if isinstance(value, str):
                    try:
                        observations = json.loads(value)
                    except Exception as e:
                        logger.error(f"❌ Erreur de parsing JSON dans la colonne {col}: {e}")
                        continue
                elif isinstance(value, list):
                    observations = value
                else:
                    observations = []
                if isinstance(observations, list):
                    for entry in observations:
                        if isinstance(entry, dict):
                            entry_copy = entry.copy()
                            entry_copy["id_station"] = station_id
                            extracted.append(entry_copy)
    df_hourly = pd.DataFrame(extracted)
    logger.info(f"✅ Extraction terminée : {len(df_hourly)} enregistrements horaires récupérés.")
    return df_hourly

# -----------------------------------------------------------------------------
# Extraction des informations sur les stations
# -----------------------------------------------------------------------------
def extract_stations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait les informations sur les stations depuis la première ligne du fichier JSONL.
    Si la donnée est une chaîne, on la convertit en liste, puis en DataFrame.
    Renomme la colonne 'id' en 'weather_station_id' pour la fusion.
    """
    logger.info("⏳ Extraction des informations sur les stations.")
    record = df.iloc[0].to_dict()
    stations = record.get("stations", None)
    if stations is None:
        logger.warning("⚠️ Aucun champ 'stations' trouvé dans le fichier.")
        return pd.DataFrame()
    if isinstance(stations, str):
        try:
            stations = json.loads(stations)
        except Exception as e:
            logger.error(f"❌ Erreur de parsing JSON dans 'stations': {e}")
            return pd.DataFrame()
    if isinstance(stations, list) and stations:
        df_stations = pd.DataFrame(stations)
        if "id" in df_stations.columns:
            df_stations.rename(columns={"id": "weather_station_id"}, inplace=True)
        logger.info(f"✅ Extraction terminée : {len(df_stations)} stations récupérées.")
        return df_stations
    else:
        logger.warning("⚠️ Les informations sur les stations ne sont pas dans le format attendu.")
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# Extraction des métadonnées
# -----------------------------------------------------------------------------
def extract_metadata(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Extrait les métadonnées depuis la première ligne du fichier JSONL.
    
    :return: Dictionnaire contenant les métadonnées, ou {} si non disponibles.
    """
    logger.info("⏳ Extraction des métadonnées.")
    record = df.iloc[0].to_dict()
    metadata = record.get("metadata", None)
    if metadata is None:
        logger.warning("⚠️ Aucun champ 'metadata' trouvé dans le fichier.")
        return {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception as e:
            logger.error(f"❌ Erreur de parsing JSON dans 'metadata': {e}")
            return {}
    if isinstance(metadata, dict):
        logger.info(f"✅ Extraction des métadonnées terminée : {len(metadata)} éléments récupérés.")
        return metadata
    logger.warning("⚠️ Les métadonnées ne sont pas dans le format attendu.")
    return {}

def add_metadata_from_dict(df: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
    """
    Ajoute les métadonnées en tant que colonnes constantes à chaque ligne du DataFrame.
    """
    if metadata:
        for key, value in metadata.items():
            df[key] = value
        logger.info("✅ Métadonnées ajoutées aux données horaires.")
    else:
        logger.warning("⚠️ Aucune métadonnée à ajouter.")
    return df

# -----------------------------------------------------------------------------
# Conversion des unités pour les données horaires
# -----------------------------------------------------------------------------
def convert_units(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renomme les colonnes du DataFrame selon COLUMN_MAPPING, nettoie les colonnes numériques
    et crée une colonne convertissant la température de Fahrenheit à Celsius si nécessaire.
    """
    logger.info("🔄 Conversion des unités et standardisation des colonnes.")
    
    # Mapping des colonnes
    COLUMN_MAPPING = {
        "dh_utc": "timestamp",  # Correction : dh_utc devient timestamp
        "temperature": "temperature_celsius",  # Correction du nom de colonne
        "pression": "pressure_hPa",
        "humidite": "humidity_percent",
        "vent_moyen": "wind_speed_kph",
        "vent_rafales": "wind_gust_kph",
        "vent_direction": "wind_direction",
        "pluie_3h": "precip_3h_mm",
        "pluie_1h": "precip_1h_mm"
    }

    # Renommer les colonnes
    df = df.rename(columns=COLUMN_MAPPING)

    # Conversion des unités
    numeric_cols = ["temperature_celsius", "pressure_hPa", "humidity_percent",
                    "wind_speed_kph", "wind_gust_kph", "precip_3h_mm", "precip_1h_mm"]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Ajouter température en Fahrenheit si absente
    if "temperature_fahrenheit" not in df.columns and "temperature_celsius" in df.columns:
        df["temperature_fahrenheit"] = (df["temperature_celsius"] * 9/5) + 32

    logger.info(f"📊 Aperçu des valeurs APRÈS conversion :\n{df.head(3)}")
    logger.info("✅ Conversion des unités terminée")

    return df


# -----------------------------------------------------------------------------
# Suppression des lignes incomplètes
# -----------------------------------------------------------------------------
def remove_incomplete_rows(df: pd.DataFrame, threshold: float = 0.6) -> pd.DataFrame:
    """
    Supprime les lignes du DataFrame dont le pourcentage de valeurs manquantes dépasse le seuil spécifié.
    """
    missing_per_row = df.isnull().sum(axis=1) / df.shape[1]
    rows_to_drop = missing_per_row[missing_per_row > threshold].index
    before = len(df)
    df.drop(index=rows_to_drop, inplace=True)
    after = len(df)
    logger.info(f"🗑️ Suppression des lignes trop incomplètes : {before - after} lignes supprimées")
    return df

# -----------------------------------------------------------------------------
# Vérification des valeurs manquantes
# -----------------------------------------------------------------------------
def check_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Affiche et traite les valeurs manquantes : suppression des colonnes entièrement vides
    et imputation par forward fill.
    """
    missing_before = df.isnull().sum()
    logger.info(f"🔍 Valeurs manquantes AVANT transformation :\n{missing_before}")
    empty_columns = missing_before[missing_before == len(df)].index.tolist()
    df.drop(columns=empty_columns, inplace=True, errors='ignore')
    if empty_columns:
        logger.info(f"🗑️ Colonnes supprimées car entièrement vides : {empty_columns}")
    df.ffill(inplace=True)
    missing_after = df.isnull().sum()
    logger.info(f"✅ Valeurs manquantes APRÈS transformation :\n{missing_after}")
    return df

# -----------------------------------------------------------------------------
# Suppression des doublons
# -----------------------------------------------------------------------------
def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Détecte et supprime les doublons dans le DataFrame après avoir converti
    les objets non sérialisables en chaînes.
    """
    for col in df.columns:
        df[col] = df[col].apply(serialize_value)
    before = len(df)
    df.drop_duplicates(inplace=True)
    after = len(df)
    logger.info(f"✅ Suppression des doublons : {before - after} lignes supprimées")
    return df

# -----------------------------------------------------------------------------
# Fusion des données horaires et des informations sur les stations
# -----------------------------------------------------------------------------
def merge_hourly_and_stations(df_hourly: pd.DataFrame, df_stations: pd.DataFrame) -> pd.DataFrame:
    """
    Fusionne le DataFrame des données horaires avec celui des informations sur les stations.
    La jointure se fait sur 'id_station' (dans df_hourly) et 'weather_station_id' (dans df_stations).
    Si le DataFrame des stations est vide, renvoie df_hourly.
    """
    logger.info("⏳ Fusion des données horaires avec les informations sur les stations.")
    if df_hourly.empty:
        logger.warning("⚠️ Aucune donnée horaire à fusionner.")
        return df_hourly
    if df_stations.empty:
        logger.warning("⚠️ Aucune donnée de station à fusionner. Le fichier final contiendra uniquement les données horaires.")
        return df_hourly
    # Vérifier que la colonne 'id_station' existe avant de la convertir
    if "id_station" not in df_hourly.columns:
        logger.error("❌ La colonne 'id_station' est absente dans les données horaires.")
        sys.exit(1)
    df_hourly["id_station"] = df_hourly["id_station"].astype(str)
    df_stations["weather_station_id"] = df_stations["weather_station_id"].astype(str)
    merged_df = pd.merge(df_hourly, df_stations, how="left", left_on="id_station", right_on="weather_station_id")
    logger.info(f"✅ Fusion terminée : {merged_df.shape[0]} enregistrements fusionnés.")
    return merged_df

# -----------------------------------------------------------------------------
# Validation du format pour MongoDB (noms de colonnes en chaînes)
# -----------------------------------------------------------------------------
def validate_mongodb_format(df: pd.DataFrame) -> bool:
    """
    Vérifie que tous les noms de colonnes du DataFrame sont des chaînes,
    condition nécessaire pour l'insertion dans MongoDB.
    """
    logger.info(f"📊 Types de données AVANT validation MongoDB :\n{df.dtypes}")
    for col in df.columns:
        if not isinstance(col, str):
            logger.error(f"❌ Nom de colonne non valide pour MongoDB : {col}")
            return False
    logger.info("✅ Données validées pour MongoDB")
    return True

# -----------------------------------------------------------------------------
# Vérification des colonnes critiques
# -----------------------------------------------------------------------------
def check_critical_columns(df: pd.DataFrame, required: list) -> bool:
    """
    Vérifie que le DataFrame contient toutes les colonnes critiques attendues.
    """
    missing = [col for col in required if col not in df.columns]
    if missing:
        logger.error(f"❌ Colonnes critiques manquantes : {missing}")
        return False
    return True

# -----------------------------------------------------------------------------
# Sauvegarde du fichier final
# -----------------------------------------------------------------------------
def save_data_final(df: pd.DataFrame) -> None:
    """
    Sauvegarde le DataFrame final fusionné en formats Parquet et JSON.
    Le fichier final sera nommé "infoclimat_YYYY_MM_DD", où la date est celle du jour.
    """
    today_str = datetime.today().strftime("%Y_%m_%d")
    final_name = f"infoclimat_{today_str}"
    output_parquet = os.path.join(OUTPUT_DIR, f"{final_name}.parquet")
    output_json = os.path.join(OUTPUT_DIR, f"{final_name}.json")
    logger.info(f"💾 Sauvegarde du fichier final [{final_name}].")
    df.to_parquet(output_parquet, index=False)
    df.to_json(output_json, orient="records", indent=4)
    logger.success(f"✅ Fichier final sauvegardé : {output_parquet}, {output_json}")

# -----------------------------------------------------------------------------
# Fonction principale avec gestion des arguments et mesure des performances
# -----------------------------------------------------------------------------
def main() -> None:
    """
    Pipeline principal pour transformer et fusionner les données Infoclimat :
      - Analyse des arguments (répertoires, seuil).
      - Recherche et sélection du fichier JSONL du jour.
      - Chargement du fichier et extraction des données.
      - Gestion des valeurs manquantes et suppression des doublons.
      - Conversion des unités et standardisation des colonnes.
      - Extraction des informations sur les stations.
      - Extraction des métadonnées et ajout en tant que colonnes constantes.
      - Fusion des données horaires avec les informations sur les stations.
      - Vérification des colonnes critiques.
      - Sauvegarde du fichier final sous le nom "infoclimat_YYYY_MM_DD".
      - Mesure du temps d'exécution.
    """
    parser = argparse.ArgumentParser(description="Transformation du fichier infoclimat (entrée JSONL)")
    parser.add_argument("--input_dir", type=str, default="data/backup/", help="Répertoire d'entrée")
    parser.add_argument("--output_dir", type=str, default="data/processed/", help="Répertoire de sortie")
    parser.add_argument("--log_dir", type=str, default="logs/", help="Répertoire des logs")
    parser.add_argument("--threshold", type=float, default=0.6, help="Seuil de suppression des lignes incomplètes")
    args = parser.parse_args()

    global INPUT_DIR, OUTPUT_DIR, LOG_DIR
    INPUT_DIR = args.input_dir
    OUTPUT_DIR = args.output_dir
    LOG_DIR = args.log_dir

    today_date = datetime.today().strftime("%Y_%m_%d")
    files_to_process = [
        f for f in os.listdir(INPUT_DIR)
        if f.startswith("infoclimat") and today_date in f and f.endswith(".jsonl")
    ]
    if not files_to_process:
        logger.critical("🚨 Aucun fichier 'infoclimat' au format JSONL détecté pour aujourd'hui.")
        sys.exit(1)
    files_to_process.sort(reverse=True)
    latest_file = files_to_process[0]
    logger.info(f"✅ Fichier sélectionné : {latest_file}")

    start_time = time.perf_counter()

    try:
        file_path = os.path.join(INPUT_DIR, latest_file)
        df = load_data(file_path)
        if df is None:
            sys.exit(1)

        # Extraction et transformation des données horaires
        df_hourly = extract_hourly_data(df)
        df_hourly = remove_incomplete_rows(df_hourly, threshold=args.threshold)
        df_hourly = check_missing_values(df_hourly)
        df_hourly = remove_duplicates(df_hourly)
        df_hourly = convert_units(df_hourly)

        # Extraction des informations sur les stations et des métadonnées
        df_stations = extract_stations(df)
        metadata = extract_metadata(df)
        df_hourly = add_metadata_from_dict(df_hourly, metadata)

        # Fusion des données horaires avec les informations sur les stations
        merged_df = merge_hourly_and_stations(df_hourly, df_stations)

        if not check_critical_columns(merged_df, CRITICAL_COLUMNS):
            sys.exit(1)

        if validate_mongodb_format(merged_df):
            save_data_final(merged_df)
    except Exception as e:
        logger.exception(f"❌ Erreur fatale lors du traitement : {e}")
        sys.exit(1)
    else:
        elapsed_time = time.perf_counter() - start_time
        logger.success(f"🎯 Processus terminé avec succès en {elapsed_time:.2f} secondes")

# -----------------------------------------------------------------------------
# Point d'entrée du script
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
