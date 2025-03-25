@echo off
echo 🧹 Nettoyage ciblé du projet Docker 'forecast2-docker'...

REM 1. Stopper et supprimer uniquement le service forecast_app
docker compose down --volumes --remove-orphans

REM 2. Supprimer les images locales forecast2-docker-*
echo 🗑️ Suppression des images forecast2-docker-*
FOR /f %%i IN ('docker images "forecast2-docker-*" -q') DO docker rmi -f %%i

REM 3. Supprimer les volumes inutilisés (sans toucher aux actifs comme Airbyte)
echo 📦 Suppression des volumes inutilisés
docker volume prune -f

REM 4. Supprimer les réseaux inutilisés
echo 🔗 Suppression des réseaux inutilisés
docker network prune -f

echo ✅ Nettoyage terminé (Airbyte n’a pas été touché)
pause
