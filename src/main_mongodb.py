"""
================================================================================
Script de Test et de Démonstration pour les Opérations CRUD sur MongoDB

Ce script a pour but de :
- Se connecter à une base MongoDB via une configuration définie dans un fichier .env.
- Réaliser des opérations CRUD (Création, Lecture, Mise à jour, Suppression) sur une collection.
- Insérer des données de test (relevés météo) avec gestion des doublons.
- Lire, mettre à jour et supprimer ces données de test.
- Vérifier la présence d'un champ spécifique dans les documents pour ensuite exporter
  un sous-ensemble de données vers un fichier CSV, selon un seuil d'humidité défini.
- Fournir un résumé détaillé des opérations réalisées via des logs.

Ce script est principalement destiné à tester et démontrer les fonctionnalités 
d'interaction avec MongoDB et peut servir de base pour des applications plus complexes.
================================================================================
"""


import os                           # Pour interagir avec le système de fichiers
from dotenv import load_dotenv      # Pour charger les variables d'environnement depuis un fichier .env
from loguru import logger           # Pour la gestion des logs et messages d'information

# --- Import des modules de connexion et des fonctions CRUD ---
# La classe MongoDBConnection permet d'établir une connexion à MongoDB Atlas.
from mongo_connection import MongoDBConnection

# Les fonctions CRUD permettent d'insérer, lire, mettre à jour, supprimer des documents
# et d'exporter des données vers un fichier CSV.
from mongo_crud import (
    insert_records,
    read_records,
    update_records,
    delete_records,
    export_to_csv
)

# --- Chargement des variables d'environnement ---
# Charge le contenu du fichier .env afin de rendre disponibles les variables d'environnement
load_dotenv()

# Récupération de la variable d'environnement "MONGO_DB" (optionnelle selon vos besoins)
MONGO_DB = os.getenv("MONGO_DB")

# Définition du nom de la collection utilisée dans la base MongoDB
COLLECTION_NAME = "airbyte_raw_weather_data_json"

# --- Définition des données de test ---
# Ces données simulent des relevés météo et servent à tester les opérations CRUD.
# Elles seront insérées dans la collection et ignorées lors de l'export si elles ne correspondent pas aux critères.
test_data = [
    {
        "station_id": "TEST-STATION-01",
        "station_name": "Station Test",
        "latitude": 50.659,
        "longitude": 3.07,
        "elevation_m": 23.0,
        "timestamp_utc": 1742783640000,
        "temperature_c": 12.94,
        "humidity_pct": 79.0,
        "source": "test_suite"
    },
    {
        "station_id": "TEST-STATION-01",
        "station_name": "Station Test",
        "latitude": 50.659,
        "longitude": 3.07,
        "elevation_m": 23.0,
        "timestamp_utc": 1742783940000,
        "temperature_c": 13.0,
        "humidity_pct": 80.0,
        "source": "test_suite"
    }
]

