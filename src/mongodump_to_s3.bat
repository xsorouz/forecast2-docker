@echo off
setlocal

:: Charger les variables du fichier .env
for /f "tokens=1,* delims==" %%A in (".env") do (
    set %%A=%%B
)

:: Dossier de dump
set DUMP_DIR=dump
set FILE_NAME=weather_backup_%DATE:~6,4%-%DATE:~3,2%-%DATE:~0,2%.gz

if not exist %DUMP_DIR% (
    mkdir %DUMP_DIR%
)

:: Dump MongoDB
mongodump --uri="%MONGO_URI%" --archive="%DUMP_DIR%\%FILE_NAME%" --gzip

:: Upload vers S3
aws s3 cp %DUMP_DIR%\%FILE_NAME% s3://forecast2-raw-data/backup_data/mongodb/ --region %AWS_REGION%

echo ✅ Backup MongoDB envoyée dans S3/backup_data/mongodb/
pause
