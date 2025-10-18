"""
Core module for MedCare AI CDSS
Contains the main clinical decision engine and AI integration
"""

from .clinical_engine import (
    MedicalKnowledgeBase,
    generate_doctor_summary,
    generate_patient_education,
    load_patient_data,
    get_guidelines_recommendations,
    analyze_drug_safety,
    fetch_research,
    merge_module_outputs,
    apply_bias_mitigation
)

__all__ = [
    'MedicalKnowledgeBase',
    'generate_doctor_summary', 
    'generate_patient_education',
    'load_patient_data',
    'get_guidelines_recommendations',
    'analyze_drug_safety',
    'fetch_research',
    'merge_module_outputs',
    'apply_bias_mitigation'
]