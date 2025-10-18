import streamlit as st
import json
import os
import sys
import traceback
from datetime import datetime
import re
from pathlib import Path
import base64
import time
import pandas as pd
from typing import Dict, Any, List
import logging
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# Add the parent directories to the path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent
project_root = src_dir.parent
sys.path.extend([str(src_dir), str(project_root)])

# Import orchestrator functions
try:
    from core.clinical_engine import (
        load_patient_data,
        get_guidelines_recommendations,
        analyze_drug_safety,
        fetch_research,
        merge_module_outputs,
        apply_bias_mitigation,
        generate_doctor_summary,
        generate_patient_education
    )
    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    st.error(f"⚠️ Orchestrator not available: {e}")
    ORCHESTRATOR_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Clinical Decision Support System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced UI
st.markdown("""
    <style>
    /* Enhanced input field styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        background-color: white !important;
        border: 1px solid #cccccc !important;
        border-radius: 4px !important;
        padding: 8px !important;
        color: #000000 !important;
    }
    
    /* Input field focus effects */
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #1f77b4 !important;
        box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
    }
    
    /* Alert styling */
    .alert-critical {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 10px;
        margin: 5px 0;
        border-radius: 4px;
    }
    
    .alert-high {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 10px;
        margin: 5px 0;
        border-radius: 4px;
    }
    
    .patient-card {
        background-color: #f8f9fa;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .patient-card:hover {
        background-color: #e9ecef;
        border-color: #007bff;
    }
    
    .selected-patient {
        background-color: #d4edda !important;
        border-color: #28a745 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = None
if 'processing_step' not in st.session_state:
    st.session_state.processing_step = 0
if 'selected_patient' not in st.session_state:
    st.session_state.selected_patient = None
if 'mode' not in st.session_state:
    st.session_state.mode = 'patient_management'  # 'patient_management', 'new_patient', 'analysis'

# Utility Functions
def create_patient_records_directory():
    """Create patient records directory if it doesn't exist."""
    records_dir = Path("patient_records")
    records_dir.mkdir(exist_ok=True)
    return records_dir

def sanitize_filename(name: str) -> str:
    """Sanitize patient name for use as filename."""
    # Remove special characters and replace spaces with underscores
    sanitized = re.sub(r'[^\w\s-]', '', name)
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    return sanitized.lower()

def save_patient_data(patient_data: Dict[str, Any]) -> str:
    """Save patient data to JSON file and return filename."""
    records_dir = create_patient_records_directory()
    
    # Create filename from patient name
    patient_name = patient_data.get('name', 'Unknown')
    safe_name = sanitize_filename(patient_name)
    filename = f"{safe_name}_{patient_data.get('patient_id', 'no_id')}.json"
    filepath = records_dir / filename
    
    # Add metadata
    patient_data['saved_at'] = datetime.now().isoformat()
    patient_data['last_modified'] = datetime.now().isoformat()
    
    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(patient_data, f, indent=2, ensure_ascii=False, default=str)
    
    return str(filepath)

def load_patient_data_from_file(filepath: str) -> Dict[str, Any]:
    """Load patient data from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_saved_patients() -> List[Dict[str, str]]:
    """Get list of saved patient files."""
    records_dir = create_patient_records_directory()
    patients = []
    
    for file_path in records_dir.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                patients.append({
                    'filepath': str(file_path),
                    'filename': file_path.name,
                    'name': data.get('name', 'Unknown'),
                    'patient_id': data.get('patient_id', 'Unknown'),
                    'age': data.get('age', 'Unknown'),
                    'gender': data.get('gender', 'Unknown'),
                    'last_modified': data.get('last_modified', 'Unknown'),
                    'diagnoses_count': len(data.get('diagnoses', [])),
                    'medications_count': len(data.get('current_medications', data.get('medications', [])))
                })
        except Exception as e:
            st.error(f"Error reading {file_path.name}: {e}")
    
    return sorted(patients, key=lambda x: x['last_modified'], reverse=True)

def validate_patient_input(patient_data: Dict[str, Any]) -> List[str]:
    """Validate patient input data."""
    errors = []
    
    # Required fields
    if not patient_data.get('patient_id', '').strip():
        errors.append("Patient ID is required")
    
    if not patient_data.get('name', '').strip():
        errors.append("Patient name is required")
    
    if not patient_data.get('age') or patient_data['age'] <= 0:
        errors.append("Valid age is required")
    
    if not patient_data.get('gender', '').strip():
        errors.append("Gender is required")
    
    return errors

def patient_management_page():
    """Display patient management page."""
    st.header("👥 Patient Records Management")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("➕ Add New Patient", type="primary", use_container_width=True):
            st.session_state.mode = 'new_patient'
            st.rerun()
    
    with col1:
        st.subheader("📁 Existing Patient Records")
    
    # Get saved patients
    patients = get_saved_patients()
    
    if not patients:
        st.info("No patient records found. Click 'Add New Patient' to create the first record.")
        return
    
    # Display patients in a grid
    cols = st.columns(2)
    for i, patient in enumerate(patients):
        with cols[i % 2]:
            # Create patient card
            is_selected = st.session_state.selected_patient == patient['filepath']
            card_class = "patient-card selected-patient" if is_selected else "patient-card"
            
            with st.container():
                # Patient info display
                st.markdown(f"""
                <div class="{card_class}">
                    <h4>👤 {patient['name']}</h4>
                    <p><strong>ID:</strong> {patient['patient_id']} | <strong>Age:</strong> {patient['age']} | <strong>Gender:</strong> {patient['gender']}</p>
                    <p><strong>Conditions:</strong> {patient['diagnoses_count']} | <strong>Medications:</strong> {patient['medications_count']}</p>
                    <p><small>Last modified: {patient['last_modified'][:10]}</small></p>
                </div>
                """, unsafe_allow_html=True)
                
                # Action buttons
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if st.button("📋 View", key=f"view_{i}", use_container_width=True):
                        st.session_state.selected_patient = patient['filepath']
                        st.session_state.patient_data = load_patient_data_from_file(patient['filepath'])
                        with st.expander("Patient Details", expanded=True):
                            st.json(st.session_state.patient_data)
                
                with col_b:
                    if st.button("🔍 Analyze", key=f"analyze_{i}", use_container_width=True):
                        st.session_state.selected_patient = patient['filepath']
                        st.session_state.patient_data = load_patient_data_from_file(patient['filepath'])
                        st.session_state.mode = 'analysis'
                        st.rerun()
                
                with col_c:
                    if st.button("✏️ Edit", key=f"edit_{i}", use_container_width=True):
                        st.session_state.selected_patient = patient['filepath']
                        st.session_state.patient_data = load_patient_data_from_file(patient['filepath'])
                        st.session_state.mode = 'edit_patient'
                        st.rerun()

def create_patient_form(edit_mode=False, existing_data=None) -> Dict[str, Any]:
    """Create comprehensive patient input form based on clinical requirements."""
    
    if edit_mode and existing_data:
        st.header("✏️ Edit Patient Data")
        st.markdown("Update patient information.")
    else:
        st.header("➕ Add New Patient")
        st.markdown("Enter detailed patient information for clinical decision support.")
    
    # Sample patient data for quick testing
    sample_patients = {
        "Margaret Johnson (68F - Diabetes, HTN, Afib)": {
            'patient_id': 'P001234',
            'name': 'Margaret Johnson',
            'age': 68,
            'gender': 'Female',
            'diagnoses': ['Type 2 Diabetes Mellitus', 'Essential Hypertension', 'Atrial Fibrillation', 'Chronic Kidney Disease Stage 3'],
            'symptoms': ['Occasional chest palpitations', 'Mild fatigue', 'Frequent urination'],
            'current_medications': [
                'Metformin 1000mg twice daily',
                'Lisinopril 10mg daily', 
                'Simvastatin 40mg daily',
                'Warfarin 5mg daily (newly prescribed)'
            ],
            'allergies': ['Penicillin - rash', 'Sulfa drugs - nausea'],
            'vital_signs': {
                'blood_pressure': '145/92',
                'heart_rate': 78,
                'temperature': 98.4,
                'respiratory_rate': 18,
                'oxygen_saturation': 97,
                'height': 165.0,
                'weight': 82.0,
                'bmi': 30.1,
                'pain_scale': 2
            },
            'lab_results': {
                'hba1c': 7.8,
                'fasting_glucose': 145,
                'total_cholesterol': 220,
                'ldl_cholesterol': 135,
                'hdl_cholesterol': 45,
                'triglycerides': 180,
                'creatinine': 1.3,
                'egfr': 55,
                'hemoglobin': 12.1,
                'alt': 28,
                'bun': 22
            },
            'chief_complaint': 'Follow-up for diabetes management and new atrial fibrillation diagnosis',
            'family_history': 'Father: Type 2 DM, CAD\nMother: Hypertension, Stroke',
            'past_history': 'Cholecystectomy 2015, No previous hospitalizations for cardiac events'
        },
        "Robert Chen (72M - CAD, COPD)": {
            'patient_id': 'P005678', 
            'name': 'Robert Chen',
            'age': 72,
            'gender': 'Male',
            'diagnoses': ['Coronary Artery Disease', 'COPD Gold Stage II', 'Dyslipidemia', 'Osteoarthritis'],
            'symptoms': ['Exertional dyspnea', 'Morning cough with sputum', 'Joint stiffness'],
            'current_medications': [
                'Atorvastatin 40mg daily',
                'Metoprolol 50mg twice daily',
                'Tiotropium inhaler daily',
                'Albuterol inhaler as needed',
                'Aspirin 81mg daily'
            ],
            'allergies': ['Codeine - nausea and dizziness'],
            'vital_signs': {
                'blood_pressure': '138/85',
                'heart_rate': 68, 
                'temperature': 98.1,
                'respiratory_rate': 22,
                'oxygen_saturation': 94,
                'height': 175.0,
                'weight': 85.0,
                'bmi': 27.8,
                'pain_scale': 1
            },
            'lab_results': {
                'fasting_glucose': 95,
                'total_cholesterol': 180,
                'ldl_cholesterol': 95,
                'hdl_cholesterol': 42,
                'triglycerides': 160,
                'creatinine': 1.1,
                'egfr': 65,
                'hemoglobin': 13.8,
                'alt': 35,
                'bun': 18
            },
            'chief_complaint': 'Routine follow-up for CAD and COPD, reports increased shortness of breath',
            'family_history': 'Father: MI at age 65\nMother: Emphysema',
            'past_history': 'PCI with stent 2020, Former smoker (quit 5 years ago)'
        },
        "Sarah Williams (28F - Anxiety, Hypothyroid)": {
            'patient_id': 'P009123',
            'name': 'Sarah Williams', 
            'age': 28,
            'gender': 'Female',
            'diagnoses': ['Generalized Anxiety Disorder', 'Hypothyroidism', 'Iron Deficiency Anemia'],
            'symptoms': ['Persistent worry', 'Palpitations', 'Fatigue', 'Cold intolerance'],
            'current_medications': [
                'Sertraline 50mg daily',
                'Levothyroxine 75mcg daily',
                'Ferrous sulfate 325mg daily'
            ],
            'allergies': ['No known drug allergies'],
            'vital_signs': {
                'blood_pressure': '110/70',
                'heart_rate': 85,
                'temperature': 98.2,
                'respiratory_rate': 16,
                'oxygen_saturation': 99,
                'height': 160.0,
                'weight': 55.0,
                'bmi': 21.5,
                'pain_scale': 0
            },
            'lab_results': {
                'fasting_glucose': 88,
                'total_cholesterol': 165,
                'ldl_cholesterol': 85,
                'hdl_cholesterol': 65,
                'triglycerides': 95,
                'creatinine': 0.8,
                'egfr': 105,
                'hemoglobin': 11.2,
                'alt': 22,
                'bun': 12
            },
            'chief_complaint': 'Follow-up for anxiety management and thyroid function',
            'family_history': 'Mother: Hypothyroidism, Depression\nFather: Healthy',
            'past_history': 'No significant past medical history'
        },
        "James Rodriguez (85M - CHF, DM, CKD)": {
            'patient_id': 'P007890',
            'name': 'James Rodriguez',
            'age': 85,
            'gender': 'Male',
            'diagnoses': ['Congestive Heart Failure', 'Type 2 Diabetes', 'Chronic Kidney Disease Stage 4', 'Mild Cognitive Impairment'],
            'symptoms': ['Lower extremity edema', 'Shortness of breath on exertion', 'Occasional confusion'],
            'current_medications': [
                'Lisinopril 5mg daily',
                'Metoprolol 25mg twice daily', 
                'Furosemide 40mg daily',
                'Insulin glargine 20 units daily',
                'Insulin lispro with meals'
            ],
            'allergies': ['ACE inhibitor cough - previous dry cough with higher doses'],
            'vital_signs': {
                'blood_pressure': '125/78',
                'heart_rate': 65,
                'temperature': 98.0,
                'respiratory_rate': 20,
                'oxygen_saturation': 95,
                'height': 170.0,
                'weight': 78.0,
                'bmi': 27.0,
                'pain_scale': 3
            },
            'lab_results': {
                'hba1c': 8.1,
                'fasting_glucose': 165,
                'total_cholesterol': 155,
                'ldl_cholesterol': 85,
                'hdl_cholesterol': 38,
                'triglycerides': 140,
                'creatinine': 2.1,
                'egfr': 28,
                'hemoglobin': 10.8,
                'alt': 32,
                'bun': 35
            },
            'chief_complaint': 'Worsening heart failure symptoms, medication adjustment needed',
            'family_history': 'Extensive family history of diabetes and heart disease',
            'past_history': 'MI 2018, Multiple hospitalizations for CHF exacerbations'
        },
        "Emily Chen (45F - Breast Cancer Survivor)": {
            'patient_id': 'P010245',
            'name': 'Emily Chen',
            'age': 45,
            'gender': 'Female',
            'diagnoses': ['Breast Cancer (Stage II - in remission)', 'Osteoporosis', 'Chemotherapy-induced neuropathy', 'Depression'],
            'symptoms': ['Peripheral numbness in hands/feet', 'Fatigue', 'Joint pain', 'Mood changes'],
            'current_medications': [
                'Tamoxifen 20mg daily',
                'Calcium carbonate 1200mg daily',
                'Vitamin D3 2000 IU daily',
                'Gabapentin 300mg three times daily',
                'Sertraline 50mg daily'
            ],
            'allergies': ['Doxorubicin - severe cardiotoxicity reaction'],
            'vital_signs': {
                'blood_pressure': '125/78',
                'heart_rate': 88,
                'temperature': 98.6,
                'respiratory_rate': 16,
                'oxygen_saturation': 99,
                'height': 162.0,
                'weight': 58.0,
                'bmi': 22.1,
                'pain_scale': 4
            },
            'lab_results': {
                'fasting_glucose': 92,
                'total_cholesterol': 195,
                'ldl_cholesterol': 115,
                'hdl_cholesterol': 58,
                'triglycerides': 110,
                'creatinine': 0.9,
                'egfr': 95,
                'hemoglobin': 10.5,
                'alt': 35,
                'bun': 14
            },
            'chief_complaint': 'Routine oncology follow-up, reports worsening neuropathy symptoms',
            'family_history': 'Mother: Breast cancer at 52\nGrandmother (maternal): Ovarian cancer',
            'past_history': 'Right mastectomy 2022, Chemotherapy completed 2023, Radiation therapy completed 2023'
        },
        "David Rodriguez (19M - Type 1 Diabetes)": {
            'patient_id': 'P011678',
            'name': 'David Rodriguez',
            'age': 19,
            'gender': 'Male',
            'diagnoses': ['Type 1 Diabetes Mellitus', 'Diabetic Ketoacidosis (recent episode)', 'Depression'],
            'symptoms': ['Frequent urination', 'Excessive thirst', 'Weight loss', 'Fatigue'],
            'current_medications': [
                'Insulin glargine 22 units at bedtime',
                'Insulin lispro with meals (carb ratio 1:12)',
                'Metformin 500mg twice daily',
                'Fluoxetine 20mg daily'
            ],
            'allergies': ['No known drug allergies'],
            'vital_signs': {
                'blood_pressure': '118/72',
                'heart_rate': 92,
                'temperature': 98.8,
                'respiratory_rate': 18,
                'oxygen_saturation': 98,
                'height': 175.0,
                'weight': 65.0,
                'bmi': 21.2,
                'pain_scale': 0
            },
            'lab_results': {
                'hba1c': 9.2,
                'fasting_glucose': 185,
                'total_cholesterol': 160,
                'ldl_cholesterol': 95,
                'hdl_cholesterol': 45,
                'triglycerides': 100,
                'creatinine': 0.8,
                'egfr': 120,
                'hemoglobin': 13.8,
                'alt': 22,
                'bun': 12
            },
            'chief_complaint': 'Follow-up after recent DKA hospitalization, diabetes management',
            'family_history': 'Father: Type 2 DM\nMother: Healthy\nGrandfather (paternal): Type 1 DM',
            'past_history': 'Diagnosed with T1DM at age 12, Recent DKA hospitalization 2 weeks ago'
        },
        "Linda Thompson (62F - COPD, Depression)": {
            'patient_id': 'P012890',
            'name': 'Linda Thompson',
            'age': 62,
            'gender': 'Female',
            'diagnoses': ['COPD Gold Stage III', 'Major Depressive Disorder', 'Osteoporosis', 'Chronic Pain'],
            'symptoms': ['Chronic dyspnea', 'Productive cough', 'Low mood', 'Back pain'],
            'current_medications': [
                'Tiotropium/Olodaterol inhaler daily',
                'Albuterol inhaler as needed',
                'Prednisone 10mg daily',
                'Venlafaxine 150mg daily',
                'Tramadol 50mg twice daily',
                'Alendronate 70mg weekly'
            ],
            'allergies': ['Morphine - respiratory depression', 'Latex - contact dermatitis'],
            'vital_signs': {
                'blood_pressure': '142/88',
                'heart_rate': 95,
                'temperature': 98.2,
                'respiratory_rate': 24,
                'oxygen_saturation': 91,
                'height': 158.0,
                'weight': 52.0,
                'bmi': 20.8,
                'pain_scale': 6
            },
            'lab_results': {
                'fasting_glucose': 105,
                'total_cholesterol': 210,
                'ldl_cholesterol': 130,
                'hdl_cholesterol': 48,
                'triglycerides': 160,
                'creatinine': 1.0,
                'egfr': 75,
                'hemoglobin': 11.8,
                'alt': 28,
                'bun': 18
            },
            'chief_complaint': 'Worsening shortness of breath and increased depression symptoms',
            'family_history': 'Father: Emphysema, died at 68\nMother: Depression',
            'past_history': 'Former smoker (2 packs/day for 40 years, quit 5 years ago), Multiple COPD exacerbations'
        },
        "Michael Kim (35M - Hypertension, Obesity)": {
            'patient_id': 'P013456',
            'name': 'Michael Kim',
            'age': 35,
            'gender': 'Male',
            'diagnoses': ['Essential Hypertension', 'Obesity Class II', 'Prediabetes', 'Sleep Apnea'],
            'symptoms': ['Headaches', 'Fatigue', 'Snoring', 'Daytime sleepiness'],
            'current_medications': [
                'Lisinopril 20mg daily',
                'Amlodipine 10mg daily',
                'Metformin 1000mg twice daily',
                'CPAP therapy nightly'
            ],
            'allergies': ['Hydrochlorothiazide - electrolyte imbalance'],
            'vital_signs': {
                'blood_pressure': '158/95',
                'heart_rate': 78,
                'temperature': 98.4,
                'respiratory_rate': 18,
                'oxygen_saturation': 96,
                'height': 178.0,
                'weight': 115.0,
                'bmi': 36.3,
                'pain_scale': 1
            },
            'lab_results': {
                'hba1c': 6.2,
                'fasting_glucose': 118,
                'total_cholesterol': 245,
                'ldl_cholesterol': 165,
                'hdl_cholesterol': 38,
                'triglycerides': 210,
                'creatinine': 1.1,
                'egfr': 85,
                'hemoglobin': 14.2,
                'alt': 45,
                'bun': 16
            },
            'chief_complaint': 'Poorly controlled blood pressure despite medications, weight management',
            'family_history': 'Father: HTN, Type 2 DM\nMother: Obesity, Sleep apnea',
            'past_history': 'No significant past medical history, Recent sleep study confirming severe OSA'
        },
        "Grace Williams (78F - Alzheimer's, Multiple Conditions)": {
            'patient_id': 'P014789',
            'name': 'Grace Williams',
            'age': 78,
            'gender': 'Female',
            'diagnoses': ['Alzheimers Disease (moderate stage)', 'Atrial Fibrillation', 'Hypertension', 'Osteoarthritis', 'Urinary Incontinence'],
            'symptoms': ['Memory loss', 'Confusion', 'Agitation', 'Joint pain', 'Frequent falls'],
            'current_medications': [
                'Donepezil 10mg daily',
                'Memantine 20mg daily',
                'Warfarin 3mg daily',
                'Metoprolol 25mg twice daily',
                'Acetaminophen 650mg three times daily',
                'Oxybutynin 5mg twice daily'
            ],
            'allergies': ['NSAIDs - GI bleeding', 'Haloperidol - extrapyramidal symptoms'],
            'vital_signs': {
                'blood_pressure': '135/80',
                'heart_rate': 88,
                'temperature': 97.8,
                'respiratory_rate': 16,
                'oxygen_saturation': 97,
                'height': 155.0,
                'weight': 60.0,
                'bmi': 25.0,
                'pain_scale': 3
            },
            'lab_results': {
                'fasting_glucose': 98,
                'total_cholesterol': 175,
                'ldl_cholesterol': 105,
                'hdl_cholesterol': 55,
                'triglycerides': 125,
                'creatinine': 1.2,
                'egfr': 65,
                'hemoglobin': 11.5,
                'alt': 25,
                'bun': 20
            },
            'chief_complaint': 'Increased confusion and agitation, medication review needed',
            'family_history': 'Mother: Dementia\nFather: Stroke',
            'past_history': 'Hip fracture 2022, Multiple falls, Progressive cognitive decline over 3 years'
        }
    }
    
    # Sample data selector
    with st.expander("📋 Load Sample Patient Data for Testing", expanded=False):
        st.markdown("**Quick start with pre-configured patient scenarios:**")
        
        cols = st.columns(2)
        for i, (patient_name, patient_data) in enumerate(sample_patients.items()):
            col = cols[i % 2]
            with col:
                if st.button(f"📝 {patient_name}", key=f"load_sample_{i}", help=f"Load sample data for {patient_data['name']}"):
                    # Store sample data in session state for pre-filling
                    st.session_state.sample_data = patient_data
                    st.success(f"✅ Loaded sample data for {patient_data['name']}")
                    st.rerun()
        
        if st.button("🗑️ Clear All Fields", key="clear_form"):
            if 'sample_data' in st.session_state:
                del st.session_state.sample_data
            st.success("✅ Form cleared")
            st.rerun()
    
    # Pre-fill data if editing or sample data selected
    default_data = existing_data if edit_mode and existing_data else {}
    if hasattr(st.session_state, 'sample_data'):
        default_data = st.session_state.sample_data
    
    with st.form("patient_form"):
        # 1. Patient Identification
        st.subheader("👤 Patient Identification")
        col1, col2 = st.columns(2)
        
        with col1:
            patient_id = st.text_input("Patient ID / MRN*", value=default_data.get('patient_id', ''), placeholder="e.g., P12345")
            name = st.text_input("Full Name*", value=default_data.get('name', ''), placeholder="John Doe")
            
            # Handle date of birth
            default_dob = datetime(1970, 1, 1)
            if default_data.get('date_of_birth'):
                try:
                    default_dob = datetime.fromisoformat(default_data['date_of_birth'])
                except:
                    pass
            date_of_birth = st.date_input("Date of Birth", value=default_dob)
            
        with col2:
            age = st.number_input("Age*", min_value=0, max_value=120, value=default_data.get('age', 30))
            gender = st.selectbox("Gender/Sex*", ["", "Male", "Female", "Other"], 
                                index=["", "Male", "Female", "Other"].index(default_data.get('gender', '')) if default_data.get('gender') in ["", "Male", "Female", "Other"] else 0)
            
        # 2. Medical History
        st.subheader("🩺 Medical History")
        col3, col4 = st.columns(2)
        
        with col3:
            st.write("**Current Diagnoses/Conditions:**")
            diagnoses_list = default_data.get('diagnoses', [])
            diagnoses_text = st.text_area("Diagnoses", value='\n'.join(diagnoses_list), placeholder="Type 2 Diabetes\nHypertension\nAsthma", height=100)
            
            st.write("**Current Symptoms:**")
            symptoms_list = default_data.get('symptoms', [])
            symptoms_text = st.text_area("Symptoms", value='\n'.join(symptoms_list), placeholder="Chest pain\nShortness of breath\nFatigue", height=80)
            
        with col4:
            st.write("**Family History:**")
            family_history = st.text_area("Family History", value=default_data.get('family_history', ''), placeholder="Father: Heart disease\nMother: Diabetes", height=100)
            
            st.write("**Past Medical History:**")
            past_history = st.text_area("Past History", value=default_data.get('past_history', ''), placeholder="Previous surgeries, hospitalizations", height=80)
        
        # 3. Medications & Allergies
        st.subheader("💊 Medications & Allergies")
        col5, col6 = st.columns(2)
        
        with col5:
            st.write("**Current Medications:**")
            # Convert current medications to text format
            current_meds_list = default_data.get('current_medications', [])
            current_meds_text = []
            for med in current_meds_list:
                if isinstance(med, dict):
                    med_line = med.get('name', '')
                    if med.get('dosage'):
                        med_line += f" {med['dosage']}"
                    current_meds_text.append(med_line)
                else:
                    current_meds_text.append(str(med))
            
            current_meds = st.text_area("Current Medications", value='\n'.join(current_meds_text), placeholder="Metformin 500mg twice daily\nLisinopril 10mg daily\nAspirin 81mg daily", height=120)
            
            st.write("**Past Medications:**")
            past_meds_list = default_data.get('past_medications', [])
            past_meds_text = []
            for med in past_meds_list:
                if isinstance(med, dict):
                    past_meds_text.append(med.get('name', ''))
                else:
                    past_meds_text.append(str(med))
            
            past_meds = st.text_area("Past Medications", value='\n'.join(past_meds_text), placeholder="Previously tried medications", height=80)
            
        with col6:
            st.write("**Allergies & Adverse Reactions:**")
            # Convert allergies to text format
            allergies_list = default_data.get('allergies', [])
            allergies_text = []
            for allergy in allergies_list:
                if isinstance(allergy, dict):
                    allergen = allergy.get('allergen', '')
                    reaction = allergy.get('reaction', '')
                    if reaction and reaction != 'Unknown':
                        allergies_text.append(f"{allergen} - {reaction}")
                    else:
                        allergies_text.append(allergen)
                else:
                    allergies_text.append(str(allergy))
            
            allergies = st.text_area("Allergies", value='\n'.join(allergies_text), placeholder="Penicillin - rash\nSulfa - nausea", height=120)
            
            st.write("**Drug Intolerances:**")
            intolerances = st.text_area("Intolerances", placeholder="Medications that caused side effects", height=80)
        
        # 4. Vital Signs & Lab Results
        st.subheader("🔬 Vital Signs & Laboratory Results")
        
        # Pre-fill vital signs
        default_vital_signs = default_data.get('vital_signs', {})
        default_lab_results = default_data.get('lab_results', {})
        
        # Vital Signs Section - Expanded with more fields
        st.write("**Vital Signs:**")
        
        # Primary Vital Signs Row
        col_vs1, col_vs2, col_vs3, col_vs4 = st.columns(4)
        
        vital_signs = {}
        
        with col_vs1:
            st.markdown("**🩸 Blood Pressure & Pulse**")
            # Blood Pressure
            bp_value = default_vital_signs.get('blood_pressure', '120/80')
            if '/' in str(bp_value):
                try:
                    sys_val, dia_val = str(bp_value).split('/')
                    default_sys, default_dia = int(sys_val), int(dia_val)
                except:
                    default_sys, default_dia = 120, 80
            else:
                default_sys, default_dia = 120, 80
                
            systolic = st.number_input("Systolic BP (mmHg)", min_value=0, max_value=300, 
                                     value=default_sys, key="systolic_bp", help="Normal: 90-139")
            diastolic = st.number_input("Diastolic BP (mmHg)", min_value=0, max_value=200, 
                                      value=default_dia, key="diastolic_bp", help="Normal: 60-89")
            
            heart_rate = st.number_input("Heart Rate (bpm)", min_value=0, max_value=250, 
                                       value=default_vital_signs.get('heart_rate', 72), key="heart_rate", help="Normal: 60-100")
            
            if systolic > 0 and diastolic > 0:
                vital_signs['blood_pressure'] = f"{systolic}/{diastolic}"
            if heart_rate > 0:
                vital_signs['heart_rate'] = heart_rate
                
        with col_vs2:
            st.markdown("**🌡️ Temperature & Respiratory**")
            
            temperature = st.number_input("Temperature (°F)", min_value=0.0, max_value=120.0, 
                                        value=default_vital_signs.get('temperature', 98.6), step=0.1, 
                                        key="temperature", help="Normal: 97.8-99.1°F")
            
            resp_rate = st.number_input("Respiratory Rate (/min)", min_value=0, max_value=60, 
                                      value=default_vital_signs.get('respiratory_rate', 16), 
                                      key="resp_rate", help="Normal: 12-20")
            
            o2_sat = st.number_input("O2 Saturation (%)", min_value=0, max_value=100, 
                                   value=default_vital_signs.get('oxygen_saturation', 98), 
                                   key="o2_sat", help="Normal: >95%")
            
            if temperature > 0:
                vital_signs['temperature'] = temperature
            if resp_rate > 0:
                vital_signs['respiratory_rate'] = resp_rate
            if o2_sat > 0:
                vital_signs['oxygen_saturation'] = o2_sat
                
        with col_vs3:
            st.markdown("**📏 Anthropometric**")
            
            height = st.number_input("Height (cm)", min_value=0.0, max_value=300.0, 
                                   value=default_vital_signs.get('height', 170.0), step=0.1, 
                                   key="height", help="Adult average: 150-200cm")
            
            weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, 
                                   value=default_vital_signs.get('weight', 70.0), step=0.1, 
                                   key="weight", help="Adult range varies")
            
            # Auto-calculate BMI
            if height > 0 and weight > 0:
                bmi = weight / ((height/100) ** 2)
                vital_signs['bmi'] = round(bmi, 1)
                vital_signs['height'] = height
                vital_signs['weight'] = weight
                st.metric("BMI", f"{bmi:.1f}")
            
        with col_vs4:
            st.markdown("**🩹 Additional Vitals**")
            
            pain_scale = st.selectbox("Pain Scale (0-10)", 
                                    options=[0,1,2,3,4,5,6,7,8,9,10],
                                    index=default_vital_signs.get('pain_scale', 0), 
                                    key="pain_scale", help="0=No pain, 10=Severe")
            
            # Additional vital signs
            pulse_ox_temp = st.number_input("Pulse Ox Temp (°F)", min_value=0.0, max_value=120.0,
                                          value=default_vital_signs.get('pulse_ox_temp', 0.0), step=0.1,
                                          key="pulse_ox_temp", help="If using pulse oximeter")
            
            blood_glucose = st.number_input("Blood Glucose (mg/dL)", min_value=0, max_value=600,
                                          value=default_vital_signs.get('blood_glucose', 0),
                                          key="blood_glucose", help="Point-of-care testing")
            
            if pain_scale >= 0:
                vital_signs['pain_scale'] = pain_scale
            if pulse_ox_temp > 0:
                vital_signs['pulse_ox_temp'] = pulse_ox_temp
            if blood_glucose > 0:
                vital_signs['blood_glucose'] = blood_glucose
        
        st.markdown("---")  # Separator line
        
        # Additional Vital Signs Row
        st.write("**Additional Measurements:**")
        col_add1, col_add2, col_add3, col_add4 = st.columns(4)
        
        with col_add1:
            st.markdown("**💪 Physical Assessment**")
            
            head_circumference = st.number_input("Head Circumference (cm)", min_value=0.0, max_value=100.0,
                                               value=default_vital_signs.get('head_circumference', 0.0), step=0.1,
                                               key="head_circumference", help="Pediatric patients")
            
            waist_circumference = st.number_input("Waist Circumference (cm)", min_value=0.0, max_value=200.0,
                                                value=default_vital_signs.get('waist_circumference', 0.0), step=0.1,
                                                key="waist_circumference", help="Metabolic assessment")
            
            if head_circumference > 0:
                vital_signs['head_circumference'] = head_circumference
            if waist_circumference > 0:
                vital_signs['waist_circumference'] = waist_circumference
        
        with col_add2:
            st.markdown("**🫀 Cardiac Assessment**")
            
            map_pressure = st.number_input("MAP (mmHg)", min_value=0, max_value=200,
                                         value=default_vital_signs.get('map_pressure', 0),
                                         key="map_pressure", help="Mean Arterial Pressure")
            
            pulse_pressure = st.number_input("Pulse Pressure (mmHg)", min_value=0, max_value=150,
                                           value=default_vital_signs.get('pulse_pressure', 0),
                                           key="pulse_pressure", help="Systolic - Diastolic")
            
            if map_pressure > 0:
                vital_signs['map_pressure'] = map_pressure
            if pulse_pressure > 0:
                vital_signs['pulse_pressure'] = pulse_pressure
                
        with col_add3:
            st.markdown("**🫁 Respiratory Assessment**")
            
            peak_flow = st.number_input("Peak Flow (L/min)", min_value=0, max_value=1000,
                                      value=default_vital_signs.get('peak_flow', 0),
                                      key="peak_flow", help="Respiratory function")
            
            fio2 = st.number_input("FiO2 (%)", min_value=0, max_value=100,
                                 value=default_vital_signs.get('fio2', 0),
                                 key="fio2", help="Fraction of inspired oxygen")
            
            if peak_flow > 0:
                vital_signs['peak_flow'] = peak_flow
            if fio2 > 0:
                vital_signs['fio2'] = fio2
                
        with col_add4:
            st.markdown("**🧠 Neurological**")
            
            gcs_score = st.selectbox("Glasgow Coma Scale", 
                                   options=[0,3,4,5,6,7,8,9,10,11,12,13,14,15],
                                   index=0 if default_vital_signs.get('gcs_score', 0) == 0 else default_vital_signs.get('gcs_score', 15) - 3,
                                   key="gcs_score", help="3-15 scale")
            
            pupil_response = st.selectbox("Pupil Response", 
                                        options=["", "Normal", "Sluggish", "Non-reactive", "Unequal"],
                                        index=0, key="pupil_response")
            
            if gcs_score > 0:
                vital_signs['gcs_score'] = gcs_score
            if pupil_response:
                vital_signs['pupil_response'] = pupil_response
        
        st.markdown("---")  # Separator line
        
        # Laboratory Results Section - Comprehensive and expandable
        st.write("**Laboratory Results:**")
        
        lab_results = {}
        
        # Basic Metabolic Panel
        st.markdown("**🔬 Basic Metabolic Panel (BMP)**")
        col_bmp1, col_bmp2, col_bmp3, col_bmp4 = st.columns(4)
        
        with col_bmp1:
            glucose = st.number_input("Glucose (mg/dL)", min_value=0, max_value=1000, 
                                    value=default_lab_results.get('fasting_glucose', 0), 
                                    key="fasting_glucose", help="Normal: 70-100 mg/dL")
            
            bun = st.number_input("BUN (mg/dL)", min_value=0, max_value=200,
                                value=default_lab_results.get('bun', 0), 
                                key="bun", help="Normal: 7-20 mg/dL")
            
            if glucose > 0:
                lab_results['fasting_glucose'] = glucose
            if bun > 0:
                lab_results['bun'] = bun
                
        with col_bmp2:
            creatinine = st.number_input("Creatinine (mg/dL)", min_value=0.0, max_value=15.0, 
                                       value=default_lab_results.get('creatinine', 0.0), step=0.01, 
                                       key="creatinine", help="Normal: 0.6-1.3 mg/dL")
            
            sodium = st.number_input("Sodium (mEq/L)", min_value=0, max_value=200,
                                   value=default_lab_results.get('sodium', 0),
                                   key="sodium", help="Normal: 136-145 mEq/L")
            
            if creatinine > 0:
                lab_results['creatinine'] = creatinine
            if sodium > 0:
                lab_results['sodium'] = sodium
                
        with col_bmp3:
            potassium = st.number_input("Potassium (mEq/L)", min_value=0.0, max_value=10.0,
                                      value=default_lab_results.get('potassium', 0.0), step=0.1,
                                      key="potassium", help="Normal: 3.5-5.0 mEq/L")
            
            chloride = st.number_input("Chloride (mEq/L)", min_value=0, max_value=150,
                                     value=default_lab_results.get('chloride', 0),
                                     key="chloride", help="Normal: 98-107 mEq/L")
            
            if potassium > 0:
                lab_results['potassium'] = potassium
            if chloride > 0:
                lab_results['chloride'] = chloride
                
        with col_bmp4:
            co2 = st.number_input("CO2 (mEq/L)", min_value=0, max_value=50,
                                value=default_lab_results.get('co2', 0),
                                key="co2", help="Normal: 22-28 mEq/L")
            
            egfr = st.number_input("eGFR (mL/min/1.73m²)", min_value=0, max_value=200, 
                                 value=default_lab_results.get('egfr', 0), 
                                 key="egfr", help="Normal: >90 mL/min/1.73m²")
            
            if co2 > 0:
                lab_results['co2'] = co2
            if egfr > 0:
                lab_results['egfr'] = egfr
        
        # Complete Blood Count (CBC)
        st.markdown("**� Complete Blood Count (CBC)**")
        col_cbc1, col_cbc2, col_cbc3, col_cbc4 = st.columns(4)
        
        with col_cbc1:
            hemoglobin = st.number_input("Hemoglobin (g/dL)", min_value=0.0, max_value=25.0,
                                       value=default_lab_results.get('hemoglobin', 0.0), step=0.1,
                                       key="hemoglobin", help="Normal: 12-16 g/dL")
            
            hematocrit = st.number_input("Hematocrit (%)", min_value=0.0, max_value=100.0,
                                       value=default_lab_results.get('hematocrit', 0.0), step=0.1,
                                       key="hematocrit", help="Normal: 36-46%")
            
            if hemoglobin > 0:
                lab_results['hemoglobin'] = hemoglobin
            if hematocrit > 0:
                lab_results['hematocrit'] = hematocrit
                
        with col_cbc2:
            wbc = st.number_input("WBC (×10³/μL)", min_value=0.0, max_value=100.0,
                                value=default_lab_results.get('wbc', 0.0), step=0.1,
                                key="wbc", help="Normal: 4.5-11.0 ×10³/μL")
            
            rbc = st.number_input("RBC (×10⁶/μL)", min_value=0.0, max_value=10.0,
                                value=default_lab_results.get('rbc', 0.0), step=0.01,
                                key="rbc", help="Normal: 4.2-5.4 ×10⁶/μL")
            
            if wbc > 0:
                lab_results['wbc'] = wbc
            if rbc > 0:
                lab_results['rbc'] = rbc
                
        with col_cbc3:
            platelets = st.number_input("Platelets (×10³/μL)", min_value=0, max_value=2000,
                                      value=default_lab_results.get('platelets', 0),
                                      key="platelets", help="Normal: 150-450 ×10³/μL")
            
            mcv = st.number_input("MCV (fL)", min_value=0.0, max_value=150.0,
                                value=default_lab_results.get('mcv', 0.0), step=0.1,
                                key="mcv", help="Normal: 80-100 fL")
            
            if platelets > 0:
                lab_results['platelets'] = platelets
            if mcv > 0:
                lab_results['mcv'] = mcv
                
        with col_cbc4:
            mch = st.number_input("MCH (pg)", min_value=0.0, max_value=50.0,
                                value=default_lab_results.get('mch', 0.0), step=0.1,
                                key="mch", help="Normal: 27-31 pg")
            
            mchc = st.number_input("MCHC (g/dL)", min_value=0.0, max_value=50.0,
                                 value=default_lab_results.get('mchc', 0.0), step=0.1,
                                 key="mchc", help="Normal: 32-36 g/dL")
            
            if mch > 0:
                lab_results['mch'] = mch
            if mchc > 0:
                lab_results['mchc'] = mchc
        
        # Lipid Panel
        st.markdown("**� Lipid Panel**")
        col_lipid1, col_lipid2, col_lipid3, col_lipid4 = st.columns(4)
        
        with col_lipid1:
            total_chol = st.number_input("Total Cholesterol (mg/dL)", min_value=0, max_value=500, 
                                       value=default_lab_results.get('total_cholesterol', 0), 
                                       key="total_cholesterol", help="Normal: <200 mg/dL")
            
            if total_chol > 0:
                lab_results['total_cholesterol'] = total_chol
                
        with col_lipid2:
            ldl = st.number_input("LDL Cholesterol (mg/dL)", min_value=0, max_value=400, 
                                value=default_lab_results.get('ldl_cholesterol', 0), 
                                key="ldl_cholesterol", help="Normal: <100 mg/dL")
            
            if ldl > 0:
                lab_results['ldl_cholesterol'] = ldl
                
        with col_lipid3:
            hdl = st.number_input("HDL Cholesterol (mg/dL)", min_value=0, max_value=150, 
                                value=default_lab_results.get('hdl_cholesterol', 0), 
                                key="hdl_cholesterol", help="Normal: >40 mg/dL (M), >50 mg/dL (F)")
            
            if hdl > 0:
                lab_results['hdl_cholesterol'] = hdl
                
        with col_lipid4:
            triglycerides = st.number_input("Triglycerides (mg/dL)", min_value=0, max_value=1000, 
                                          value=default_lab_results.get('triglycerides', 0), 
                                          key="triglycerides", help="Normal: <150 mg/dL")
            
            if triglycerides > 0:
                lab_results['triglycerides'] = triglycerides
        
        # Additional Labs
        st.markdown("**🧪 Additional Laboratory Tests**")
        col_add_lab1, col_add_lab2, col_add_lab3, col_add_lab4 = st.columns(4)
        
        with col_add_lab1:
            st.markdown("**Diabetes Monitoring**")
            
            hba1c = st.number_input("HbA1c (%)", min_value=0.0, max_value=20.0, 
                                  value=default_lab_results.get('hba1c', 0.0), step=0.1, 
                                  key="hba1c", help="Normal: <5.7%")
            
            random_glucose = st.number_input("Random Glucose (mg/dL)", min_value=0, max_value=1000,
                                           value=default_lab_results.get('random_glucose', 0),
                                           key="random_glucose", help="Varies by timing")
            
            if hba1c > 0:
                lab_results['hba1c'] = hba1c
            if random_glucose > 0:
                lab_results['random_glucose'] = random_glucose
                
        with col_add_lab2:
            st.markdown("**Liver Function**")
            
            alt = st.number_input("ALT (U/L)", min_value=0, max_value=500,
                                value=default_lab_results.get('alt', 0),
                                key="alt", help="Normal: 7-40 U/L")
            
            ast = st.number_input("AST (U/L)", min_value=0, max_value=500,
                                value=default_lab_results.get('ast', 0),
                                key="ast", help="Normal: 10-40 U/L")
            
            if alt > 0:
                lab_results['alt'] = alt
            if ast > 0:
                lab_results['ast'] = ast
                
        with col_add_lab3:
            st.markdown("**Thyroid Function**")
            
            tsh = st.number_input("TSH (mIU/L)", min_value=0.0, max_value=100.0,
                                value=default_lab_results.get('tsh', 0.0), step=0.01,
                                key="tsh", help="Normal: 0.4-4.0 mIU/L")
            
            free_t4 = st.number_input("Free T4 (ng/dL)", min_value=0.0, max_value=10.0,
                                    value=default_lab_results.get('free_t4', 0.0), step=0.01,
                                    key="free_t4", help="Normal: 0.8-1.8 ng/dL")
            
            if tsh > 0:
                lab_results['tsh'] = tsh
            if free_t4 > 0:
                lab_results['free_t4'] = free_t4
                
        with col_add_lab4:
            st.markdown("**Other Tests**")
            
            psa = st.number_input("PSA (ng/mL)", min_value=0.0, max_value=100.0,
                                value=default_lab_results.get('psa', 0.0), step=0.1,
                                key="psa", help="Age-dependent normal ranges")
            
            vitamin_d = st.number_input("Vitamin D (ng/mL)", min_value=0.0, max_value=200.0,
                                      value=default_lab_results.get('vitamin_d', 0.0), step=0.1,
                                      key="vitamin_d", help="Normal: 30-100 ng/mL")
            
            if psa > 0:
                lab_results['psa'] = psa
            if vitamin_d > 0:
                lab_results['vitamin_d'] = vitamin_d
        
        # Free text area for additional lab results
        st.markdown("**📋 Additional Lab Results (Free Text)**")
        additional_labs = st.text_area("Other Laboratory Results", 
                                     value=default_lab_results.get('additional_labs', ''), 
                                     placeholder="Enter any additional lab results not listed above...",
                                     height=80, key="additional_labs",
                                     help="Format: Test Name: Result (Units) - Reference Range")
        
        if additional_labs:
            lab_results['additional_labs'] = additional_labs
        
        # 5. Additional Information
        st.subheader("📝 Clinical Notes")
        chief_complaint = st.text_area("Chief Complaint", value=default_data.get('chief_complaint', ''), placeholder="Patient reports chest pain for 2 days...")
        clinical_notes = st.text_area("Additional Clinical Notes", value=default_data.get('notes', ''), placeholder="Any other relevant clinical information...", height=100)
        
        # Submit buttons
        col_submit1, col_submit2 = st.columns(2)
        
        with col_submit1:
            submitted = st.form_submit_button("💾 Save Patient Data", type="primary")
            
        with col_submit2:
            cancel = st.form_submit_button("❌ Cancel")
        
        if cancel:
            st.session_state.mode = 'patient_management'
            st.rerun()
        
        if submitted:
            # Process form data
            diagnoses_list = [d.strip() for d in diagnoses_text.split('\n') if d.strip()] if diagnoses_text else []
            symptoms_list = [s.strip() for s in symptoms_text.split('\n') if s.strip()] if symptoms_text else []
            
            # Process medications
            current_medications = []
            if current_meds:
                for med_line in current_meds.split('\n'):
                    med_line = med_line.strip()
                    if med_line:
                        # Try to parse medication name and dosage
                        parts = med_line.split(' ', 1)
                        med_name = parts[0]
                        dosage = parts[1] if len(parts) > 1 else ""
                        current_medications.append({
                            'name': med_name,
                            'dosage': dosage,
                            'status': 'active'
                        })
            
            past_medications = []
            if past_meds:
                for med_line in past_meds.split('\n'):
                    med_line = med_line.strip()
                    if med_line:
                        past_medications.append({
                            'name': med_line,
                            'status': 'discontinued'
                        })
            
            # Process allergies
            allergies_list = []
            if allergies:
                for allergy_line in allergies.split('\n'):
                    allergy_line = allergy_line.strip()
                    if allergy_line:
                        if ' - ' in allergy_line:
                            allergen, reaction = allergy_line.split(' - ', 1)
                            allergies_list.append({
                                'allergen': allergen.strip(),
                                'reaction': reaction.strip()
                            })
                        else:
                            allergies_list.append({
                                'allergen': allergy_line,
                                'reaction': 'Unknown'
                            })
            
            # Compile patient data according to the specified JSON structure
            patient_data = {
                'patient_id': patient_id.strip(),
                'name': name.strip(),
                'age': age,
                'date_of_birth': date_of_birth.isoformat() if date_of_birth else None,
                'gender': gender,
                'diagnoses': diagnoses_list,
                'symptoms': symptoms_list,
                'medications': current_medications + past_medications,
                'current_medications': current_medications,
                'past_medications': past_medications,
                'allergies': allergies_list,
                'vital_signs': vital_signs,
                'lab_results': lab_results,
                'family_history': family_history,
                'past_history': past_history,
                'chief_complaint': chief_complaint,
                'notes': clinical_notes,
                'created_at': default_data.get('created_at', datetime.now().isoformat()),
                'last_modified': datetime.now().isoformat()
            }
            
            # Validate input
            validation_errors = validate_patient_input(patient_data)
            if validation_errors:
                st.error("Please correct the following errors:")
                for error in validation_errors:
                    st.error(f"• {error}")
                return None
            
            return patient_data
    
    return None

def run_clinical_analysis(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run comprehensive clinical analysis using orchestrator."""
    
    if not ORCHESTRATOR_AVAILABLE:
        st.error("❌ Clinical orchestrator is not available. Please check the installation.")
        return None
    
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Load and validate patient data
        status_text.text("Step 1/5: Loading patient data...")
        processed_patient = load_patient_data(patient_data)
        progress_bar.progress(20)
        time.sleep(0.5)
        
        # Step 2: Get guidelines recommendations
        status_text.text("Step 2/5: Analyzing clinical guidelines...")
        guidelines_result = get_guidelines_recommendations(processed_patient)
        progress_bar.progress(40)
        time.sleep(0.5)
        
        # Step 3: Analyze drug safety
        status_text.text("Step 3/5: Analyzing drug safety...")
        drug_safety_result = analyze_drug_safety(processed_patient)
        progress_bar.progress(60)
        time.sleep(0.5)
        
        # Step 4: Fetch research evidence
        status_text.text("Step 4/5: Fetching research evidence...")
        research_result = fetch_research(processed_patient)
        progress_bar.progress(80)
        time.sleep(0.5)
        
        # Step 5: Merge outputs and apply bias mitigation
        status_text.text("Step 5/5: Integrating results and applying bias mitigation...")
        
        # Merge module outputs
        merged_recommendations = merge_module_outputs(
            guidelines_result,
            drug_safety_result,
            research_result,
            patient_data['patient_id']
        )
        
        # Apply bias mitigation
        final_results = apply_bias_mitigation(merged_recommendations, processed_patient)
        
        progress_bar.progress(100)
        status_text.text("✅ Analysis complete!")
        
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
        return final_results
        
    except Exception as e:
        st.error(f"❌ Error during analysis: {str(e)}")
        st.error("Full error details:")
        st.code(traceback.format_exc())
        return None

def download_doctor_summary(summary_content: str, patient_data: Dict[str, Any]):
    """Generate downloadable doctor summary PDF document"""
    
    # Create PDF buffer
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        textColor=colors.darkblue,
        alignment=1  # Center alignment
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=12,
        leftIndent=0,
        rightIndent=0
    )
    
    # Create story (content)
    story = []
    
    # Title
    story.append(Paragraph("CLINICAL SUMMARY", title_style))
    story.append(Spacer(1, 20))
    
    # Patient information table
    patient_info = [
        ['Patient:', patient_data.get('name', 'Unknown')],
        ['ID:', patient_data.get('patient_id', 'Unknown')],
        ['Age:', f"{patient_data.get('age', 'Unknown')} years"],
        ['Gender:', patient_data.get('gender', 'Unknown')],
        ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    ]
    
    patient_table = Table(patient_info, colWidths=[1.5*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    
    story.append(patient_table)
    story.append(Spacer(1, 30))
    
    # Clinical Summary Content
    story.append(Paragraph("Clinical Assessment", header_style))
    
    # Split summary content into paragraphs and format
    paragraphs = summary_content.split('\n\n')
    for para in paragraphs:
        if para.strip():
            # Handle markdown-style headers
            if para.startswith('###'):
                header_text = para.replace('###', '').strip()
                story.append(Paragraph(header_text, header_style))
            elif para.startswith('**') and para.endswith('**'):
                header_text = para.replace('**', '').strip()
                story.append(Paragraph(header_text, header_style))
            else:
                # Clean up the text for PDF
                clean_para = para.replace('**', '').replace('*', '•').strip()
                if clean_para:
                    story.append(Paragraph(clean_para, body_style))
            story.append(Spacer(1, 12))
    
    # Footer
    story.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    story.append(Paragraph("Generated by MedCare Clinical Decision Support System", footer_style))
    story.append(Paragraph("This summary is AI-generated and should be reviewed by a healthcare professional", footer_style))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Create download button
    st.download_button(
        label="📄 Download PDF Summary",
        data=pdf_data,
        file_name=f"doctor_summary_{patient_data.get('patient_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
        help="Download clinical summary as PDF for doctor",
        use_container_width=True
    )

def download_patient_education(education_content: str, patient_data: Dict[str, Any]):
    """Generate downloadable patient education PDF document"""
    
    # Create PDF buffer
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles for patient education
    title_style = ParagraphStyle(
        'PatientTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.darkgreen,
        alignment=1  # Center alignment
    )
    
    subtitle_style = ParagraphStyle(
        'PatientSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=15,
        textColor=colors.darkgreen,
        leftIndent=0
    )
    
    body_style = ParagraphStyle(
        'PatientBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        leftIndent=10,
        rightIndent=10,
        leading=14
    )
    
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        leftIndent=25,
        bulletIndent=10,
        bulletFontName='Symbol'
    )
    
    # Create story (content)
    story = []
    
    # Title with patient name
    story.append(Paragraph("YOUR HEALTH GUIDE", title_style))
    story.append(Paragraph(f"Personal Health Information for {patient_data.get('name', 'Patient')}", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Patient information box
    patient_info = [
        ['Patient Name:', patient_data.get('name', 'Unknown')],
        ['Age:', f"{patient_data.get('age', 'Unknown')} years"],
        ['Date Generated:', datetime.now().strftime('%B %d, %Y')]
    ]
    
    patient_table = Table(patient_info, colWidths=[2*inch, 3.5*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgreen),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.darkgreen),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
    ]))
    
    story.append(patient_table)
    story.append(Spacer(1, 25))
    
    # Process education content
    # Split content into sections
    sections = education_content.split('\n\n')
    
    for section in sections:
        if section.strip():
            # Handle markdown-style headers
            if section.startswith('# '):
                header_text = section.replace('# ', '').strip()
                story.append(Paragraph(header_text, title_style))
                story.append(Spacer(1, 15))
            elif section.startswith('## '):
                header_text = section.replace('## ', '').strip()
                story.append(Paragraph(header_text, subtitle_style))
                story.append(Spacer(1, 10))
            elif section.startswith('### '):
                header_text = section.replace('### ', '').strip()
                subheader_style = ParagraphStyle(
                    'SubHeader',
                    parent=styles['Heading3'],
                    fontSize=12,
                    spaceAfter=8,
                    textColor=colors.darkgreen,
                    fontName='Helvetica-Bold'
                )
                story.append(Paragraph(header_text, subheader_style))
            else:
                # Handle bullet points and regular text
                lines = section.split('\n')
                for line in lines:
                    line = line.strip()
                    if line:
                        if line.startswith('- ') or line.startswith('• '):
                            bullet_text = line.replace('- ', '').replace('• ', '')
                            story.append(Paragraph(f"• {bullet_text}", bullet_style))
                        elif line.startswith('**') and line.endswith('**'):
                            bold_text = line.replace('**', '')
                            bold_style = ParagraphStyle(
                                'Bold',
                                parent=body_style,
                                fontName='Helvetica-Bold'
                            )
                            story.append(Paragraph(bold_text, bold_style))
                        else:
                            # Clean up markdown formatting
                            clean_line = line.replace('**', '').replace('*', '')
                            if clean_line:
                                story.append(Paragraph(clean_line, body_style))
                
                story.append(Spacer(1, 12))
    
    # Important notice box
    story.append(Spacer(1, 20))
    notice_style = ParagraphStyle(
        'Notice',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.red,
        alignment=1,
        borderWidth=1,
        borderColor=colors.red,
        borderPadding=10
    )
    
    notice_data = [[Paragraph("IMPORTANT: This information is for educational purposes only. Always consult with your healthcare provider before making any changes to your treatment plan.", notice_style)]]
    notice_table = Table(notice_data, colWidths=[6*inch])
    notice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightyellow),
        ('BORDER', (0, 0), (-1, -1), 2, colors.red),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15)
    ]))
    
    story.append(notice_table)
    
    # Footer
    story.append(Spacer(1, 20))
    footer_style = ParagraphStyle(
        'PatientFooter',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=1
    )
    story.append(Paragraph("Generated by MedCare Clinical Decision Support System", footer_style))
    story.append(Paragraph("Please share this information with your healthcare team", footer_style))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Create download button
    st.download_button(
        label="📄 Download PDF Guide",
        data=pdf_data,
        file_name=f"patient_education_{patient_data.get('patient_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
        help="Download patient education material as PDF",
        use_container_width=True
    )

