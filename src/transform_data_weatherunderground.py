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

# -----------------------------------------------------------------------------
# Définition du mapping pour renommer les colonnes du DataFrame
# -----------------------------------------------------------------------------
# Cette variable permet de standardiser les noms de colonnes du fichier source.
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

# Liste des colonnes critiques qui doivent être présentes après transformation
CRITICAL_COLUMNS = ["timestamp", "temperature_fahrenheit", "temperature_celsius"]

# -----------------------------------------------------------------------------
# Fonctions auxiliaires pour la conversion d'objets non sérialisables
# -----------------------------------------------------------------------------
def safe_convert(x: Any) -> Any:
    """
    Convertit récursivement les objets non sérialisables (dict, list, ndarray)
    en objets simples (dict, list) pouvant être sérialisés en JSON.
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
    Sérialise une valeur en chaîne JSON après l'avoir convertie de manière sûre avec safe_convert().
    Cela permet de gérer les objets complexes (dict, list, ndarray) qui ne sont pas directement sérialisables.
    """
    if isinstance(x, (dict, list, np.ndarray)):
        try:
            return json.dumps(safe_convert(x), sort_keys=True)
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sérialisation de {x}: {e}")
            return x
    return x

# -----------------------------------------------------------------------------
# Fonctions de transformation du DataFrame
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
        # Si les données sont imbriquées sous "_airbyte_data", les normaliser
        if "_airbyte_data" in df.columns:
            df = pd.json_normalize(df["_airbyte_data"], errors="ignore")
        logger.info(f"✅ Fichier JSONL chargé avec {len(df)} lignes et {len(df.columns)} colonnes")
        return df
    except Exception as e:
        logger.exception(f"❌ Erreur lors du chargement du fichier {file_path} : {e}")
        return None

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

def check_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Affiche et traite les valeurs manquantes : suppression des colonnes entièrement vides et imputation (forward fill).
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

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Supprime les doublons dans le DataFrame après avoir converti les objets non sérialisables en chaînes.
    """
    for col in df.columns:
        df[col] = df[col].apply(serialize_value)
    
    before = len(df)
    df.drop_duplicates(inplace=True)
    after = len(df)
    logger.info(f"✅ Suppression des doublons : {before - after} lignes supprimées")
    return df

def clean_numeric(value: Any) -> float:
    """
    Nettoie une valeur numérique sous forme de chaîne (en retirant les unités et espaces inutiles) et la convertit en float.
    """
    if isinstance(value, str):
        value = value.replace("°F", "").replace("mph", "").replace("%", "").replace("in", "").replace("w/m²", "").strip()
        try:
            return float(value)
        except ValueError:
            return np.nan
    return value

def convert_units(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renomme les colonnes du DataFrame selon COLUMN_MAPPING, nettoie les colonnes numériques et crée de nouvelles colonnes avec des unités converties.
    """
    # Renommage des colonnes selon le mapping défini globalement
    df = df.rename(columns=COLUMN_MAPPING)
    
    numeric_cols = [
        "temperature_fahrenheit", "dew_point_fahrenheit", "humidity_percent", "solar_radiation_wm2",
        "wind_speed_mph", "wind_gust_mph", "pressure_inHg", "precip_rate_in", "precip_accum_in"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric)
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Création de nouvelles colonnes pour les unités converties (par exemple Fahrenheit -> Celsius)
    if "temperature_fahrenheit" in df.columns:
        df["temperature_celsius"] = (df["temperature_fahrenheit"] - 32) * 5/9
    if "dew_point_fahrenheit" in df.columns:
        df["dew_point_celsius"] = (df["dew_point_fahrenheit"] - 32) * 5/9
    if "wind_speed_mph" in df.columns:
        df["wind_speed_kmh"] = df["wind_speed_mph"] * 1.60934
    if "wind_gust_mph" in df.columns:
        df["wind_gust_kmh"] = df["wind_gust_mph"] * 1.60934
    if "pressure_inHg" in df.columns:
        df["pressure_hpa"] = df["pressure_inHg"] * 33.8639
    if "precip_rate_in" in df.columns:
        df["precip_rate_mm"] = df["precip_rate_in"] * 25.4
    if "precip_accum_in" in df.columns:
        df["precip_accum_mm"] = df["precip_accum_in"] * 25.4

    logger.info(f"📊 Aperçu des valeurs APRÈS conversion :\n{df.head(3)}")
    logger.info("✅ Conversion des unités terminée")
    return df

