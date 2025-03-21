import re
import pandas as pd
from datetime import datetime
from loguru import logger
import math

# Conversion d’unités
def f_to_c(fahrenheit_str):
    try:
        value = float(fahrenheit_str.replace("°F", "").replace(",", ".").strip())
        return round((value - 32) * 5/9, 2)
    except:
        return None

def inhg_to_hpa(pressure_str):
    try:
        value = float(pressure_str.replace("in", "").replace(",", ".").strip())
        return round(value * 33.8639, 2)
    except:
        return None

def mph_to_kmh(speed_str):
    try:
        value = float(speed_str.replace("mph", "").replace(",", ".").strip())
        return round(value * 1.60934, 2)
    except:
        return None

def in_to_mm(inches_str):
    try:
        value = float(inches_str.replace("in", "").replace(",", ".").strip())
        return round(value * 25.4, 2)
    except:
        return None

def percent_to_float(pct_str):
    try:
        return float(pct_str.replace("%", "").replace(" ", "").strip())
    except:
        return None

def solar_to_float(solar_str):
    try:
        return float(solar_str.replace("w/m²", "").replace(" ", "").strip())
    except:
        return None

# Transformation de la direction cardinale en degrés (si souhaité)
CARDINAL_TO_DEGREES = {
    "N": 0, "NNE": 22, "NE": 45, "ENE": 67,
    "E": 90, "ESE": 112, "SE": 135, "SSE": 157,
    "S": 180, "SSW": 202, "SW": 225, "WSW": 247,
    "W": 270, "WNW": 292, "NW": 315, "NNW": 337
}

def cardinal_to_degrees(cardinal):
    try:
        return CARDINAL_TO_DEGREES.get(cardinal.strip().upper())
    except:
        return None

# Reconstruire datetime depuis feuille Excel + time
def build_full_timestamp(date_str, time_str):
    try:
        dt_str = f"{date_str} {time_str}"
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None

# Nettoyage pour InfoClimat : float safe
def safe_float(x):
    try:
        return float(x)
    except:
        return None

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=lambda c: c.strip().replace(" ", "_").replace(".", "").lower())
