"""
Module: utils_weather.py
------------------------
Ce module fournit des fonctions utilitaires pour :
  - Convertir des mesures d'unités (température, pression, vitesse, précipitations, etc.)
  - Transformer des valeurs de chaîne en nombres (float)
  - Convertir la direction cardinale en degrés
  - Construire un objet datetime à partir de chaînes de date et d'heure
  - Nettoyer les noms de colonnes dans un DataFrame Pandas

Chaque fonction intègre un mécanisme de gestion d'erreur qui renvoie None en cas d'échec de conversion.
"""

import re
import pandas as pd
from datetime import datetime
from loguru import logger
import math

# -----------------------------------------------------------------------------
# Fonctions de conversion d'unités
# -----------------------------------------------------------------------------

def f_to_c(fahrenheit_str):
    """
    Convertit une température de Fahrenheit en Celsius.
    
    Paramètres:
      fahrenheit_str (str): Température en Fahrenheit sous forme de chaîne (ex: "68°F").
    
    Retourne:
      float: Température convertie en Celsius, arrondie à 2 décimales, ou None en cas d'erreur.
    """
    try:
        # Supprime le symbole "°F", remplace les virgules par des points et convertit en float
        value = float(fahrenheit_str.replace("°F", "").replace(",", ".").strip())
        return round((value - 32) * 5/9, 2)
    except Exception as e:
        logger.debug(f"Erreur dans f_to_c pour '{fahrenheit_str}': {e}")
        return None

def inhg_to_hpa(pressure_str):
    """
    Convertit une pression de pouces de mercure (inHg) en hectopascals (hPa).
    
    Paramètres:
      pressure_str (str): Pression en inHg sous forme de chaîne (ex: "29.92 in").
    
    Retourne:
      float: Pression convertie en hPa, arrondie à 2 décimales, ou None en cas d'erreur.
    """
    try:
        value = float(pressure_str.replace("in", "").replace(",", ".").strip())
        return round(value * 33.8639, 2)
    except Exception as e:
        logger.debug(f"Erreur dans inhg_to_hpa pour '{pressure_str}': {e}")
        return None

def mph_to_kmh(speed_str):
    """
    Convertit une vitesse de miles par heure (mph) en kilomètres par heure (km/h).
    
    Paramètres:
      speed_str (str): Vitesse en mph sous forme de chaîne (ex: "30 mph").
    
    Retourne:
      float: Vitesse convertie en km/h, arrondie à 2 décimales, ou None en cas d'erreur.
    """
    try:
        value = float(speed_str.replace("mph", "").replace(",", ".").strip())
        return round(value * 1.60934, 2)
    except Exception as e:
        logger.debug(f"Erreur dans mph_to_kmh pour '{speed_str}': {e}")
        return None

def in_to_mm(inches_str):
    """
    Convertit une mesure de précipitation de pouces en millimètres.
    
    Paramètres:
      inches_str (str): Valeur en pouces sous forme de chaîne (ex: "0.5 in").
    
    Retourne:
      float: Valeur convertie en mm, arrondie à 2 décimales, ou None en cas d'erreur.
    """
    try:
        value = float(inches_str.replace("in", "").replace(",", ".").strip())
        return round(value * 25.4, 2)
    except Exception as e:
        logger.debug(f"Erreur dans in_to_mm pour '{inches_str}': {e}")
        return None

def percent_to_float(pct_str):
    """
    Convertit une chaîne représentant un pourcentage en nombre flottant.
    
    Paramètres:
      pct_str (str): Pourcentage sous forme de chaîne (ex: "75%").
    
    Retourne:
      float: La valeur numérique du pourcentage, ou None en cas d'erreur.
    """
    try:
        return float(pct_str.replace("%", "").replace(" ", "").strip())
    except Exception as e:
        logger.debug(f"Erreur dans percent_to_float pour '{pct_str}': {e}")
        return None

def solar_to_float(solar_str):
    """
    Convertit une chaîne représentant une radiation solaire en nombre flottant.
    
    Paramètres:
      solar_str (str): Valeur de radiation solaire sous forme de chaîne (ex: "800 w/m²").
    
    Retourne:
      float: La valeur numérique de la radiation solaire, ou None en cas d'erreur.
    """
    try:
        return float(solar_str.replace("w/m²", "").replace(" ", "").strip())
    except Exception as e:
        logger.debug(f"Erreur dans solar_to_float pour '{solar_str}': {e}")
        return None

# -----------------------------------------------------------------------------
# Conversion de la direction cardinale en degrés
# -----------------------------------------------------------------------------

# Dictionnaire de conversion des points cardinaux en degrés
CARDINAL_TO_DEGREES = {
    "N": 0, "NNE": 22, "NE": 45, "ENE": 67,
    "E": 90, "ESE": 112, "SE": 135, "SSE": 157,
    "S": 180, "SSW": 202, "SW": 225, "WSW": 247,
    "W": 270, "WNW": 292, "NW": 315, "NNW": 337
}

def cardinal_to_degrees(cardinal):
    """
    Convertit une direction cardinale en degrés.
    
    Paramètres:
      cardinal (str): Direction cardinale (ex: "NE").
    
    Retourne:
      int: Valeur en degrés correspondant, ou None si la conversion échoue.
    """
    try:
        # Convertit la chaîne en majuscules et retire les espaces superflus
        return CARDINAL_TO_DEGREES.get(cardinal.strip().upper())
    except Exception as e:
        logger.debug(f"Erreur dans cardinal_to_degrees pour '{cardinal}': {e}")
        return None

# -----------------------------------------------------------------------------
# Construction d'un timestamp complet à partir d'une date et d'une heure
# -----------------------------------------------------------------------------

def build_full_timestamp(date_str, time_str):
    """
    Reconstruit un objet datetime à partir d'une date et d'une heure fournies sous forme de chaînes.
    
    Paramètres:
      date_str (str): Date au format "YYYY-MM-DD".
      time_str (str): Heure au format "HH:MM:SS".
    
    Retourne:
      datetime: L'objet datetime correspondant, ou None en cas d'erreur.
    """
    try:
        dt_str = f"{date_str} {time_str}"
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.debug(f"Erreur dans build_full_timestamp pour '{date_str} {time_str}': {e}")
        return None

# -----------------------------------------------------------------------------
# Autres fonctions utilitaires
# -----------------------------------------------------------------------------

def safe_float(x):
    """
    Tente de convertir une valeur en float.
    
    Paramètres:
      x: La valeur à convertir.
    
    Retourne:
      float: La valeur convertie, ou None en cas d'erreur.
    """
    try:
        return float(x)
    except Exception as e:
        logger.debug(f"Erreur dans safe_float pour '{x}': {e}")
        return None

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie les noms de colonnes d'un DataFrame.
    
    Transformation appliquée :
      - Suppression des espaces en début/fin,
      - Remplacement des espaces par des underscores,
      - Suppression des points,
      - Conversion en minuscules.
    
    Paramètres:
      df (pd.DataFrame): Le DataFrame dont les colonnes doivent être nettoyées.
    
    Retourne:
      pd.DataFrame: Le DataFrame avec des noms de colonnes standardisés.
    """
    return df.rename(columns=lambda c: c.strip().replace(" ", "_").replace(".", "").lower())
