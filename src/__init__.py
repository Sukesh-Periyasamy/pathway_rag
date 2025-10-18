"""
MedCare AI Clinical Decision Support System
AI-powered healthcare solution for hackathon submission
"""

__version__ = "1.0.0"
__author__ = "Healthcare AI Innovators"
__description__ = "AI-Powered Clinical Decision Support System with Vector Database Integration"

# Package metadata
PACKAGE_NAME = "medcare-ai-cdss"
HACKATHON_SUBMISSION = True
DEMO_URL = "http://localhost:8505"
GITHUB_URL = "https://github.com/your-team/medcare-ai-cdss"

# Feature flags
FEATURES = {
    "vector_search": True,
    "ai_summaries": True,
    "pdf_generation": True,
    "patient_education": True,
    "drug_interactions": True,
    "bias_mitigation": True,
}

# System requirements
MIN_PYTHON_VERSION = "3.9"
REQUIRED_MEMORY_GB = 4
REQUIRED_DISK_GB = 2