# --- Fonction principale du script ---
def main():
    """
    Point d'entrée principal du script.
    
    Ce script réalise une série d'opérations sur une collection MongoDB :
    - Connexion à la base de données MongoDB.
    - Récupération de statistiques globales de la collection.
    - Insertion des données de test avec gestion des doublons.
    - Lecture, mise à jour et suppression des documents de test.
    - Vérification de la présence et du type du champ '_airbyte_data.humidity_pct'.
    - Exportation vers CSV des documents répondant à un critère d'humidité.
    - Affichage d'un résumé final des opérations réalisées via des logs.
    """

    # --- Configuration des logs ---
    # Ajoute un fichier de log pour enregistrer les messages d'information et d'erreur.
    # La rotation automatique s'effectue tous les 5 Mo pour limiter la taille du fichier.
    logger.add("logs/weather_db.log", rotation="5 MB")

    # --- Connexion à MongoDB ---
    # Crée une instance de connexion à MongoDB et tente d'établir la connexion.
    mongo_conn = MongoDBConnection()
    try:
        mongo_conn.connect()

        # Sélection de la collection spécifiée dans la base de données MongoDB
        collection = mongo_conn.db[COLLECTION_NAME]
        logger.info(f"🧪 Début des tests CRUD sur la collection : {COLLECTION_NAME}")

        # --- Statistiques globales de la collection ---
        # Compte le nombre total de documents présents dans la collection
        total_docs = collection.count_documents({})
        logger.info(f"📦 {total_docs} documents au total dans la collection.")

        # --- Insertion des données de test ---
        # Insertion des documents de test avec gestion des doublons basée sur "station_id" et "timestamp_utc"
        inserted = insert_records(
            collection,
            test_data,
            unique_keys=["station_id", "timestamp_utc"]
        )
        logger.info(f"✅ {inserted} documents de test insérés.")

        # --- Lecture des documents de test ---
        # Récupère jusqu'à 5 documents où le champ "source" vaut "test_suite"
        test_docs = read_records(collection, {"source": "test_suite"}, limit=5)
        logger.info(f"📖 {len(test_docs)} documents récupérés pour 'test_suite'")
        # Affiche chaque document récupéré pour vérification
        for doc in test_docs:
            logger.debug(doc)

        # --- Mise à jour des documents de test ---
        # Met à jour le champ "station_name" pour tous les documents avec "station_id" égal à "TEST-STATION-01"
        updated = update_records(
            collection,
            {"station_id": "TEST-STATION-01"},
            {"$set": {"station_name": "Station Test Modifiée"}}
        )
        logger.info(f"✏️ {updated} documents mis à jour pour 'TEST-STATION-01'")

        # --- Suppression des documents de test ---
        # Supprime tous les documents dont "station_id" commence par "TEST" (utilisation d'une expression régulière)
        deleted = delete_records(collection, {"station_id": {"$regex": "^TEST"}})
        logger.info(f"🧹 {deleted} documents de test supprimés")

        # --- Vérification pour l'exportation ---
        # Avant d'exporter, vérifier la présence du champ '_airbyte_data.humidity_pct' dans la collection
        logger.info("🔍 Vérification de la présence de '_airbyte_data.humidity_pct'...")
        example = collection.find_one({"_airbyte_data.humidity_pct": {"$exists": True}})
        if not example:
            # Si aucun document ne contient ce champ, l'export ne peut pas être réalisé
            logger.error("❌ Aucun document avec '_airbyte_data.humidity_pct' détecté — export annulé.")
            total_exported = 0
        else:
            # --- Vérification du type du champ '_airbyte_data.humidity_pct' ---
            # Utilisation d'une agrégation pour déterminer le type du champ
            type_check = collection.aggregate([
                {"$project": {"type": {"$type": "$_airbyte_data.humidity_pct"}}},
                {"$group": {"_id": "$type", "count": {"$sum": 1}}}
            ])
            valid_type = False
            # Parcourt les résultats pour vérifier si le champ est de type numérique
            for entry in type_check:
                logger.info(f"🧪 Type détecté pour '_airbyte_data.humidity_pct' : {entry['_id']} ({entry['count']} doc)")
                if entry["_id"] in ["double", "int", "long", "decimal"]:
                    valid_type = True

            # --- Exportation vers CSV si le type est valide ---
            total_exported = 0
            if valid_type:
                # Définition d'une liste de seuils décroissants pour la valeur d'humidité
                humidity_thresholds = [90, 85, 80, 75]
                for threshold in humidity_thresholds:
                    # Tentative d'exporter jusqu'à 50 documents répondant au critère d'humidité
                    export_count = export_to_csv(
                        collection,
                        file_name=f"humid_conditions_gte_{threshold}",
                        query={"_airbyte_data.humidity_pct": {"$gte": threshold}},
                        fields=[
                            "_airbyte_data.station_id",
                            "_airbyte_data.temperature_c",
                            "_airbyte_data.humidity_pct",
                            "_airbyte_data.timestamp_utc"
                        ],
                        limit=50
                    )
                    if export_count > 0:
                        logger.success(
                            f"📤 {export_count} documents exportés avec humidité ≥ {threshold}% → 'humid_conditions_gte_{threshold}.csv'"
                        )
                        total_exported = export_count
                        # Quitte la boucle dès qu'un export réussi est réalisé
                        break

                if total_exported == 0:
                    logger.warning("📭 Aucun document exporté même avec humidité ≥ 75%")
            else:
                logger.error("❌ Le champ '_airbyte_data.humidity_pct' n’est pas de type numérique — export impossible.")

        # --- RÉSUMÉ FINAL DES OPÉRATIONS ---
        logger.info("📊 RÉSUMÉ FINAL DES OPÉRATIONS :")
        logger.info(f"• Total documents : {total_docs}")
        logger.info(f"• Insertion test : {inserted}")
        logger.info(f"• Lecture test : {len(test_docs)}")
        logger.info(f"• Mise à jour test : {updated}")
        logger.info(f"• Suppression test : {deleted}")
        logger.info(f"• Export effectué : {total_exported} lignes exportées")

    except Exception as e:
        # En cas d'erreur critique durant une des opérations, celle-ci est loguée
        logger.error(f"❌ Erreur critique : {e}")

    finally:
        # Indépendamment du succès ou de l'échec des opérations, on ferme toujours la connexion à MongoDB
        mongo_conn.close()
        logger.info("🔌 Connexion MongoDB fermée.")

# --- Point d'entrée du script ---
if __name__ == "__main__":
    main()
