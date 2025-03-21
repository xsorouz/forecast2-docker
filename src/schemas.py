from pydantic import BaseModel, Field, condecimal, validator
from typing import Optional
from datetime import datetime

class WeatherObservation(BaseModel):
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    elevation_m: float
    timestamp_utc: datetime

    temperature_c: Optional[condecimal(ge=-80, le=60)] = None
    dew_point_c: Optional[condecimal(ge=-80, le=60)] = None
    humidity_pct: Optional[condecimal(ge=0, le=100)] = None
    pressure_hpa: Optional[condecimal(ge=800, le=1100)] = None

    wind_speed_kmh: Optional[condecimal(ge=0, le=250)] = None
    wind_gust_kmh: Optional[condecimal(ge=0, le=300)] = None
    wind_dir_deg: Optional[int] = Field(None, ge=0, le=360)
    wind_dir_cardinal: Optional[str] = None

    precip_mm_1h: Optional[condecimal(ge=0, le=500)] = None
    solar_radiation_wm2: Optional[condecimal(ge=0, le=2000)] = None
    uv_index: Optional[condecimal(ge=0, le=15)] = None
    visibility_m: Optional[condecimal(ge=0, le=100000)] = None
    cloud_cover_okta: Optional[int] = Field(None, ge=0, le=8)

    source: str

    # ✅ Champs de métadonnées supplémentaires
    hardware: Optional[str] = None
    software: Optional[str] = None

    @validator("station_id", "station_name", "source", "hardware", "software")
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v
