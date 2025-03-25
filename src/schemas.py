# schemas.py
# --------------------------------------------------------------------------------
# Ce module définit le schéma de validation des observations météo à l'aide de Pydantic.
# Le modèle WeatherObservation garantit que les données météo respectent des contraintes
# précises (plages de valeurs, types, etc.) et permet d'appliquer des transformations 
# automatiques, comme la suppression des espaces superflus dans certains champs textuels.
# --------------------------------------------------------------------------------

from pydantic import BaseModel, Field, condecimal, field_validator
from typing import Optional
from datetime import datetime

class WeatherObservation(BaseModel):
    # -------------------------------------------------------------------------
    # Informations de base sur la station météo
    # -------------------------------------------------------------------------
    station_id: str             # Identifiant unique de la station
    station_name: str           # Nom de la station
    latitude: float             # Latitude géographique de la station
    longitude: float            # Longitude géographique de la station
    elevation_m: float          # Élévation (en mètres) de la station
    timestamp_utc: datetime     # Date et heure de l'observation en UTC

    # -------------------------------------------------------------------------
    # Mesures météorologiques avec contraintes de validation (plages acceptées)
    # -------------------------------------------------------------------------
    temperature_c: Optional[condecimal(ge=-80, le=60)] = None         # Température en °C (entre -80 et 60)
    dew_point_c: Optional[condecimal(ge=-80, le=60)] = None             # Point de rosée en °C (entre -80 et 60)
    humidity_pct: Optional[condecimal(ge=0, le=100)] = None              # Humidité relative en % (entre 0 et 100)
    pressure_hpa: Optional[condecimal(ge=800, le=1100)] = None           # Pression atmosphérique en hPa (entre 800 et 1100)

    wind_speed_kmh: Optional[condecimal(ge=0, le=250)] = None            # Vitesse du vent en km/h (entre 0 et 250)
    wind_gust_kmh: Optional[condecimal(ge=0, le=300)] = None             # Rafales de vent en km/h (entre 0 et 300)
    wind_dir_deg: Optional[int] = Field(None, ge=0, le=360)              # Direction du vent en degrés (entre 0 et 360)
    wind_dir_cardinal: Optional[str] = None                             # Direction du vent sous forme cardinale (ex: N, NE, etc.)

    precip_mm_1h: Optional[condecimal(ge=0, le=500)] = None              # Précipitations sur 1 heure en mm (entre 0 et 500)
    solar_radiation_wm2: Optional[condecimal(ge=0, le=2000)] = None       # Radiation solaire en W/m² (entre 0 et 2000)
    uv_index: Optional[condecimal(ge=0, le=15)] = None                    # Indice UV (entre 0 et 15)
    visibility_m: Optional[condecimal(ge=0, le=100000)] = None            # Visibilité en mètres (entre 0 et 100000)
    cloud_cover_okta: Optional[int] = Field(None, ge=0, le=8)             # Couverture nuageuse en oktas (entre 0 et 8)

    # -------------------------------------------------------------------------
    # Informations sur la source et les métadonnées techniques
    # -------------------------------------------------------------------------
    source: str               # Source de l'observation (ex: weather_underground, infoclimat, etc.)
    hardware: Optional[str] = None    # Matériel utilisé par la station (si disponible)
    software: Optional[str] = None    # Version du logiciel utilisé (si disponible)

    # -------------------------------------------------------------------------
    # Validator pour nettoyer les champs textuels : suppression des espaces en trop
    # -------------------------------------------------------------------------
    @field_validator("station_id", "station_name", "source", "hardware", "software")
    @classmethod
    def strip_strings(cls, v):
        """
        Supprime les espaces superflus en début et fin de chaîne pour les champs textuels.

        Paramètres:
            v (Any): La valeur à nettoyer.

        Retourne:
            La chaîne nettoyée si v est une chaîne, sinon la valeur d'origine.
        """
        return v.strip() if isinstance(v, str) else v
