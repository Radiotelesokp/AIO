from backend.Engine.EngineServiceRest import EngineServiceRest


__all__ = ["EngineServiceRest"]
__author__ = "Aleks Czarnecki"
__version__ = "0.1.0"
__editor__ = "Wiktoria Dębowska"

"""
Library for controlling the radio telescope antenna motor
Communication protocol: Hamlib rotctl

Main library containing a complete control system for the radio telescope antenna.
Uses the Hamlib (rotctl) library to communicate with the SPID MD-01/02/03 controller.
Includes the rotctl driver, position controller, real-time monitoring,
and comprehensive error and safety limit handling.

Author: Aleks Czarnecki
"""