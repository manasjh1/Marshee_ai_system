"""Stage management module"""

import importlib
from typing import Dict, Any, Optional

# List of all stage modules
STAGE_MODULES = [
    "user_name",
    "pet_name", 
    "pet_type",
    "pet_gender",
    "pet_breed",
    "pet_age",
    "pet_weight"
]

def load_stage(stage_id: str):
    """Dynamically load a stage module"""
    try:
        return importlib.import_module(f"stages.{stage_id}")
    except ImportError:
        return None

def get_stage_config(stage_id: str) -> Optional[Dict[str, Any]]:
    """Get stage configuration"""
    stage_module = load_stage(stage_id)
    if stage_module:
        return stage_module.STAGE_CONFIG
    return None

def get_stage_response(stage_id: str, user_data: dict, is_error: bool = False) -> str:
    """Get stage response"""
    stage_module = load_stage(stage_id)
    if stage_module:
        return stage_module.get_marshee_response(user_data, is_error)
    return "How can I help you?"

def validate_stage_input(stage_id: str, value: str) -> bool:
    """Validate stage input"""
    stage_module = load_stage(stage_id)
    if stage_module:
        return stage_module.validate_input(value)
    return True

def get_stage_data(stage_id: str, user_data: dict = None) -> Dict[str, Any]:
    """Get stage data (buttons/dropdown options)"""
    stage_module = load_stage(stage_id)
    if stage_module and hasattr(stage_module, 'get_stage_data'):
        try:
            return stage_module.get_stage_data(user_data)
        except TypeError:
            try:
                return stage_module.get_stage_data()
            except TypeError:
                return {}
    return {}