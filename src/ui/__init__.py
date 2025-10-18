"""
UI module for MedCare AI CDSS
Contains the Streamlit application and user interface components
"""

# Import main components when available
try:
    from .main_app import main
    __all__ = ['main']
except ImportError:
    __all__ = []