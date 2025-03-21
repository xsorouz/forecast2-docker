import os
import json
import pandas as pd
from glob import glob
from loguru import logger
from pathlib import Path
import math
from schemas import WeatherObservation
from utils_weather import (
    f_to_c, inhg_to_hpa, mph_to_kmh, in_to_mm, percent_to_float, solar_to_float,
    cardinal_to_degrees, build_full_timestamp, safe_float, clean_column_names
)
import re

def extract_date_from_filename(path: str) -> str:
    filename = Path(path).stem
    match = re.search(r"(\d{4}_\d{2}_\d{2})", filename)
    if match:
        return match.group(1).replace("_", "-")
    else:
        logger.warning("❓ Aucune date trouvée dans le nom du fichier, date par défaut appliquée.")
        return "2024-10-01"


def load_wu_from_airbyte(path: str, station_id: str) -> pd.DataFrame:
    logger.info(f"🔄 Chargement Airbyte WU : {path} (station {station_id})")

    # Lecture ligne à ligne pour éviter les erreurs de format JSONL
    with open(path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    df_raw = pd.DataFrame(records)

    if "_airbyte_data" not in df_raw.columns:
        raise ValueError("🛑 Le champ '_airbyte_data' est manquant dans le fichier.")

    # Extraction des données météo internes
    df = pd.json_normalize(df_raw["_airbyte_data"])
    df = clean_column_names(df)

    # Extraction fiable de la date depuis le nom de fichier
    date_str = extract_date_from_filename(path)

    # Construction du timestamp complet
    df["timestamp_utc"] = df["time"].apply(lambda t: build_full_timestamp(date_str, str(t)))
    df["station_id"] = station_id

    logger.info(f"✅ {len(df)} lignes chargées depuis {station_id}")
    return df



def load_infoclimat_from_airbyte(path: str) -> pd.DataFrame:
    """
    Charge un fichier InfoClimat JSONL exporté via Airbyte,
    extrait les observations (depuis 'hourly') et les métadonnées de station,
    puis les met en forme dans un DataFrame standardisé.
    """
    logger.info(f"🔄 Chargement Airbyte InfoClimat : {path}")
    
    df_raw = pd.read_json(path, lines=True)
    json_data = df_raw["_airbyte_data"].iloc[0]

    stations = {station["id"]: station for station in json_data["stations"]}
    hourly_data = json_data["hourly"]

    records = []

    for station_id, obs_list in hourly_data.items():
        if station_id.startswith("_"):
            logger.debug(f"⏩ Clé ignorée (non station) : {station_id}")
            continue

        station_meta = stations.get(station_id)
        if not station_meta:
            logger.warning(f"⛔ Station inconnue pour l'observation : {station_id}")
            continue

        for obs in obs_list:
            try:
                record = {
                    "station_id": station_id,
                    "station_name": station_meta["name"],
                    "latitude": float(station_meta["latitude"]),
                    "longitude": float(station_meta["longitude"]),
                    "elevation_m": float(station_meta["elevation"]),
                    "source": "infoclimat",
                    "hardware": None,
                    "software": None,
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
                    "cloud_cover_okta": safe_float(obs.get("nebulosite"))
                }
                records.append(record)
            except Exception as e:
                logger.warning(f"⛔ Observation ignorée pour la station {station_id} : {e}")

    logger.info(f"✅ {len(records)} observations extraites depuis InfoClimat")
    return pd.DataFrame(records)



# 📁 Dossiers de travail
RAW_DATA_DIR = Path("data/backup")
PROCESSED_DATA_DIR = Path("data/processed")
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 🗺️ Métadonnées manuelles pour les stations WU
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



# 🔄 Transformation Weather Underground
def process_weather_underground(file_path: str, station_id: str) -> pd.DataFrame:
    logger.info(f"Chargement des données WU depuis {file_path} pour la station {station_id}")
    xls = pd.ExcelFile(file_path)
    dfs = []
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df = df.iloc[1:].copy()
        df = clean_column_names(df)
        df["timestamp_utc"] = df["time"].apply(lambda t: build_full_timestamp(f"2024-10-{sheet[:2]}", str(t)))
        df["station_id"] = station_id
        dfs.append(df)
    df_all = pd.concat(dfs, ignore_index=True)
    logger.info(f"{len(df_all)} lignes traitées pour la station {station_id}")
    return df_all

def clean_wu_dataframe(df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    logger.info("Nettoyage et conversion des unités WU...")
    return pd.DataFrame({
        "station_id": df["station_id"],
        "station_name": meta["station_name"],
        "hardware": meta.get("hardware"),
        "software": meta.get("software"),
        "latitude": meta["latitude"],
        "longitude": meta["longitude"],
        "elevation_m": meta["elevation_m"],
        "timestamp_utc": df["timestamp_utc"],
        "temperature_c": df["temperature"].apply(f_to_c),
        "dew_point_c": df["dew_point"].apply(f_to_c),
        "humidity_pct": df["humidity"].apply(percent_to_float),
        "pressure_hpa": df["pressure"].apply(inhg_to_hpa),
        "wind_speed_kmh": df["speed"].apply(mph_to_kmh),
        "wind_gust_kmh": df["gust"].apply(mph_to_kmh),
        "wind_dir_cardinal": df["wind"],
        "wind_dir_deg": df["wind"].apply(cardinal_to_degrees),
        "precip_mm_1h": df["precip_rate"].apply(in_to_mm),
        "solar_radiation_wm2": df["solar"].apply(solar_to_float),
        "uv_index": df["uv"],
        "source": meta["source"]
    })

# 🔄 Transformation InfoClimat
def process_infoclimat(json_file: str) -> pd.DataFrame:
    logger.info(f"Chargement des données InfoClimat depuis {json_file}")
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    for station in data["stations"]:
        meta = {
                "station_id": station["id"],
                "station_name": station["name"],
                "latitude": float(station["latitude"]),
                "longitude": float(station["longitude"]),
                "elevation_m": float(station["elevation"]),
                "source": "infoclimat",
                "hardware": None,
                "software": None
            }
        for obs in data["hourly"].get(station["id"], []):
            record = {
                **meta,
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
                "source": "infoclimat"
            }
            records.append(record)
    logger.info(f"{len(records)} lignes chargées depuis InfoClimat")
    return pd.DataFrame(records)

# ✅ Validation Pydantic
def validate_records(df: pd.DataFrame) -> list:
    logger.info("Validation Pydantic des observations...")
    validated = []
    for i, row in df.iterrows():
        try:
            cleaned = {k: (None if pd.isna(v) or (isinstance(v, float) and math.isnan(v)) else v) for k, v in row.items()}
            validated.append(WeatherObservation(**cleaned).model_dump())
        except Exception as e:
            logger.warning(f"⛔ Ligne ignorée à l’index {i} : {e}")
    logger.info(f"{len(validated)} lignes validées sur {len(df)}")
    return validated


# 🚀 Script principal
if __name__ == "__main__":
    logger.info("=== DÉMARRAGE DU TRAITEMENT DES DONNÉES MÉTÉO ===")

    # 🔹 Charger et nettoyer les données WU
    wu_all = []
    wu_files = {
        "ILAMAD25": RAW_DATA_DIR / "weather_la_madeleine_2025_03_21.jsonl",
        "IICHTE19": RAW_DATA_DIR / "weather_ichtegem_2025_03_21.jsonl"
    }
    for station_id, file_path in wu_files.items():
        df_raw = load_wu_from_airbyte(str(file_path), station_id)
        df_clean = clean_wu_dataframe(df_raw, WU_METADATA[station_id])
        wu_all.append(df_clean)

    df_wu = pd.concat(wu_all, ignore_index=True)

    # 🔹 Charger InfoClimat
    df_ic = load_infoclimat_from_airbyte(RAW_DATA_DIR / "infoclimat_2025_03_21.jsonl")

    # 🔹 Fusionner les deux sources
    df_all = pd.concat([df_wu, df_ic], ignore_index=True)
    logger.info(f"Fusion finale : {df_all.shape[0]} observations")

    # 🔁 Suppression des doublons
    dups = df_all[df_all.duplicated(subset=["station_id", "timestamp_utc"], keep=False)]
    dups.to_csv("logs/doublons_station_timestamp.csv", index=False)
    logger.info(f"🔍 {dups.shape[0]} lignes en double sauvegardées pour inspection.")

    nb_before = df_all.shape[0]
    df_all.drop_duplicates(subset=["station_id", "timestamp_utc"], inplace=True)
    nb_after = df_all.shape[0]
    logger.info(f"🧹 Suppression des doublons : {nb_before - nb_after} lignes supprimées ({nb_after} restantes)")

    # 📉 Valeurs manquantes
    missing_before = df_all.isna().sum()
    logger.info("📉 Valeurs manquantes AVANT traitement :")
    logger.info(f"\n{missing_before[missing_before > 0]}")

    # 🔎 Types de données
    logger.info("🔍 Vérification des types de données (échantillon) :")
    logger.info(df_all.dtypes)

    # 🧹 Suppression des lignes invalides
    nb_total = df_all.shape[0]
    df_all.dropna(subset=["timestamp_utc"], inplace=True)

    # (Optionnel) Supprimer les lignes où toutes les colonnes météo sont manquantes
    weather_cols = [
        "temperature_c", "dew_point_c", "humidity_pct", "pressure_hpa",
        "wind_speed_kmh", "wind_gust_kmh", "wind_dir_deg",
        "precip_mm_1h", "solar_radiation_wm2", "uv_index", "visibility_m", "cloud_cover_okta"
    ]
    df_all = df_all.dropna(subset=weather_cols, how="all")

    nb_after = df_all.shape[0]
    logger.info(f"🧹 Lignes supprimées avant validation : {nb_total - nb_after} (timestamp ou toutes valeurs météo manquantes)")


    # 🔍 Validation
    df_all = df_all.where(pd.notnull(df_all), None)
    validated_data = validate_records(df_all)

    # 💾 Export
    df_export = pd.DataFrame(validated_data)
    df_export.to_parquet(PROCESSED_DATA_DIR / "final_weather.parquet", index=False)
    df_export.to_json(PROCESSED_DATA_DIR / "final_weather.json", orient="records", lines=True)
   

    logger.success("✅ Export terminé : fichiers Parquet et JSON générés dans /data/processed")

    logger.info("📦 RÉSUMÉ FINAL")
    logger.info(f"- Observations traitées : {df_all.shape[0]}")
    logger.info(f"- Valeurs manquantes (top 5) :\n{df_all.isna().sum().sort_values(ascending=False).head()}")
    logger.success("🎉 Données prêtes pour MongoDB !")
