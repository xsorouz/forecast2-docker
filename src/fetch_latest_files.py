# -----------------------------------------------------------------------------
# Importation des librairies
# -----------------------------------------------------------------------------
import os       # Pour la gestion du système de fichiers (création de dossiers, etc.)
import sys      # Pour utiliser sys.exit() en cas d'erreur fatale
import time     # Pour mesurer la durée d'exécution du script
import argparse # Pour gérer les arguments de la ligne de commande
import json     # Pour la sérialisation/désérialisation en JSON
from io import BytesIO  # Pour gérer les fichiers en mémoire (nécessaire pour télécharger depuis S3)
from typing import Optional, Any, Dict  # Pour ajouter des annotations de type et améliorer la lisibilité
import pandas as pd  # Pour manipuler des DataFrame et effectuer des transformations sur les données
import numpy as np   # Pour les opérations numériques et la gestion des tableaux
from datetime import datetime  # Pour manipuler et formater les dates et heures
from dotenv import load_dotenv  # Pour charger des variables d'environnement depuis un fichier .env
from loguru import logger  # Pour une gestion avancée des logs (flexibilité, rotation, etc.)

# -----------------------------------------------------------------------------
# Chargement des variables d'environnement
# -----------------------------------------------------------------------------
load_dotenv()  # Charge les variables définies dans le fichier .env

# -----------------------------------------------------------------------------
# Définition des répertoires utilisés dans le traitement
# -----------------------------------------------------------------------------
INPUT_DIR = "data/backup/"       # Répertoire contenant les fichiers extraits depuis S3
OUTPUT_DIR = "data/processed/"   # Répertoire où seront sauvegardées les données transformées
LOG_DIR = "logs/"                # Répertoire pour les fichiers de logs
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Configuration des logs avec Loguru
# -----------------------------------------------------------------------------
CURRENT_TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Timestamp unique pour le log
LOG_FILE = os.path.join(LOG_DIR, f"extraction_{CURRENT_TIMESTAMP}.log")
logger.remove()  # Supprime les handlers par défaut pour éviter les doublons
logger.add(sys.stdout, level="INFO")  # Affichage dans la console
logger.add(
    LOG_FILE,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="10 MB",  # Rotation automatique si le fichier dépasse 10 MB
    retention="7 days"  # Conservation des logs pendant 7 jours
)

logger.info("🚀 Démarrage du script de téléchargement depuis S3.")

# -----------------------------------------------------------------------------
# Définition des répertoires S3 et des types de fichiers associés
# -----------------------------------------------------------------------------
S3_DIRECTORIES = {
    "infoclimat": "raw_data/s3_forecast_json/",   # Par exemple, données Infoclimat en JSON/JSONL ou Parquet
    "weatherunderground": "raw_data/s3_forecast_excel/"  # Par exemple, données WeatherUnderground en Excel
}

# Répertoire local pour stocker les fichiers extraits
LOCAL_DIR = "data/backup/"

# Date du jour pour la sélection et le nommage des fichiers
TODAY_DATE = datetime.today().strftime("%Y_%m_%d")

# -----------------------------------------------------------------------------
# Initialisation du client S3 avec les identifiants AWS
# -----------------------------------------------------------------------------
import boto3
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = "forecast2-raw-data"  # Nom du bucket S3 contenant les fichiers bruts
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

# -----------------------------------------------------------------------------
# Vérification de la connexion AWS et de l'existence de fichiers locaux
# -----------------------------------------------------------------------------
def check_aws_connection():
    """Vérifie la connexion AWS en listant les buckets disponibles."""
    try:
        response = s3_client.list_buckets()
        logger.info("✅ Connexion réussie à AWS ! Buckets disponibles :")
        for bucket in response["Buckets"]:
            logger.info(f"  - {bucket['Name']}")
    except Exception as e:
        logger.critical(f"🚨 Problème de connexion à AWS : {e}")
        sys.exit(1)

def check_existing_backup():
    """Vérifie si des fichiers existent déjà dans le répertoire local."""
    if os.path.exists(LOCAL_DIR) and os.listdir(LOCAL_DIR):
        logger.warning("⚠️ Des fichiers existent déjà dans data/backup/. Ils seront écrasés par la nouvelle extraction.")

