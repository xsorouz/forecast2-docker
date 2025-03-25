# Importation des bibliothèques nécessaires
# - pymongo: pour interagir avec MongoDB
# - loguru: pour la gestion et la configuration des logs
# - dotenv: pour charger les variables d'environnement à partir d'un fichier .env
# - os: pour accéder aux variables d'environnement
from pymongo import MongoClient
from loguru import logger
from dotenv import load_dotenv
import os

# Définition d'une classe pour gérer la connexion à MongoDB
class MongoDBConnection:
    def __init__(self):
        # Initialisation des attributs
        # self.client contiendra l'objet MongoClient une fois la connexion établie
        # self.db contiendra la référence à la base de données utilisée
        self.client = None
        self.db = None

    def connect(self):
        """
        Établit une connexion à MongoDB Atlas en utilisant l'URI défini dans le fichier .env.
        """
        # Charger les variables d'environnement depuis le fichier .env
        load_dotenv()

        # Récupérer l'URI MongoDB à partir de la variable d'environnement MONGO_URI
        mongo_uri = os.getenv("MONGO_URI")

        # Vérifier si l'URI est disponible ; sinon, lever une exception avec un message explicite
        if not mongo_uri:
            raise ValueError("La variable MONGO_URI est manquante dans .env")

        try:
            # Créer un client MongoDB en utilisant l'URI
            self.client = MongoClient(mongo_uri)
            
            # Extraire le nom de la base de données depuis l'URI.
            # Exemple d'URI : "mongodb+srv://user:password@cluster.mongodb.net/nom_de_la_db?retryWrites=true&w=majority"
            # Le nom de la base de données se trouve entre le dernier "/" et le "?" éventuel.
            db_name = mongo_uri.split("/")[-1].split("?")[0]

            # Sélectionner la base de données correspondante sur le client
            self.db = self.client[db_name]

            # Envoyer une commande "ping" pour vérifier la connexion avec le serveur MongoDB
            self.client.admin.command("ping")

            # Si la connexion est réussie, enregistrer un message de succès avec le nom de la base de données
            logger.success(f"✅ Connexion réussie à MongoDB Atlas → base '{db_name}'")
            # Afficher également la liste des collections disponibles dans cette base de données
            logger.info(f"Collections disponibles: {self.db.list_collection_names()}")
        except Exception as e:
            # En cas d'erreur lors de la connexion, enregistrer un message d'erreur détaillé
            logger.error(f"❌ Erreur de connexion MongoDB : {e}")
            # Relancer l'exception pour permettre un traitement ultérieur si nécessaire
            raise

    def close(self):
        # Fermer la connexion avec MongoDB si le client a été initialisé
        if self.client:
            self.client.close()
            logger.info("🔌 Connexion MongoDB fermée.")

# --- Test rapide si on exécute ce fichier directement ---
if __name__ == "__main__":
    # Configurer loguru pour enregistrer les logs dans un fichier
    # Le fichier de log sera "logs/mongo_connection_test.log" et la rotation se fera tous les 500 Ko
    logger.add("logs/mongo_connection_test.log", rotation="500 KB")
    
    # Créer une instance de la classe de connexion MongoDB
    mongo_conn = MongoDBConnection()
    try:
        # Essayer d'établir la connexion à MongoDB
        mongo_conn.connect()
        logger.info("🎉 Test de connexion réussi depuis mongo_connection.py")
    finally:
        # Fermer la connexion, que le test ait réussi ou non
        mongo_conn.close()
