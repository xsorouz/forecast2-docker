# 📦 Importation des bibliothèques nécessaires
from pymongo import MongoClient  # Connexion à MongoDB
import pandas as pd  # Manipulation des données tabulaires
from loguru import logger  # Gestion avancée des logs

# 🔗 Connexion à MongoDB Atlas
# MONGO_URI contient l'URL de connexion à notre base de données hébergée sur Atlas
MONGO_URI = "mongodb+srv://Sorouz:Sorouz&0512@nimbusdb.glwzm.mongodb.net/weather_db"

# 📡 Création d'un client MongoDB et sélection de la base de données et de la collection
client = MongoClient(MONGO_URI)  # Création de la connexion à MongoDB Atlas
db = client["weather_db"]  # Sélection de la base de données
collection = db["stations_data"]  # Sélection de la collection où seront stockées les données

# 📝 Configuration des logs avec Loguru
# On enregistre les logs dans un fichier avec rotation automatique à 1 Mo
logger.add("logs/transform_script.log", rotation="1 MB", level="INFO")


def transform_and_insert():
    """
    Fonction pour transformer les données météorologiques et les insérer dans MongoDB Atlas.
    """
    try:
        # 📡 Données brutes simulées (normalement, elles proviennent d'une API ou d'Airbyte)
        data = [
            {"station_id": "ILAMAD25", "temperature": 22.5, "humidity": 65, "wind_speed": 12},
            {"station_id": "IICHTE19", "temperature": 19.8, "humidity": 70, "wind_speed": 10}
        ]
        
        # 📊 Conversion des données en DataFrame Pandas pour faciliter la manipulation
        df = pd.DataFrame(data)

        # 🔍 Vérification et nettoyage des données
        # Suppression des valeurs aberrantes en température (inférieures à -50 ou supérieures à 60°C)
        df = df[(df["temperature"] > -50) & (df["temperature"] < 60)]
        
        # 📤 Conversion des données en dictionnaire et insertion dans MongoDB
        collection.insert_many(df.to_dict("records"))
        
        # ✅ Log du succès de l'opération
        logger.info("✅ Données insérées avec succès dans MongoDB Atlas !")
        
    except Exception as e:
        # ❌ Log en cas d'erreur
        logger.error(f"❌ Erreur lors de l'insertion des données : {e}")


# 🎯 Exécution du script si c'est le fichier principal
if __name__ == "__main__":
    transform_and_insert()
