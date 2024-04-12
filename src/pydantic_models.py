from enum import Enum
import json
from typing import Callable, Coroutine, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


growbuddies_config_filename = "config/growbuddies_config.json"
class MonitorParam(Enum):
    KP = "Kp"
    KI = "Ki"
    KD = "Kd"

class GlobalSettingsModel(BaseModel):
    log_level: str # TODO: Right now, the log level is set to whatever..I haven't paid attention.
class PidConfigModel(BaseModel):
    active: bool
    hostname:str
    snifferbuddy_incoming_port: int
    setpoint: float
    Kp: float = Field(ge=0)  # Ensures Kp is greater than or equal to 0
    Ki: float = Field(ge=0)  # Ensures Ki is greater than or equal to 0
    Kd: float = Field(ge=0)  # Ensures Kd is greater than or equal to 0
    seconds_on_limit: List[int]
    integral_limits: List[int]
    comparison_function: str
    mqtt_power_topics: List[str]
    telegraf_fieldname: str

    @field_validator('comparison_function')
    @classmethod
    def check_comparison_function(cls, v):
        if v not in ["greater_than", "less_than"]:
            raise ValueError("Invalid comparison function. Must be 'greater_than' or 'less_than'")
        return v

class GrowTentConfigModel(BaseModel):
    name: str
    MistBuddy: PidConfigModel
    CO2Buddy: PidConfigModel

class GlobalConfigModel(BaseModel):
    global_settings: GlobalSettingsModel
    grow_tents: List[GrowTentConfigModel]

class GlobalConfig:
    _model = None

    @classmethod
    def get_model(cls):
        return cls._model

    @classmethod
    def update(cls, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, Enum):
                # Assuming you want to use the first value in the tuple for the enum
                actual_value = value.value[0]  # Adjust this as needed
            else:
                actual_value = value
            if hasattr(cls._model, key):
                setattr(cls._model, key, actual_value)
            else:
                raise ValueError(f"{key} is not a property of the GlobalConfig class and no similar field found.")


    @classmethod
    def get(cls, field_name):
        if hasattr(cls._model, field_name):
            return getattr(cls._model, field_name, None)
        else:
            raise ValueError(f"{field_name} is not a property of the GlobalConfig class and no similar field found.")

    @classmethod
    def load_config(cls, config_filename: str):
        if not cls._model: # No reason to load the data if it is already loaded.
            with open(config_filename, 'r', encoding="utf-8") as file:
                data = json.load(file)
            cls._model = GlobalConfigModel(**data)

    @classmethod
    def get_pid_config(cls, tent_name: str, controller_type: str) -> PidConfigModel:
        cls.load_config(growbuddies_config_filename)
        for tent in cls._model.grow_tents:
            if tent.name == tent_name:
                if controller_type.lower() == "co2":
                    return tent.CO2Buddy
                if controller_type.lower() == "vpd":
                    return tent.MistBuddy

        raise ValueError(f"Tent named {tent_name} not found or controller type {controller_type} is incorrect.")

class PIDState(BaseModel):
    value: float = None  # Assuming value should be float; adjust type as needed
    seconds_on: float = None
    error: float
    P: float
    I: float
    D: float
    Kp: float
    Ki: float
    Kd: float

class GrowTentParams(BaseModel):
    monitor_param: MonitorParam
    tent_name: str
    controller_type: str
    hostname: Optional[str] = "gus.local"
    snifferbuddy_incoming_port: Optional[int]=8095
    mqtt_power_topics: Optional[List[str]] = []
    sensor_reading_callback: Optional[Callable[..., Coroutine]] = None
    PID_state_callback: Optional[Callable[..., Coroutine]] = None

    @field_validator('controller_type')
    @classmethod
    def name_must_be_one_of_these(cls,v):
        allowed_values = {"CO2", "VPD"}
        if v.upper() not in allowed_values:
            raise ValueError(f"Invalid value: {v}. Expected one of {allowed_values}")
        return v

    @field_validator('tent_name')
    @classmethod
    def name_must_be_string(cls, v):
        if not isinstance(v, str):
            raise ValueError('The tent name must exist and must be a string')
        return v

class SensorDataModel(BaseModel):
    CO2: float
    dewpoint: float
    eCO2: float
    humidity: float
    light: int
    temperature: float
    vpd: float

class SnifferBuddyModel(BaseModel):
    fields: SensorDataModel
    name: str
    tags: Dict[str, str]
    timestamp: int