def display_clinical_report(results: Dict[str, Any], patient_data: Dict[str, Any]):
    """Display comprehensive clinical report."""
    
    st.header("📊 Clinical Decision Support Report")
    
    # Patient Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Patient", patient_data['name'])
        st.metric("ID", results['patient_id'])
    with col2:
        st.metric("Age", f"{patient_data['age']} years")
        st.metric("Gender", patient_data['gender'].title())
    with col3:
        st.metric("Total Recommendations", results['summary']['total_recommendations'])
        st.metric("Confidence Score", f"{results['summary']['confidence_score']:.1%}")
    
    # Display results in tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🎯 Summary", "💊 Drug Safety", "📖 Guidelines", "🔬 Research", "👨‍⚕️ Doctor Summary", "👤 Patient Education"])
    
    with tab1:
        st.subheader("Executive Summary")
        summary = results['summary']
        st.write(f"**Total Recommendations:** {summary['total_recommendations']}")
        st.write(f"**Highest Priority:** {summary['highest_priority']}")
        st.write(f"**Requires Immediate Action:** {'Yes' if summary['requires_immediate_action'] else 'No'}")
        st.write(f"**Confidence Score:** {summary['confidence_score']:.1%}")
        
        # Show critical alerts
        critical_alerts = results['unified_alerts'].get('critical', [])
        if critical_alerts:
            st.subheader("🚨 Critical Alerts")
            for alert in critical_alerts:
                st.error(f"**{alert['title']}**\n{alert['description']}")
    
    with tab2:
        st.subheader("💊 Drug Safety Analysis")
        drug_recs = results['recommendations']['drug_based']
        if drug_recs:
            for rec in drug_recs:
                with st.expander(f"🔹 {rec['title']}", expanded=False):
                    st.write(f"**Priority:** {rec['priority']}")
                    st.write(f"**Description:** {rec['description']}")
                    st.write(f"**Relevance Score:** {rec['relevance_score']:.1%}")
        else:
            st.info("No drug safety recommendations available")
    
    with tab3:
        st.subheader("📖 Clinical Guidelines")
        guideline_recs = results['recommendations']['guideline_based']
        if guideline_recs:
            for rec in guideline_recs:
                with st.expander(f"🔹 {rec['title']}", expanded=False):
                    st.write(f"**Priority:** {rec['priority']}")
                    st.write(f"**Description:** {rec['description']}")
                    st.write(f"**Relevance Score:** {rec['relevance_score']:.1%}")
        else:
            st.info("No clinical guideline recommendations available")
    
    with tab4:
        st.subheader("🔬 Research Evidence")
        research_recs = results['recommendations']['research_based']
        
        # Display PubMed Research Results
        pubmed_research = None
        for rec in research_recs:
            if rec.get('evidence_source') == 'pubmed_literature' and 'supporting_studies' in rec:
                pubmed_research = rec
                break
        
        if pubmed_research:
            st.markdown("### 📚 PubMed Literature Evidence")
            
            with st.expander("🔹 PubMed Research Summary", expanded=True):
                st.write(f"**Priority:** {pubmed_research['priority']}")
                st.write(f"**Clinical Summary:** {pubmed_research['description']}")
                st.write(f"**Relevance Score:** {pubmed_research['relevance_score']:.1%}")
                
                if pubmed_research.get('action_items'):
                    st.write("**Recommended Actions:**")
                    for action in pubmed_research['action_items']:
                        st.write(f"• {action}")
            
            st.markdown("#### 📄 Supporting Research Studies")
            
            # Display supporting studies in a more structured format
            studies = pubmed_research.get('supporting_studies', [])
            for i, study in enumerate(studies):
                with st.expander(f"Study {i+1}: {study['title'][:100]}{'...' if len(study['title']) > 100 else ''}", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Title:** {study['title']}")
                        st.write(f"**Abstract Excerpt:** {study['snippet']}")
                        
                    with col2:
                        st.metric("PMID", study['pmid'])
                        st.write(f"**Published:** {study.get('pubdate', 'Unknown')}")
                        st.write(f"**Relevance:** {study.get('relevance', 'Medium')}")
                        
                        if study.get('doi'):
                            st.markdown(f"**DOI:** [{study['doi']}](https://doi.org/{study['doi']})")
                        
                        # PubMed link
                        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{study['pmid']}"
                        st.markdown(f"**Link:** [View on PubMed]({pubmed_url})")
        
        # Display other research recommendations
        other_research_recs = [rec for rec in research_recs if rec.get('evidence_source') != 'pubmed_literature']
        
        if other_research_recs:
            st.markdown("### 📖 Additional Research Evidence")
            for rec in other_research_recs:
                with st.expander(f"🔹 {rec['title']}", expanded=False):
                    st.write(f"**Priority:** {rec['priority']}")
                    st.write(f"**Description:** {rec['description']}")
                    st.write(f"**Evidence Source:** {rec.get('evidence_source', 'Unknown')}")
                    st.write(f"**Relevance Score:** {rec['relevance_score']:.1%}")
                    
                    if rec.get('action_items'):
                        st.write("**Action Items:**")
                        for action in rec['action_items']:
                            st.write(f"• {action}")
        
        # Display recent studies summary if available
        research_module_data = None
        for module_result in [results.get('research_result', {})]:
            if module_result.get('recent_studies'):
                research_module_data = module_result
                break
        
        if research_module_data and research_module_data.get('recent_studies'):
            st.markdown("### 📊 Recent Studies Summary")
            
            studies_df = []
            for study in research_module_data['recent_studies']:
                studies_df.append({
                    'PMID': study.get('pmid', ''),
                    'Title': study.get('title', '')[:80] + ('...' if len(study.get('title', '')) > 80 else ''),
                    'Date': study.get('pubdate', ''),
                    'Relevance': study.get('clinical_relevance', 'Medium'),
                    'Score': f"{study.get('relevance_score', 0):.2f}"
                })
            
            if studies_df:
                import pandas as pd
                df = pd.DataFrame(studies_df)
                st.dataframe(df, use_container_width=True)
        
        if not research_recs:
            st.info("No research-based recommendations available. This may indicate that PubMed integration is not configured or no relevant studies were found.")
    
    with tab5:
        st.subheader("👨‍⚕️ Clinical Summary for Doctor")
        
        # Generate doctor summary if not already available
        if 'doctor_summary' not in results:
            with st.spinner("Generating AI-powered clinical summary..."):
                from core.clinical_engine import generate_doctor_summary
                doctor_summary_result = generate_doctor_summary(patient_data, results)
                results['doctor_summary'] = doctor_summary_result
        
        doctor_summary = results.get('doctor_summary', {})
        
        if doctor_summary.get('success'):
            st.markdown("**AI-Generated Clinical Summary:**")
            st.write(doctor_summary['summary'])
            
            # Download button for doctor summary
            col1, col2 = st.columns([3, 1])
            with col2:
                download_doctor_summary(doctor_summary['summary'], patient_data)
            
            # Metadata
            with st.expander("📊 Generation Details"):
                st.write(f"**Generated at:** {doctor_summary.get('generated_at', 'Unknown')}")
                st.write(f"**Model used:** {doctor_summary.get('model_used', 'Unknown')}")
                st.write(f"**Token count:** {doctor_summary.get('token_count', 'Unknown')}")
        else:
            st.error(f"Failed to generate doctor summary: {doctor_summary.get('error', 'Unknown error')}")
            if doctor_summary.get('fallback_summary'):
                st.write(doctor_summary['fallback_summary'])
    
    with tab6:
        st.subheader("👤 Patient Education Material")
        
        # Generate patient education if not already available
        if 'patient_education' not in results:
            with st.spinner("Generating patient-friendly education material..."):
                from core.clinical_engine import generate_patient_education
                education_result = generate_patient_education(patient_data, results)
                results['patient_education'] = education_result
        
        patient_education = results.get('patient_education', {})
        
        if patient_education.get('success'):
            st.markdown("**Patient-Friendly Health Information:**")
            st.write(patient_education['content'])
            
            # Download button for patient education
            col1, col2 = st.columns([3, 1])
            with col2:
                download_patient_education(patient_education['content'], patient_data)
            
            # Metadata
            with st.expander("📊 Generation Details"):
                st.write(f"**Generated at:** {patient_education.get('generated_at', 'Unknown')}")
                st.write(f"**Model used:** {patient_education.get('model_used', 'Unknown')}")
                st.write(f"**Patient friendly:** {patient_education.get('patient_friendly', 'Unknown')}")
                st.write(f"**Token count:** {patient_education.get('token_count', 'Unknown')}")
        else:
            st.error(f"Failed to generate patient education: {patient_education.get('error', 'Unknown error')}")
            if patient_education.get('fallback_content'):
                st.write(patient_education['fallback_content'])

# Main Application
def main():
    """Main application function."""
    
    # Sidebar
    with st.sidebar:
        st.title("🏥 CDSS Navigation")
        st.markdown("---")
        
        # Mode selection
        if st.button("👥 Patient Management", type="primary" if st.session_state.mode == 'patient_management' else "secondary", use_container_width=True):
            st.session_state.mode = 'patient_management'
            st.session_state.analysis_results = None
            st.rerun()
        
        if st.button("➕ New Patient", type="primary" if st.session_state.mode == 'new_patient' else "secondary", use_container_width=True):
            st.session_state.mode = 'new_patient'
            st.session_state.analysis_results = None
            st.rerun()
        
        st.markdown("---")
        
        # Current state info
        if st.session_state.selected_patient:
            st.success("✅ Patient Selected")
            if st.session_state.patient_data:
                st.write(f"**Name:** {st.session_state.patient_data.get('name', 'Unknown')}")
                st.write(f"**ID:** {st.session_state.patient_data.get('patient_id', 'Unknown')}")
        
        if st.session_state.analysis_results:
            st.success("✅ Analysis Complete")
            summary = st.session_state.analysis_results['summary']
            st.write(f"• Total Recs: {summary['total_recommendations']}")
            st.write(f"• Priority: {summary['highest_priority']}")
            st.write(f"• Confidence: {summary['confidence_score']:.1%}")
        
        st.markdown("---")
        st.markdown("### System Status")
        if ORCHESTRATOR_AVAILABLE:
            st.success("🟢 Orchestrator Online")
        else:
            st.error("🔴 Orchestrator Offline")
        
        st.markdown("### About")
        st.info("""
        This Clinical Decision Support System integrates:
        • Patient Data Management
        • Clinical Guidelines
        • Drug Safety Analysis  
        • Research Evidence
        • Bias Mitigation
        
        Version: 3.0
        """)
    
    # Main Content based on mode
    if st.session_state.mode == 'patient_management':
        patient_management_page()
    
    elif st.session_state.mode == 'new_patient':
        # Show patient input form
        patient_data = create_patient_form()
        
        if patient_data:
            # Save patient data
            filepath = save_patient_data(patient_data)
            st.success(f"✅ Patient data saved successfully to: `{filepath}`")
            
            # Update session state
            st.session_state.patient_data = patient_data
            st.session_state.selected_patient = filepath
            
            # Option to analyze immediately
            if st.button("🔍 Analyze This Patient Now", type="primary"):
                st.session_state.mode = 'analysis'
                st.rerun()
            
            if st.button("👥 Return to Patient Management"):
                st.session_state.mode = 'patient_management'
                st.rerun()
    
    elif st.session_state.mode == 'edit_patient':
        # Show patient edit form
        patient_data = create_patient_form(edit_mode=True, existing_data=st.session_state.patient_data)
        
        if patient_data:
            # Save updated patient data
            filepath = save_patient_data(patient_data)
            st.success(f"✅ Patient data updated successfully!")
            
            # Update session state
            st.session_state.patient_data = patient_data
            
            # Return to patient management
            if st.button("👥 Return to Patient Management"):
                st.session_state.mode = 'patient_management'
                st.rerun()
    
    elif st.session_state.mode == 'analysis':
        if st.session_state.patient_data is None:
            st.error("No patient data available for analysis. Please select a patient first.")
            if st.button("👥 Go to Patient Management"):
                st.session_state.mode = 'patient_management'
                st.rerun()
            return
        
        # Show analysis page
        st.header(f"🔍 Clinical Analysis for {st.session_state.patient_data.get('name', 'Unknown Patient')}")
        
        if st.session_state.analysis_results is None:
            # Run analysis
            if st.button("🚀 Start Clinical Analysis", type="primary"):
                with st.spinner("🔄 Running comprehensive clinical analysis..."):
                    results = run_clinical_analysis(st.session_state.patient_data)
                
                if results:
                    st.session_state.analysis_results = results
                    st.rerun()
        else:
            # Show results
            display_clinical_report(st.session_state.analysis_results, st.session_state.patient_data)
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Run New Analysis"):
                    st.session_state.analysis_results = None
                    st.rerun()
            
            with col2:
                # Download JSON report
                json_data = {
                    'patient_data': st.session_state.patient_data,
                    'analysis_results': st.session_state.analysis_results,
                    'generated_at': datetime.now().isoformat()
                }
                
                json_str = json.dumps(json_data, indent=2, default=str)
                
                st.download_button(
                    label="📄 Download Report (JSON)",
                    data=json_str,
                    file_name=f"clinical_report_{st.session_state.analysis_results['patient_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            with col3:
                if st.button("👥 Back to Patients"):
                    st.session_state.mode = 'patient_management'
                    st.session_state.analysis_results = None
                    st.rerun()

if __name__ == "__main__":
    main()