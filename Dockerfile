# 🔧 Base image officielle Python
FROM python:3.11-slim

# 👤 Créer un utilisateur non root pour plus de sécurité
RUN useradd -m appuser
USER appuser

# 📁 Définir le dossier de travail dans le conteneur
WORKDIR /app

# 📥 Copier les fichiers du projet dans l’image
COPY --chown=appuser:appuser . .

# 📦 Installer les dépendances
RUN pip install --upgrade pip && pip install -r requirements.txt

# 🔊 Créer les dossiers pour les logs et les fichiers transformés
RUN mkdir -p logs processed exports

# ✅ Commande par défaut
CMD ["python", "src/main_mongodb.py"]
