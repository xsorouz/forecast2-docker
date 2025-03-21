import os
import pandas as pd
import json
from datetime import time

# Définition des chemins des fichiers
INPUT_DIR = "data/raw/"
OUTPUT_DIR = "data/processed/"

# Liste des fichiers à traiter
files = {
    "madeleine": {
        "input": os.path.join(INPUT_DIR, "Weather+Underground+-+La+Madeleine,+FR.xlsx"),
        "output": os.path.join(OUTPUT_DIR, "dataset_madeleine.json"),
        "metadata": {
            "Weather Station ID": "ILAMAD25",
            "Station Name": "La Madeleine",
            "Latitude": 50.659,
            "Longitude": 3.07,
            "Elevation": 23,
            "City": "La Madeleine",
            "State": "-/-",
            "Hardware": "other",
            "Software": "EasyWeatherPro_V5.1.6"
        }
    },
    "ichtegem": {
        "input": os.path.join(INPUT_DIR, "Weather+Underground+-+Ichtegem,+BE.xlsx"),
        "output": os.path.join(OUTPUT_DIR, "dataset_ichtegem.json"),
        "metadata": {
            "Weather Station ID": "IICHTE19",
            "Station Name": "WeerstationBS",
            "Latitude": 51.092,
            "Longitude": 2.999,
            "Elevation": 15,
            "City": "Ichtegem",
            "State": "-/-",
            "Hardware": "other",
            "Software": "EasyWeatherV1.6.6"
        }
    }
}

def transform_to_json(input_path, output_path, metadata):
    """Convertit un fichier Excel en JSON en ajoutant des métadonnées de station météo."""
    try:
        # Charger le fichier Excel et récupérer toutes les feuilles
        xls = pd.ExcelFile(input_path)
        data = {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names}

        # Correction des types de données pour éviter les erreurs JSON
        for sheet, df in data.items():
            df = df.copy()
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].astype(str)
                elif pd.api.types.is_timedelta64_dtype(df[col]):
                    df[col] = df[col].astype(str)
                elif df[col].dtype == object:
                    df[col] = df[col].apply(lambda x: x.strftime("%H:%M:%S") if isinstance(x, time) else x)

            data[sheet] = df.to_dict(orient="records")

        # Structure finale du fichier JSON
        transformed_data = {
            "metadata": metadata,
            "data": data
        }

        # Sauvegarde du fichier JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transformed_data, f, indent=4)

        print(f"✅ Fichier JSON généré : {output_path}")

    except Exception as e:
        print(f"❌ Erreur lors du traitement de {input_path} : {e}")

# Création du répertoire de sortie s'il n'existe pas
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Exécution du traitement pour chaque fichier
for key, file_info in files.items():
    transform_to_json(file_info["input"], file_info["output"], file_info["metadata"])
