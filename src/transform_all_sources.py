# transform_all_sources.py
# --------------------------------------------------------------------------------
# Ce script télécharge, nettoie, valide et exporte des données météo provenant de
# plusieurs sources (Weather Underground et InfoClimat).
#
# Les étapes principales sont :
#   1. Récupérer les fichiers bruts depuis S3.
#   2. Traiter et nettoyer les données de Weather Underground.
#   3. Traiter les données InfoClimat.
#   4. Fusionner les différentes sources, supprimer les doublons et nettoyer
#      les données consolidées.
#   5. Gérer les valeurs manquantes dans les mesures météo.
#   6. Valider les enregistrements avec Pydantic et exporter les données.
# --------------------------------------------------------------------------------

import os               # Pour interagir avec le système de fichiers
import json             # Pour manipuler les données JSON
import math             # Pour les fonctions mathématiques (ex. math.isnan)
import pandas as pd     # Pour la manipulation de données tabulaires
import awswrangler as wr  # Pour interagir avec S3 en utilisant Pandas
from datetime import datetime  # Pour manipuler les dates et heures
from dotenv import load_dotenv  # Pour charger les variables d'environnement depuis un fichier .env
from loguru import logger       # Pour un logging structuré et coloré
from schemas import WeatherObservation  # Schéma Pydantic pour valider les observations météo
from utils_weather import (  
    # Fonctions utilitaires pour la conversion d'unités et le traitement des données météo
    f_to_c, inhg_to_hpa, mph_to_kmh, in_to_mm, percent_to_float, solar_to_float,
    cardinal_to_degrees, build_full_timestamp, safe_float, clean_column_names
)
import sys

# Configuration du logger pour afficher les logs sur la console et dans un fichier
logger.remove()  # Supprime les handlers par défaut
logger.add(sys.stdout, level="INFO", colorize=True)
logger.add("logs/pipeline.log", level="INFO", rotation="1 MB", enqueue=True)

# =============================================================================
# Chargement des variables d'environnement et définition des constantes
# =============================================================================

# Charge automatiquement les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupération de la région AWS
AWS_REGION = os.getenv("AWS_REGION")

# Configuration des buckets S3 et des préfixes pour les données brutes et transformées
S3_BUCKET = "forecast2-raw-data"
S3_RAW_PREFIX = "backup_data/"
S3_PROCESSED_PREFIX = "data_processed/"

# Répertoire local pour stocker les données transformées
LOCAL_OUTPUT_DIR = "data/processed/"

# Format de la date actuelle pour nommer les fichiers (deux formats sont utilisés)
TODAY_STR = datetime.today().strftime("%Y_%m_%d")       # Exemple : "2025_03_24"
TODAY_STR_DASH = datetime.today().strftime("%Y-%m-%d")    # Exemple : "2025-03-24"

# Création du répertoire de sortie local s'il n'existe pas
os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)

 

# =============================================================================
# Métadonnées des stations Weather Underground
# =============================================================================
# Ces informations sont utilisées pour enrichir et standardiser les données météo provenant de Weather Underground.
WU_METADATA = {
    "ILAMAD25": {
        "station_name": "La Madeleine",
        "latitude": 50.659,
        "longitude": 3.07,
        "elevation_m": 23,
        "source": "weather_underground",
        "hardware": "other",
        "software": "EasyWeatherPro_V5.1.6"
    },
    "IICHTE19": {
        "station_name": "WeerstationBS",
        "latitude": 51.092,
        "longitude": 2.999,
        "elevation_m": 15,
        "source": "weather_underground",
        "hardware": "other",
        "software": "EasyWeatherV1.6.6"
    }
}

# =============================================================================
# Fonctions utilitaires
# =============================================================================

