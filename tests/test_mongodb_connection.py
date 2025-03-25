# 📦 Importation de la bibliothèque pour interagir avec MongoDB
from pymongo import MongoClient  # Client MongoDB pour se connecter à la base de données
import os               # Pour interagir avec le système de fichiers
from dotenv import load_dotenv  # Pour charger les variables d'environnement depuis un fichier .env

# =============================================================================
# Chargement des variables d'environnement et définition des constantes
# =============================================================================

# Charge automatiquement les variables d'environnement depuis le fichier .env
load_dotenv()

# 🔗 Définition de l'URI de connexion à MongoDB Atlas
MONGO_URI = os.getenv("MONGO_URI")

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
