import os
import pymongo
import json
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "weather_data"
COLLECTION_NAME = "forecasts"
PROCESSED_DIR = Path("data/processed/")

# Connexion MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

def load_data_to_mongo():
    """Charge les fichiers transformés dans MongoDB"""
    for file in PROCESSED_DIR.glob("*.jsonl"):
        with open(file, "r") as f:
            records = [json.loads(line) for line in f]

        if records:
            collection.insert_many(records)
            print(f"✅ {len(records)} enregistrements ajoutés depuis {file.name}")

if __name__ == "__main__":
    load_data_to_mongo()