def download_and_rename_from_s3(s3_path: str, file_type: str) -> str:
    """
    Télécharge un fichier JSONL depuis S3 et le renomme en fonction du type de fichier.
    
    Paramètres:
        s3_path (str): Chemin complet du fichier sur S3.
        file_type (str): Identifiant/type de fichier pour le renommage.
        
    Retour:
        str: Chemin local du fichier sauvegardé.
    """
    # Log de l'opération de téléchargement
    logger.info(f"📥 Téléchargement depuis S3 : {s3_path}")
    
    # Lecture du fichier JSONL depuis S3
    obj = wr.s3.read_json(path=s3_path, lines=True)
    
    # Construction du nom de fichier avec le type et la date du jour
    target_name = f"{file_type}_{TODAY_STR}.jsonl"
    local_path = os.path.join(LOCAL_OUTPUT_DIR, target_name)
    
    # Sauvegarde du DataFrame au format JSONL localement, avec une configuration pour l'encodage
    obj.to_json(local_path, orient="records", lines=True, force_ascii=False)
    
    # Log de succès de l'exportation
    logger.success(f"💾 Fichier renommé et sauvegardé sous {local_path}")
    return local_path


def find_latest_s3_file(prefix: str, fallback_days: int = 7) -> str:
    """
    Recherche le fichier le plus récent sur S3 pour un préfixe donné, en cherchant pour aujourd'hui ou en remontant un certain nombre de jours.
    
    Paramètres:
        prefix (str): Préfixe du dossier sur S3 dans lequel chercher le fichier.
        fallback_days (int): Nombre de jours en arrière à essayer si aucun fichier n'est trouvé pour la date actuelle.
    
    Retour:
        str: Chemin complet du fichier le plus récent trouvé.
        
    Exception:
        FileNotFoundError: Si aucun fichier n'est trouvé dans le délai spécifié.
    """
    # Construction du chemin complet sur S3 en combinant le bucket et le préfixe
    full_prefix = f"s3://{S3_BUCKET}/{prefix}"
    
    # Récupération de la liste des fichiers dans le répertoire S3
    files = wr.s3.list_objects(full_prefix)
    
    # Si aucun fichier n'est trouvé, on lève une exception
    if not files:
        raise FileNotFoundError(f"Aucun fichier trouvé dans {full_prefix}")
    
    # Parcours des jours récents jusqu'au nombre de jours de repli (fallback_days)
    for i in range(fallback_days + 1):
        # Calcul de la date à essayer (au format YYYY_MM_DD)
        date_try = (datetime.today() - pd.Timedelta(days=i)).strftime("%Y_%m_%d")
        # Filtrage des fichiers contenant la date recherchée dans leur nom
        matching_files = [f for f in files if date_try in f]
        if matching_files:
            # Tri des fichiers pour obtenir le plus récent et sélection du premier
            latest_file = sorted(matching_files, reverse=True)[0]
            logger.info(f"✅ Fichier trouvé pour {prefix} : {latest_file}")
            return latest_file
    
    # Si aucun fichier n'a été trouvé après le nombre de jours spécifié, on lève une exception
    raise FileNotFoundError(f"Aucun fichier trouvé dans {prefix} pour les {fallback_days} derniers jours.")


