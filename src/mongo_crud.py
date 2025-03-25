# Importation des modules nécessaires
from loguru import logger                   # Pour la journalisation (logs)
from pymongo.collection import Collection    # Pour typer les objets de collection MongoDB
import pandas as pd                          # Pour la manipulation des données et l'export en CSV
import os                                    # Pour les opérations système (création de dossiers, chemins, etc.)

# === INSERTION avec gestion des doublons ===
def insert_records(collection: Collection, records: list, unique_keys: list = None) -> int:
    """
    Insère des documents dans une collection MongoDB.
    Possibilité d'éviter les doublons en vérifiant certaines clés uniques.
    
    Paramètres :
    - collection: La collection MongoDB dans laquelle insérer les documents.
    - records: Liste de dictionnaires représentant les documents à insérer.
    - unique_keys: Liste optionnelle de clés à vérifier pour détecter les doublons.
    
    Retourne :
    - Le nombre de documents insérés.
    """
    # Vérifier si la liste de documents est vide
    if not records:
        logger.warning("❗ Aucun document à insérer.")
        return 0

    inserted_count = 0  # Compteur pour le nombre de documents insérés

    try:
        # Si des clés uniques sont définies, insérer document par document avec vérification
        if unique_keys:
            for doc in records:
                # Création d'un filtre basé sur les clés uniques pour vérifier l'existence d'un doublon
                filter_query = {key: doc.get(key) for key in unique_keys}
                # Si aucun document ne correspond au filtre, on insère le document
                if not collection.find_one(filter_query):
                    collection.insert_one(doc)
                    inserted_count += 1
                else:
                    # Si le document existe déjà, on loggue que le doublon est ignoré
                    logger.debug(f"⏩ Doublon ignoré : {filter_query}")
            logger.success(f"✅ {inserted_count} documents insérés sans doublons.")
        else:
            # Si aucune clé unique n'est fournie, insérer tous les documents en une seule opération
            result = collection.insert_many(records)
            inserted_count = len(result.inserted_ids)
            logger.success(f"✅ {inserted_count} documents insérés.")
        return inserted_count

    except Exception as e:
        # En cas d'erreur lors de l'insertion, enregistrer l'erreur et relancer l'exception
        logger.error(f"❌ Erreur d'insertion : {e}")
        raise

# === LECTURE ===
def read_records(collection: Collection, query: dict = {}, limit: int = 5) -> list:
    """
    Récupère des documents depuis une collection MongoDB selon un filtre et une limite.
    
    Paramètres :
    - collection: La collection MongoDB à interroger.
    - query: Dictionnaire définissant les critères de filtrage (par défaut, aucun filtre).
    - limit: Nombre maximum de documents à récupérer (par défaut 5).
    
    Retourne :
    - Une liste contenant les documents récupérés.
    """
    try:
        # Exécuter la requête avec la limite spécifiée
        cursor = collection.find(query).limit(limit)
        results = list(cursor)
        logger.info(f"🔍 {len(results)} documents récupérés.")
        return results

    except Exception as e:
        # En cas d'erreur lors de la lecture, loguer l'erreur et relancer l'exception
        logger.error(f"❌ Erreur de lecture : {e}")
        raise

# === MISE À JOUR ===
def update_records(collection: Collection, filter_query: dict, update_query: dict) -> int:
    """
    Met à jour les documents d'une collection MongoDB qui correspondent au filtre donné.
    
    Paramètres :
    - collection: La collection MongoDB à mettre à jour.
    - filter_query: Dictionnaire définissant les critères de sélection des documents à mettre à jour.
    - update_query: Dictionnaire définissant les modifications à appliquer.
    
    Retourne :
    - Le nombre de documents modifiés.
    """
    try:
        # Appliquer la mise à jour sur tous les documents correspondants au filtre
        result = collection.update_many(filter_query, update_query)
        logger.info(f"🔁 {result.modified_count} documents mis à jour.")
        return result.modified_count

    except Exception as e:
        # En cas d'erreur lors de la mise à jour, enregistrer l'erreur et relancer l'exception
        logger.error(f"❌ Erreur de mise à jour : {e}")
        raise

# === SUPPRESSION ===
def delete_records(collection: Collection, filter_query: dict) -> int:
    """
    Supprime les documents d'une collection MongoDB qui correspondent au filtre donné.
    
    Paramètres :
    - collection: La collection MongoDB où les documents seront supprimés.
    - filter_query: Dictionnaire définissant les critères de suppression.
    
    Retourne :
    - Le nombre de documents supprimés.
    """
    try:
        # Supprimer tous les documents qui correspondent au filtre
        result = collection.delete_many(filter_query)
        logger.warning(f"🗑️ {result.deleted_count} documents supprimés.")
        return result.deleted_count

    except Exception as e:
        # En cas d'erreur lors de la suppression, enregistrer l'erreur et relancer l'exception
        logger.error(f"❌ Erreur de suppression : {e}")
        raise

# === EXPORT CSV (optionnel) ===
def export_to_csv(collection: Collection, file_name: str, query: dict = {}, fields: list = None, limit: int = 0) -> int:
    """
    Exporte des documents d'une collection MongoDB vers un fichier CSV.
    
    Paramètres :
    - collection: La collection MongoDB à exporter.
    - file_name: Nom du fichier CSV (sans extension) qui sera créé.
    - query: Dictionnaire définissant les critères de filtrage des documents (par défaut, aucun filtre).
    - fields: Liste de champs à inclure dans l'export ; si None, tous les champs seront exportés.
    - limit: Nombre maximum de documents à exporter ; si 0, exporter tous les documents correspondants.
    
    Retourne :
    - Le nombre de documents exportés.
    """
    try:
        # Définir le dossier de sortie pour l'export et le créer s'il n'existe pas
        output_dir = "exports"
        os.makedirs(output_dir, exist_ok=True)
        # Construire le chemin complet du fichier CSV
        path = os.path.join(output_dir, f"{file_name}.csv")

        # Si une liste de champs est fournie, créer une projection pour extraire uniquement ces champs
        projection = {field: 1 for field in fields} if fields else None

        # Exécuter la requête avec la projection et la limite spécifiée (limit=0 signifie pas de limite)
        cursor = collection.find(query, projection).limit(limit if limit > 0 else 0)
        records = list(cursor)

        # Vérifier s'il y a des documents à exporter
        if not records:
            logger.warning("📭 Aucun document à exporter.")
            return 0

        # Convertir la liste des documents en DataFrame pandas
        df = pd.DataFrame(records)
        
        # Supprimer la colonne '_id' si elle existe, pour une exportation plus lisible
        if '_id' in df.columns:
            df.drop(columns=['_id'], inplace=True)

        # Exporter la DataFrame vers un fichier CSV
        df.to_csv(path, index=False, encoding='utf-8')
        logger.success(f"📄 Exporté avec succès dans : {path}")
        return len(df)

    except Exception as e:
        # En cas d'erreur lors de l'export, enregistrer l'erreur et relancer l'exception
        logger.error(f"❌ Erreur d'export CSV : {e}")
        raise
