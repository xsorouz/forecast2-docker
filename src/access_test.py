# === access_test.py ===
# Mesure du temps de connexion et de requête MongoDB

import os
import time
from pymongo import MongoClient
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
COLLECTION_NAME = "airbyte_raw_weather_data_json"

logger.add("logs/access_test.log", rotation="1 MB")

try:
    logger.info("🔍 Début du test de performance MongoDB Atlas")

    start_conn = time.perf_counter()
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db[COLLECTION_NAME]
    end_conn = time.perf_counter()

    logger.success(f"✅ Connexion établie en {end_conn - start_conn:.3f} secondes")

    # Requête spécifique pour test (ville/date ou autre critère)
    logger.info("🔢 Lancement de la requête de test...")
    start_query = time.perf_counter()
    results = list(collection.find({"_airbyte_data.station_name": "La Madeleine"}).limit(10))
    end_query = time.perf_counter()

    logger.success(f"📅 Requête exécutée en {end_query - start_query:.3f} secondes")
    logger.info(f"📊 {len(results)} documents retournés.")

except Exception as e:
    logger.error(f"❌ Erreur lors du test de connexion : {e}")
finally:
    client.close()
    logger.info("🔌 Connexion MongoDB fermée.")