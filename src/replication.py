from pymongo import MongoClient, ReadPreference
from pprint import pprint
from dotenv import load_dotenv
import os

# Chargement du fichier .env
load_dotenv()

# Connexion à MongoDB Atlas (URL dans .env)
MONGO_URI = os.getenv("MONGO_URI")

# Connexion normale (lecture par défaut sur PRIMARY)
client_default = MongoClient(MONGO_URI)
db = client_default.get_database()

# Connexion avec lecture sur SECONDARY si possible
client_secondary = MongoClient(MONGO_URI, read_preference=ReadPreference.SECONDARY_PREFERRED)
db_secondary = client_secondary.get_database()

# === 1. Affiche le rôle du nœud utilisé (isMaster) ===
print("🔍 Rôle du nœud utilisé (connexion par défaut) :")
is_master = db.command("isMaster")
pprint({"isWritablePrimary": is_master.get("isWritablePrimary"), "host": is_master.get("me")})

# === 2. Lecture depuis secondaire si disponible ===
print("\n📖 Lecture depuis un réplica secondaire (si disponible) :")
try:
    doc = db_secondary["airbyte_raw_weather_data_json"].find_one()
    print("✅ Document récupéré depuis le secondaire (ou primaire si indisponible) :")
    pprint(doc)
except Exception as e:
    print("❌ Erreur de lecture :", e)

# === 3. Infos sur le Replica Set ===
print("\n🛠️  Statut du Replica Set :")
try:
    repl_status = client_default.admin.command("replSetGetStatus")
    for member in repl_status["members"]:
        print(f"• {member['name']} - rôle : {member['stateStr']}")
except Exception as e:
    print("❌ Impossible d’obtenir le statut du Replica Set :", e)

# Fermeture
client_default.close()
client_secondary.close()
