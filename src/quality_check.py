# === quality_check.py ===
# Contrôle de qualité des documents MongoDB

from pydantic import BaseModel, ValidationError, conint, confloat

class WeatherDoc(BaseModel):
    station_id: str
    temperature_c: confloat(ge=-50, le=60)
    humidity_pct: conint(ge=0, le=100)
    timestamp_utc: int

logger.add("logs/quality_check.log", rotation="1 MB")

try:
    logger.info("🔍 Démarrage du contrôle de qualité...")
    client = MongoClient(MONGO_URI)
    collection = client[MONGO_DB][COLLECTION_NAME]
    sample = collection.find({"_airbyte_data.station_id": {"$exists": True}}).limit(50)

    valid, invalid = 0, 0

    for doc in sample:
        data = doc.get("_airbyte_data", {})
        try:
            WeatherDoc(**data)
            valid += 1
        except ValidationError as ve:
            invalid += 1
            logger.warning(f"Document invalide : {ve.errors()}")

    logger.success(f"✅ {valid} valides | ❌ {invalid} invalides sur 50")

except Exception as e:
    logger.error(f"❌ Erreur : {e}")
finally:
    client.close()
    logger.info("🔌 Connexion MongoDB fermée.")
