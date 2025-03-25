# === src/quality_check.py ===
# Contrôle qualité des documents stockés dans MongoDB (schema météo)

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel, ValidationError, conint, confloat

# ─────────────────────────────────────────────
# 📌 Chargement des variables d'environnement
# ─────────────────────────────────────────────
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

if not all([MONGO_URI, MONGO_DB, COLLECTION_NAME]):
    logger.error("❌ Configuration MongoDB incomplète. Vérifiez votre fichier .env (MONGO_URI, MONGO_DB, COLLECTION_NAME).")
    sys.exit(1)

# ─────────────────────────────────────────────
# 📋 Définition du schéma Pydantic attendu
# ─────────────────────────────────────────────
class WeatherDoc(BaseModel):
    station_id: str
    temperature_c: confloat(ge=-50, le=60)
    humidity_pct: conint(ge=0, le=100)
    timestamp_utc: int

# ─────────────────────────────────────────────
# 📁 Préparation du dossier et du fichier log
# ─────────────────────────────────────────────
if not os.path.exists("logs"):
    os.makedirs("logs")

logger.add("logs/quality_check.log", rotation="1 MB")

# ─────────────────────────────────────────────
# 🚀 Fonction principale de contrôle qualité
# ─────────────────────────────────────────────
def main():
    try:
        logger.info("🔍 Démarrage du contrôle qualité des documents MongoDB...")

        # Connexion à MongoDB
        client = MongoClient(MONGO_URI)
        collection = client[MONGO_DB][COLLECTION_NAME]

        # Chargement d'un échantillon de 50 documents
        sample = collection.find().limit(50)

        valid_count = 0
        invalid_count = 0

        for doc in sample:
            data = doc.get("_airbyte_data", {})  # Données utiles extraites
            try:
                # Validation du document avec Pydantic
                WeatherDoc(**data)
                valid_count += 1
            except ValidationError as ve:
                invalid_count += 1
                logger.warning(f"⚠️ Document invalide (ID: {doc.get('_id')}): {ve.errors()}")

        # Résumé
        logger.success(f"🎯 Contrôle terminé : ✅ {valid_count} valides | ❌ {invalid_count} invalides (sur 50 documents)")

    except Exception as e:
        logger.exception(f"💥 Erreur inattendue : {e}")

    finally:
        client.close()
        logger.info("🔌 Connexion MongoDB fermée.")

# ─────────────────────────────────────────────
# 🎯 Lancement du script
# ─────────────────────────────────────────────
if __name__ == '__main__':
    main()