def clean_wu_dataframe(df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    """
    Nettoie et convertit les unités des données météo issues de Weather Underground.
    
    Paramètres:
        df (pd.DataFrame): DataFrame brut contenant les données téléchargées.
        meta (dict): Métadonnées associées à la station (nom, latitude, etc.).
    
    Retour:
        pd.DataFrame: DataFrame nettoyé et enrichi avec les conversions d'unités.
    """
    logger.info("🧽 Nettoyage et conversion des unités WU")
    # Création d'un nouveau DataFrame avec les colonnes standardisées et les unités converties
    return pd.DataFrame({
        "station_id": df["station_id"],                            # ID de la station
        "station_name": meta["station_name"],                      # Nom de la station (issu des métadonnées)
        "hardware": meta["hardware"],                              # Type de matériel utilisé
        "software": meta["software"],                              # Version du logiciel utilisé
        "latitude": meta["latitude"],                              # Latitude de la station
        "longitude": meta["longitude"],                            # Longitude de la station
        "elevation_m": meta["elevation_m"],                        # Élévation en mètres
        "timestamp_utc": df["timestamp_utc"],                      # Timestamp en UTC
        "temperature_c": df["temperature"].apply(f_to_c),          # Température convertie de Fahrenheit en Celsius
        "dew_point_c": df["dew_point"].apply(f_to_c),              # Point de rosée converti de Fahrenheit en Celsius
        "humidity_pct": df["humidity"].apply(percent_to_float),    # Humidité convertie en pourcentage
        "pressure_hpa": df["pressure"].apply(inhg_to_hpa),         # Pression convertie de inHg en hPa
        "wind_speed_kmh": df["speed"].apply(mph_to_kmh),           # Vitesse du vent convertie de mph en km/h
        "wind_gust_kmh": df["gust"].apply(mph_to_kmh),             # Rafale de vent convertie de mph en km/h
        "wind_dir_cardinal": df["wind"],                           # Direction du vent sous forme de cardinal (ex: N, NE)
        "wind_dir_deg": df["wind"].apply(cardinal_to_degrees),     # Conversion de la direction du vent en degrés
        "precip_mm_1h": df["precip_rate"].apply(in_to_mm),         # Précipitations converties de pouces à millimètres pour 1h
        "solar_radiation_wm2": df["solar"].apply(solar_to_float),   # Radiation solaire convertie en W/m²
        "uv_index": df["uv"],                                      # Indice UV
        "source": meta["source"]                                   # Source des données (Weather Underground)
    })

def load_infoclimat_from_file(path: str) -> pd.DataFrame:
    """
    Charge et transforme un fichier JSONL provenant d'InfoClimat.
    Le fichier est généré via Airbyte et contient des données encapsulées dans un champ "_airbyte_data".
    
    Paramètres:
        path (str): Chemin local du fichier InfoClimat.
    
    Retour:
        pd.DataFrame: DataFrame contenant les observations météo transformées.
    """
    logger.info(f"📥 Chargement InfoClimat depuis {path}")
    
    # Chargement du fichier JSONL en DataFrame
    df_raw = pd.read_json(path, lines=True)
    
    # Extraction des données encapsulées dans la colonne "_airbyte_data"
    data = df_raw["_airbyte_data"].iloc[0]
    
    # Construction d'un dictionnaire de stations pour un accès rapide aux métadonnées par station_id
    stations = {s["id"]: s for s in data["stations"]}
    
    # Extraction des données horaires
    hourly = data["hourly"]
    records = []
    
    # Parcours de chaque station dans les données horaires
    for station_id, observations in hourly.items():
        # Ignorer les clés commençant par "_" (données internes ou inutiles)
        if station_id.startswith("_"):
            continue
        
        # Récupération des métadonnées pour la station en cours
        meta = stations.get(station_id)
        if not meta:
            continue
        
        # Parcours de chaque observation horaire
        for obs in observations:
            records.append({
                "station_id": station_id,
                "station_name": meta["name"],
                "latitude": float(meta["latitude"]),
                "longitude": float(meta["longitude"]),
                "elevation_m": float(meta["elevation"]),
                "hardware": None,  # Info non disponible pour InfoClimat
                "software": None,  # Info non disponible pour InfoClimat
                "timestamp_utc": pd.to_datetime(obs["dh_utc"]),
                "temperature_c": safe_float(obs.get("temperature")),
                "dew_point_c": safe_float(obs.get("point_de_rosee")),
                "humidity_pct": safe_float(obs.get("humidite")),
                "pressure_hpa": safe_float(obs.get("pression")),
                "wind_speed_kmh": safe_float(obs.get("vent_moyen")),
                "wind_gust_kmh": safe_float(obs.get("vent_rafales")),
                "wind_dir_deg": safe_float(obs.get("vent_direction")),
                "precip_mm_1h": safe_float(obs.get("pluie_1h")),
                "visibility_m": safe_float(obs.get("visibilite")),
                "cloud_cover_okta": safe_float(obs.get("nebulosite")),
                "source": "infoclimat"  # Indique la source des données
            })
    # Transformation de la liste de dictionnaires en DataFrame
    return pd.DataFrame(records)

def validate_records(df: pd.DataFrame) -> list:
    """
    Valide chaque ligne du DataFrame en utilisant le modèle Pydantic WeatherObservation.
    Si une ligne ne passe pas la validation, elle est ignorée avec un avertissement.
    
    Paramètres:
        df (pd.DataFrame): DataFrame contenant les observations à valider.
    
    Retour:
        list: Liste des enregistrements validés (sous forme de dictionnaires).
    """
    logger.info("🔎 Validation Pydantic des données")
    validated = []
    # Itération sur chaque ligne du DataFrame
    for i, row in df.iterrows():
        try:
            # Création d'un dictionnaire en nettoyant les valeurs NaN (ou équivalents)
            cleaned = {
                k: (None if pd.isna(v) or (isinstance(v, float) and math.isnan(v)) else v)
                for k, v in row.items()
            }
            # Validation de la ligne à l'aide du schéma WeatherObservation et ajout au résultat
            validated.append(WeatherObservation(**cleaned).model_dump())
        except Exception as e:
            # En cas d'erreur de validation, log de l'erreur et passage à la ligne suivante
            logger.warning(f"Ligne ignorée ({i}) : {e}")
    return validated

 
def resolve_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Supprime uniquement les doublons stricts (identiques sur toutes les colonnes).
    Ne fusionne pas les données partiellement différentes à timestamp égal.
    """
    initial_len = len(df)
    df_cleaned = df.drop_duplicates(keep="first").copy()
    df_cleaned.reset_index(drop=True, inplace=True)
    logger.info(f"🧠 Doublons stricts supprimés : {initial_len - len(df_cleaned)} lignes supprimées.")
    return df_cleaned


def export_results(validated_data: list):
    """
    Exporte uniquement les données validées au format Parquet et JSON
    
    Paramètres:
        validated_data (list): Liste des enregistrements validés par Pydantic
    """
    # Conversion en DataFrame
    df = pd.DataFrame(validated_data)
    
    # 1. Export Parquet
    parquet_path = os.path.join(LOCAL_OUTPUT_DIR, "final_weather.parquet")
    df.to_parquet(parquet_path, index=False)
    
    # 2. Export JSON (ligne par ligne)
    json_path = os.path.join(LOCAL_OUTPUT_DIR, "final_weather.json")
    df.to_json(json_path, orient="records", lines=True, force_ascii=False)
    
    # 3. Export vers S3 (optionnel)
    s3_json_path = f"s3://{S3_BUCKET}/{S3_PROCESSED_PREFIX}final_weather_{TODAY_STR}.json"
    wr.s3.to_json(df, path=s3_json_path, orient="records", lines=True)
    
    # Logging
    logger.success(f"✅ Export Parquet : {parquet_path}")
    logger.success(f"✅ Export JSON : {json_path}")
    logger.success(f"📤 Export S3 JSON : {s3_json_path}")

def main():
    """
    Fonction principale orchestrant le traitement complet des données météo.
    
    Étapes :
      1. Récupération des fichiers bruts depuis S3.
      2. Traitement et nettoyage des données de Weather Underground.
      3. Traitement des données InfoClimat.
      4. Fusion des sources, déduplication et nettoyage des données consolidées.
      5. Traitement des valeurs manquantes dans les mesures météo.
      6. Validation des enregistrements (via Pydantic) et export final.
    """
    logger.info("=== 🔁 TRAITEMENT DES DONNÉES MÉTÉO - DIRECT S3 ===")

    # -----------------------------------------------------------------------------
    # Étape 1 : Récupération des fichiers depuis S3
    # -----------------------------------------------------------------------------
    # On récupère les chemins S3 les plus récents pour chaque source,
    # puis on télécharge et renomme ces fichiers localement.
    s3_keys = {
        "weather_la_madeleine": find_latest_s3_file(f"{S3_RAW_PREFIX}weather_la_madeleine/"),
        "weather_ichtegem":      find_latest_s3_file(f"{S3_RAW_PREFIX}weather_ichtegem/"),
        "infoclimat":             find_latest_s3_file(f"{S3_RAW_PREFIX}infoclimat/")
    }
    local_files = {
        "ILAMAD25": download_and_rename_from_s3(s3_keys["weather_la_madeleine"], "weather_la_madeleine"),
        "IICHTE19": download_and_rename_from_s3(s3_keys["weather_ichtegem"], "weather_ichtegem"),
        "infoclimat": download_and_rename_from_s3(s3_keys["infoclimat"], "infoclimat")
    }

    # -----------------------------------------------------------------------------
    # Étape 2 : Traitement des données Weather Underground
    # -----------------------------------------------------------------------------
    # Pour chaque station Weather Underground, on :
    #   - Charge le fichier JSONL,
    #   - Normalise les données imbriquées (_airbyte_data),
    #   - Nettoie les noms de colonnes,
    #   - Construit un timestamp complet,
    #   - Ajoute l'identifiant de station,
    #   - Convertit et nettoie les mesures.
    wu_dfs = []
    for station_id in ["ILAMAD25", "IICHTE19"]:
        df_raw = pd.read_json(local_files[station_id], lines=True)
        df_raw = pd.json_normalize(df_raw["_airbyte_data"])

        logger.info(f"🔎 {station_id} → {df_raw.shape[0]} lignes avant nettoyage")
        logger.info(f"🧾 Aperçu ({station_id}) :\n{df_raw.head(3).to_string(index=False)}")

        df_raw = clean_column_names(df_raw)
        # Construction du timestamp complet en associant la date et l'heure
        df_raw["timestamp_utc"] = df_raw["time"].apply(lambda t: build_full_timestamp(TODAY_STR_DASH, str(t)))
        df_raw["station_id"] = station_id
        # Nettoyage et conversion des unités pour cette station
        df_clean = clean_wu_dataframe(df_raw, WU_METADATA[station_id])

        logger.info(f"✅ {station_id} → {df_clean.shape[0]} lignes après nettoyage")
        logger.info(f"🧾 Exemple nettoyé ({station_id}) :\n{df_clean.head(3).to_string(index=False)}")

        wu_dfs.append(df_clean)
    # Fusion des données Weather Underground
    df_wu = pd.concat(wu_dfs, ignore_index=True)

    # -----------------------------------------------------------------------------
    # Étape 3 : Traitement des données InfoClimat
    # -----------------------------------------------------------------------------
    # Chargement et transformation des données InfoClimat à partir du fichier local.
    df_ic = load_infoclimat_from_file(local_files["infoclimat"])

    logger.info(f"🔎 InfoClimat → {df_ic.shape[0]} lignes chargées")
    logger.info(f"🧾 Exemple InfoClimat :\n{df_ic.head(3).to_string(index=False)}")

    # -----------------------------------------------------------------------------
    # Étape 4 : Fusion, déduplication et nettoyage global
    # -----------------------------------------------------------------------------
    # Fusion des sources Weather Underground et InfoClimat
    df_all = pd.concat([df_wu, df_ic], ignore_index=True)
    logger.info(f"📦 Fusion initiale : {df_all.shape[0]} lignes consolidées.")
    logger.info(f"🧾 Exemple fusionné :\n{df_all.head(3).to_string(index=False)}")

    # Identification et export des doublons (mêmes station_id et timestamp)
    dups_mask = df_all.duplicated(subset=["station_id", "timestamp_utc"], keep=False)
    df_all[dups_mask].to_csv("logs/doublons_detectes.csv", index=False)
    logger.info(f"🔍 {dups_mask.sum()} lignes avec timestamp partagé (voir logs/doublons_detectes.csv)")

    # Suppression des doublons stricts via une fonction dédiée
    before_dedup = df_all.shape[0]
    df_all = resolve_duplicates(df_all)
    # Vérification manuelle (peut être retirée ensuite)
    assert df_all.duplicated().sum() == 0, "❌ Des doublons stricts subsistent après resolve_duplicates()"

    logger.success(f"✅ Doublons stricts supprimés : {before_dedup - df_all.shape[0]} lignes")

    # Suppression des lignes dépourvues de timestamp
    before_ts = df_all.shape[0]
    df_all.dropna(subset=["timestamp_utc"], inplace=True)
    logger.info(f"🧹 {before_ts - df_all.shape[0]} lignes supprimées (timestamp manquant)")

    # -----------------------------------------------------------------------------
    # Étape 5 : Traitement des valeurs manquantes dans les mesures météo
    # -----------------------------------------------------------------------------
    weather_cols = [
        "temperature_c", "dew_point_c", "humidity_pct", "pressure_hpa",
        "wind_speed_kmh", "wind_gust_kmh", "wind_dir_deg",
        "precip_mm_1h", "solar_radiation_wm2", "uv_index", "visibility_m", "cloud_cover_okta"
    ]
    # Affichage des statistiques de valeurs manquantes par colonne
    nan_stats = df_all[weather_cols].isna().sum()
    logger.info("📉 Valeurs manquantes détectées :")
    for col, nb in nan_stats.items():
        logger.info(f"   - {col} : {nb} manquantes")

    # Remplissage automatique pour certaines colonnes spécifiques (stratégies définies)
    FILL_STRATEGIES = {
        "wind_dir_deg": 0,
        "wind_dir_cardinal": "N",
        "uv_index": 0,
        "solar_radiation_wm2": 0,
        "visibility_m": df_all["visibility_m"].median(),
        "cloud_cover_okta": 0,
        "wind_gust_kmh": df_all["wind_gust_kmh"].median(),
        "precip_mm_1h": 0
    }
    for col, val in FILL_STRATEGIES.items():
        if col in df_all.columns:
            df_all[col] = df_all[col].fillna(val)
            logger.info(f"🔧 {col} rempli automatiquement → {val}")

    # Pour toutes les colonnes numériques de mesures météo encore manquantes, on remplit avec la médiane
    for col in df_all.select_dtypes(include="number").columns:
        if col in weather_cols and df_all[col].isna().sum() > 0:
            med = df_all[col].median()
            df_all[col] = df_all[col].fillna(med)
            logger.info(f"🔧 {col} rempli par médiane : {med:.2f}")

    # Suppression des lignes qui n'ont aucune donnée dans aucune des colonnes météo
    before_clean = df_all.shape[0]
    df_all.dropna(subset=weather_cols, how="all", inplace=True)
    logger.info(f"🗑️ {before_clean - df_all.shape[0]} lignes supprimées (aucune donnée météo)")

    logger.success(f"📊 Nettoyage finalisé : {df_all.shape[0]} lignes, {df_all.shape[1]} colonnes")

    # -----------------------------------------------------------------------------
    # Étape 6 : Validation et export
    # -----------------------------------------------------------------------------
    # Remplacer les NaN par None pour compatibilité avec Pydantic
    df_all = df_all.where(pd.notnull(df_all), None)

    # Conversion de wind_dir_deg en entier pour correspondre au schéma Pydantic
    if "wind_dir_deg" in df_all.columns:
        df_all["wind_dir_deg"] = df_all["wind_dir_deg"].apply(
            lambda x: int(round(x)) if isinstance(x, float) and not pd.isna(x) else x
        )
        logger.info("🔧 wind_dir_deg converti en int pour Pydantic")

    # Validation de chaque enregistrement via Pydantic et export des résultats
    validated = validate_records(df_all)
    export_results(validated)

    logger.success("🎯 Données météo prêtes pour MongoDB !")
 

if __name__ == "__main__":
    main()