def add_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute des métadonnées à chaque ligne du DataFrame en fonction du contenu de la colonne '_ab_source_file_url'.
    Si la colonne existe et contient "Madeleine", on utilise les métadonnées de 'La Madeleine', sinon celles d'Ichtegem.
    """
    metadata: Dict[str, Dict[str, Any]] = {
        "La Madeleine": {
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
        "Ichtegem": {
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
    
    if "_ab_source_file_url" in df.columns:
        def get_metadata(row: pd.Series) -> pd.Series:
            station_key = "La Madeleine" if "Madeleine" in row["_ab_source_file_url"] else "Ichtegem"
            return pd.Series(metadata[station_key])
        df_metadata = df.apply(get_metadata, axis=1)
        df = pd.concat([df, df_metadata], axis=1)
    else:
        logger.warning("⚠️ `_ab_source_file_url` non trouvé, ajout des métadonnées par défaut : Ichtegem")
        for col_name, col_value in metadata["Ichtegem"].items():
            df[col_name] = col_value
    logger.info("📌 Métadonnées correctement ajoutées pour chaque ligne.")
    return df

def validate_mongodb_format(df: pd.DataFrame) -> bool:
    """
    Vérifie que tous les noms de colonnes du DataFrame sont des chaînes, condition nécessaire pour l'insertion dans MongoDB.
    """
    logger.info(f"📊 Types de données AVANT validation MongoDB :\n{df.dtypes}")
    for col in df.columns:
        if not isinstance(col, str):
            logger.error(f"❌ Nom de colonne non valide pour MongoDB : {col}")
            return False
    logger.info("✅ Données validées pour MongoDB")
    return True

def check_critical_columns(df: pd.DataFrame, required: list) -> bool:
    """
    Vérifie que le DataFrame contient toutes les colonnes critiques attendues.
    """
    missing = [col for col in required if col not in df.columns]
    if missing:
        logger.error(f"❌ Colonnes critiques manquantes : {missing}")
        return False
    return True

def save_data(df: pd.DataFrame, file_name: str) -> None:
    """
    Sauvegarde le DataFrame transformé en formats Parquet et JSON.
    Le nom de base du fichier est dérivé du fichier d'entrée.
    """
    logger.info(f"📊 Aperçu des données après transformation :\n{df.head(5)}")
    base_name = os.path.splitext(file_name)[0]
    output_parquet = os.path.join(OUTPUT_DIR, base_name + ".parquet")
    output_json = os.path.join(OUTPUT_DIR, base_name + ".json")
    df.to_parquet(output_parquet, index=False)
    df.to_json(output_json, orient="records", indent=4)
    logger.success(f"✅ Données sauvegardées : {output_parquet}, {output_json}")

# -----------------------------------------------------------------------------
# Fonction principale avec gestion des arguments et mesure des performances
# -----------------------------------------------------------------------------
def main() -> None:
    """
    Fonction principale qui orchestre le pipeline de transformation :
      - Analyse des arguments de la ligne de commande.
      - Recherche et sélection du fichier d'entrée.
      - Exécution des étapes de nettoyage, conversion et enrichissement.
      - Vérification que les colonnes critiques sont présentes.
      - Sauvegarde du DataFrame transformé.
      - Mesure et affichage du temps total d'exécution.
    """
    parser = argparse.ArgumentParser(description="Transformation du fichier weatherunderground")
    parser.add_argument("--input_dir", type=str, default="data/backup/", help="Répertoire d'entrée")
    parser.add_argument("--output_dir", type=str, default="data/processed/", help="Répertoire de sortie")
    parser.add_argument("--log_dir", type=str, default="logs/", help="Répertoire des logs")
    parser.add_argument("--threshold", type=float, default=0.6, help="Seuil de suppression des lignes incomplètes")
    args = parser.parse_args()

    global INPUT_DIR, OUTPUT_DIR, LOG_DIR
    INPUT_DIR = args.input_dir
    OUTPUT_DIR = args.output_dir
    LOG_DIR = args.log_dir

    # Recherche du fichier Parquet à traiter dans le répertoire d'entrée, en fonction de la date du jour
    today_date = datetime.today().strftime("%Y_%m_%d")
    files_to_process = [
        f for f in os.listdir(INPUT_DIR)
        if f.startswith("weatherunderground") and today_date in f and f.endswith(".jsonl")
    ]
    if not files_to_process:
        logger.critical("🚨 Alerte : Aucun fichier 'weatherunderground' au format JSONL  détecté pour aujourd'hui.")
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

        df = remove_incomplete_rows(df, threshold=args.threshold)
        df = check_missing_values(df)
        df = convert_units(df)
        df = remove_duplicates(df)
        df = add_metadata(df)

        if not check_critical_columns(df, CRITICAL_COLUMNS):
            sys.exit(1)

        if validate_mongodb_format(df):
            save_data(df, latest_file)
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
