"""
Centralized Observatory Configuration
Defines predefined observatory locations for the radio telescope project.

This module provides a centralized location for observatory coordinates
to avoid duplication across different example and test files.

Author: Aleks Czarnecki
"""

from Engine.AstronomyCalculator import ObserverLocation
from backend.LanguageHelper import LanguageHelper

# Initialize language helper for observatory definitions
_language_helper = LanguageHelper(language="pl", defaultLanguage="en")

# Predefiniowane lokalizacje obserwatoriów
OBSERVATORIES = {
    "polanka": {
        "name": "Poznań Polanka",
        "latitude": 52.40030228321106,
        "longitude": 16.955077591791788,
        "elevation": 60.0
    },
    "krakow": {
        "name": "Kraków",
        "latitude": 50.0647,
        "longitude": 19.9450,
        "elevation": 219.0
    }
}


def get_observer_location(location_key: str, language_helper: LanguageHelper = None) -> ObserverLocation:
    """
    Get an ObserverLocation object for a specific observatory.
    
    Args:
        location_key: Key identifying the observatory (e.g., "polanka", "krakow")
        language_helper: Optional LanguageHelper instance. If not provided, uses default.
        
    Returns:
        ObserverLocation object for the specified observatory
        
    Raises:
        KeyError: If location_key is not found in OBSERVATORIES
    """
    if location_key not in OBSERVATORIES:
        raise KeyError(f"Unknown observatory location: {location_key}. "
                      f"Available locations: {', '.join(OBSERVATORIES.keys())}")
    
    obs_data = OBSERVATORIES[location_key]
    lang_helper = language_helper or _language_helper
    
    return ObserverLocation(
        lang_helper,
        latitude=obs_data['latitude'],
        longitude=obs_data['longitude'],
        elevation=obs_data['elevation'],
        name=obs_data['name']
    )


def list_observatories():
    """
    List all available observatory locations.
    
    Returns:
        Dictionary of observatory configurations
    """
    return OBSERVATORIES.copy()
