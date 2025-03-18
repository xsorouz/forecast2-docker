# 📦 Importation de la bibliothèque pour interagir avec MongoDB
from pymongo import MongoClient  # Client MongoDB pour se connecter à la base de données

# 🔗 Définition de l'URI de connexion à MongoDB Atlas
# Remplace les identifiants ci-dessous par les tiens si besoin
MONGO_URI = "mongodb+srv://Sorouz:Sorouz&0512@nimbusdb.glwzm.mongodb.net/weather_db"

try:
    # 🛠️ Création du client MongoDB avec l'URI de connexion
    client = MongoClient(MONGO_URI)

    # 📂 Sélection de la base de données 'weather_db'
    db = client["weather_db"]

    # ✅ Affichage d'un message si la connexion réussit
    print("✅ Connexion réussie à MongoDB Atlas !")

    # 📜 Affichage de la liste des bases de données disponibles sur MongoDB Atlas
    print("📂 Bases de données disponibles :", client.list_database_names())

except Exception as e:
    # ❌ Gestion des erreurs si la connexion échoue
    print("❌ Erreur de connexion à MongoDB :", e)
