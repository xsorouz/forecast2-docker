# 🐍 Utilisation de l'image officielle de Python 3.9
# Cette image contient déjà une installation de Python et pip
FROM python:3.9

# 📂 Définition du répertoire de travail dans le conteneur
# Tous les fichiers seront copiés et exécutés à partir de ce dossier
WORKDIR /app

# 📜 Copie du fichier requirements.txt dans le conteneur
# Ce fichier contient la liste des bibliothèques Python à installer
COPY ../requirements.txt /app/requirements.txt

# 📦 Installation des dépendances Python
# `--no-cache-dir` permet d'éviter d'enregistrer des fichiers temporaires inutiles
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    pip cache purge  # Nettoie le cache de pip après installation

# 🔄 Création des dossiers pour éviter les erreurs si les volumes montés sont vides
RUN mkdir -p /app/data /app/logs

# 🔄 Copie des fichiers et dossiers nécessaires dans le conteneur
COPY ../scripts/ /app/scripts/

# 🚀 Définition du point d’entrée du conteneur
# À chaque exécution du conteneur, ce script sera lancé automatiquement
ENTRYPOINT ["python", "/app/scripts/transform_script.py"]
