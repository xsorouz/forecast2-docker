# tests/conftest.py
# --------------------------------------------------------------------------------
# Ce fichier de configuration (conftest.py) est exécuté avant les tests.
# Il configure Loguru pour afficher les logs sur la console et ajoute le dossier "src/"
# au chemin d'importation Python pour permettre l'accès aux modules du projet.
# --------------------------------------------------------------------------------

import sys
import pytest
from loguru import logger
import os

@pytest.fixture(autouse=True)
def loguru_setup():
    """Configure Loguru pour afficher les logs sur la console avec le niveau INFO."""
    logger.remove()  # Supprime les handlers par défaut
    logger.add(sys.stdout, level="INFO", enqueue=True)

# Ajout du dossier "src/" au chemin Python pour accéder aux modules du projet
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
