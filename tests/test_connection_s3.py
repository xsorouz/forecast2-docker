import requests

# Liste des fichiers publics à récupérer
files = {
    "Data_Source1.json": "https://s3.eu-west-1.amazonaws.com/course.oc-static.com/projects/922_Data+Engineer/922_P8/Data_Source1_011024-071024.json",
    "Weather_Ichtegem.xlsx": "https://s3.eu-west-1.amazonaws.com/course.oc-static.com/projects/922_Data+Engineer/922_P8/Weather+Underground+-+Ichtegem%2C+BE.xlsx",
    "Weather_Madeleine.xlsx": "https://s3.eu-west-1.amazonaws.com/course.oc-static.com/projects/922_Data+Engineer/922_P8/Weather+Underground+-+La+Madeleine%2C+FR.xlsx"
}

for filename, url in files.items():
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"✅ {filename} téléchargé avec succès !")
    else:
        print(f"❌ Erreur {response.status_code} en téléchargeant {filename}")
