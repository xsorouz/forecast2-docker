# 📌 Forecast 2.0 - Pipeline de Traitement des Données Météo 🌍⚡

## 🚀 Contexte du Projet
GreenAndCoop, fournisseur coopératif d’électricité renouvelable, souhaite améliorer la **prévision de la demande énergétique** en intégrant des **données météorologiques issues de stations semi-professionnelles** (**InfoClimat & Weather Underground**).  

### 🎯 Objectif  
Développer un **pipeline automatisé et scalable** permettant de :  
- Collecter les données météorologiques en temps réel,  
- Nettoyer, transformer et valider ces données,  
- Stocker les relevés météo dans une base de données NoSQL (**MongoDB Atlas**),  
- Exporter les données pour analyses et reporting.

---

## 📊 Fonctionnalités Clés
✅ **Collecte automatisée** des données via **Airbyte** 📡  
✅ **Stockage temporaire** en **local et AWS S3** 🗄️  
✅ **Transformation et validation** des relevés météorologiques 🔍  
✅ **Stockage optimisé** dans **MongoDB Atlas** pour les analyses 📂  
✅ **Export en CSV** pour les Data Scientists 📈  
✅ **Déploiement cloud-ready** avec **Docker, AWS S3 et ECS** ☁️  

---

## 🛠️ Stack Technique Utilisée
| **Technologie**              | **Utilisation**                          |
|------------------------------|------------------------------------------|
| **Docker & Docker Compose**  | Orchestration des services               |
| **MongoDB Atlas**            | Base de données NoSQL                    |
| **AWS S3**                   | Stockage des fichiers bruts              |
| **Airbyte**                  | Collecte automatique des données météo   |
| **Python (pandas, pymongo, boto3)** | Transformation et validation |
| **Loguru**                    | Gestion des logs                        |

---

## 📂 Structure des Répertoires  

```
📂 forecast2-docker/
│
├── 📂 data/                  # Stockage des fichiers JSON et CSV
│   ├── 📂 raw/               # Données brutes collectées
│   ├── 📂 processed/         # Données transformées
│   ├── 📂 export/            # Fichiers CSV exportés
│   ├── 📂 logs/              # Logs du pipeline
│
├── 📂 scripts/               # Scripts Python du pipeline
│   ├── collect_data.py       # Récupération des données via API
│   ├── transform_script.py   # Nettoyage et validation des données
│   ├── upload_to_s3.py       # Envoi des fichiers vers AWS S3
│   ├── export_to_csv.py      # Génération du fichier CSV
│   ├── data_quality_report.py # Vérification de la qualité des données
│   └── test_pipeline.py      # Tests unitaires du pipeline
│
├── 📂 docker/                # Configuration des conteneurs Docker
│   ├── Dockerfile            # Configuration du conteneur principal
│   ├── docker-compose.yml    # Orchestration des services Docker
│   └── setup.sh              # Script de lancement automatique
│
├── 📂 docs/                  # Documentation et ressources
│   ├── architecture.png      # Schéma d'architecture
│   ├── logigramme.png        # Logigramme du pipeline
│   ├── README_pipeline.md    # Documentation détaillée du pipeline
│   └── README_deploiement.md # Documentation sur le déploiement AWS
│
├── 📂 tests/                 # Tests unitaires et validation du pipeline
│   ├── test_data_validation.py # Test des mécanismes de validation
│   ├── test_mongodb.py       # Test de connexion MongoDB
│   └── test_export.py        # Test de l’export en CSV
│
├── .gitignore                # Fichiers à ignorer dans Git
├── requirements.txt          # Dépendances Python nécessaires
├── README.md                 # Documentation principale du projet
└── LICENSE                   # Licence du projet (ex : MIT)
```
---

## 📊 Validation des Données et Contrôle Qualité  

📌 **Qualité des données vérifiée avant et après l’import dans MongoDB** :
- 🔍 **Vérification des types de données**
- 📉 **Gestion des valeurs manquantes et des doublons**
- 📜 **Logs détaillés via `loguru`**

✅ **Analyse des logs :**
```bash
cat logs/data_quality_report.log
---

## ⚙️ Installation et Exécution du Projet  

### **1️⃣ Cloner le Projet**  
```bash
git clone https://github.com/VOTRE_NOM/forecast2-docker.git
cd forecast2-docker
```

### **2️⃣ Installer les Dépendances Python**  
```bash
pip install -r requirements.txt
```

### **3️⃣ Lancer les Services Docker**  
```bash
chmod +x docker/setup.sh
./docker/setup.sh
```

### **4️⃣ Vérifier MongoDB et les Fichiers Stockés**  
```bash
docker exec -it mongo_container mongo
use weather_db
db.stations_data.find().limit(5).pretty();
```

### **5️⃣ Tester l’Export en CSV**  
```bash
head -n 5 data/export/weather_data.csv
```

---

## 📊 Présentation de l’Architecture Technique  

Le pipeline fonctionne en **5 étapes clés** :  
1️⃣ **Collecte des données** via API avec **Airbyte**  
2️⃣ **Stockage brut** en local et sur **AWS S3**  
3️⃣ **Transformation et validation** des données via Python  
4️⃣ **Stockage des données nettoyées** dans **MongoDB Atlas**  
5️⃣ **Export des données en CSV** pour analyse  

📌 **Schéma détaillé disponible dans `docs/architecture.png`**  

---

## 🚀 Réplication MongoDB Atlas  
MongoDB Atlas est configuré avec :
- **Un cluster répliqué (3 nœuds)**
- **Sauvegarde automatique**
- **Haute disponibilité**

📌 **Configuration détaillée dans `README_deploiement.md`**  

---

## 📝 Auteurs et Contributeurs  

- **[Sorouz]** - Développement et intégration  
- **GreenAndCoop** - Commanditaire du projet  

---

## 📜 Licence  

Ce projet est sous licence **MIT**.  

---
 