# -----------------------------------------------------------------------------
# Fonction pour obtenir le dernier fichier dans un répertoire S3 donné
# -----------------------------------------------------------------------------
def get_latest_file(s3_directory: str) -> Optional[str]:
    """
    Récupère le fichier le plus récent dans un répertoire S3 et vérifie qu'il correspond à la date du jour.
    """
    logger.info(f"🔍 Recherche du fichier le plus récent dans {s3_directory}...")
    response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=s3_directory)
    if "Contents" not in response:
        logger.error(f"⚠️ Aucun fichier trouvé dans {s3_directory}.")
        return None

    sorted_files = sorted(response["Contents"], key=lambda x: x["LastModified"], reverse=True)
    latest_file = sorted_files[0]["Key"]

    if TODAY_DATE not in latest_file:
        logger.critical(f"🚨 Le fichier {latest_file} ne correspond pas à la date du jour ({TODAY_DATE}).")
        sys.exit(1)
    else:
        logger.info(f"✅ Le fichier du jour {latest_file} est valide.")
    return latest_file

# -----------------------------------------------------------------------------
# Fonction de téléchargement générique pour JSON/Parquet et Excel
# -----------------------------------------------------------------------------
def download_file(s3_key: str, file_type: str) -> Optional[str]:
    """
    Télécharge un fichier depuis S3, le sauvegarde localement, affiche un aperçu et sauvegarde un extrait en texte.
    Le fichier est sauvegardé avec son extension d'origine.
    
    :param s3_key: Chemin du fichier dans S3.
    :param file_type: Préfixe pour nommer le fichier localement (ex: "infoclimat", "weatherunderground").
    :return: Chemin local du fichier téléchargé ou None en cas d'erreur.
    """
    logger.info(f"📥 Téléchargement du fichier {s3_key} depuis S3...")
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        file_content = BytesIO(response["Body"].read())

        # Extraire l'extension du fichier
        _, file_extension = os.path.splitext(s3_key)
        local_filename = os.path.join(LOCAL_DIR, f"{file_type}_{TODAY_DATE}{file_extension}")

        if os.path.exists(local_filename):
            logger.warning(f"⚠️ Le fichier {local_filename} existe déjà et sera écrasé.")

        logger.info(f"💾 Sauvegarde du fichier sous {local_filename}...")
        with open(local_filename, "wb") as f:
            f.write(file_content.getvalue())
        logger.info(f"✅ Fichier sauvegardé sous {local_filename}")

        # Chargement et aperçu selon le format
        try:
            if file_extension.lower() == ".parquet":
                df = pd.read_parquet(local_filename)
            elif file_extension.lower() in [".json", ".jsonl"]:
                df = pd.read_json(local_filename, lines=True)
            elif file_extension.lower() in [".xls", ".xlsx"]:
                df = pd.read_excel(local_filename)
            else:
                df = None
            if df is not None:
                logger.info(f"📊 Aperçu du fichier {local_filename} :\n{df.head()}")
                logger.info(f"🔍 Types de données :\n{df.dtypes}")
            else:
                logger.info(f"📄 Aucun aperçu disponible pour le format {file_extension}")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la lecture du fichier pour l'aperçu : {e}")

        # Sauvegarde d'un extrait en format texte
        preview_txt = os.path.join(LOCAL_DIR, f"{file_type}_preview.txt")
        if df is not None:
            df.head(10).to_csv(preview_txt, sep="\t", index=False)
            logger.info(f"📄 Extrait sauvegardé sous {preview_txt}")
        return local_filename
    except Exception as e:
        logger.error(f"❌ Erreur lors du téléchargement du fichier {s3_key} : {e}")
        return None

# -----------------------------------------------------------------------------
# Fonction principale
# -----------------------------------------------------------------------------
def main() -> None:
    """
    Télécharge les fichiers depuis S3 pour les types JSON/Parquet/Excel.
    Vérifie la connexion AWS, l'existence de fichiers locaux, puis pour chaque répertoire S3 défini,
    récupère le fichier le plus récent correspondant à la date du jour et le télécharge.
    """
    logger.info("🚀 Démarrage du processus de téléchargement depuis S3...")
    check_aws_connection()
    check_existing_backup()
    os.makedirs(LOCAL_DIR, exist_ok=True)

    for file_type, s3_directory in S3_DIRECTORIES.items():
        latest_file = get_latest_file(s3_directory)
        if latest_file:
            download_file(latest_file, file_type)

    logger.success("🎯 Processus terminé avec succès !")

if __name__ == "__main__":
    main()
