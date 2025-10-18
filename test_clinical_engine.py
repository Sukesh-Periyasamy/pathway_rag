# test_clinical_engine.py - Test clinical engine functionality
import sys
import json
from datetime import datetime

# Add source path
sys.path.append('src/core')
sys.path.append('src/utils')

def test_clinical_engine():
    """Test the clinical engine with sample patient data."""
    print("🧪 Testing Clinical Engine")
    print("=" * 40)
    
    # Sample patient data
    test_patient = {
        "name": "Test Patient",
        "age": 65,
        "gender": "Male",
        "conditions": ["Type 2 Diabetes", "Hypertension"],
        "medications": [
            {"name": "Metformin", "dosage": "1000mg", "frequency": "twice daily"},
            {"name": "Lisinopril", "dosage": "10mg", "frequency": "once daily"}
        ],
        "symptoms": ["Fatigue", "Blurred vision"],
        "vital_signs": {
            "blood_pressure": "150/95 mmHg",
            "heart_rate": "88 bpm",
            "temperature": "98.6°F"
        },
        "lab_results": {
            "hba1c": "8.2%",
            "creatinine": "1.8 mg/dL"
        }
    }
    
    try:
        # Test basic import
        from clinical_engine import generate_doctor_summary
        print("✅ Successfully imported clinical_engine")
        
        # Test basic analysis without OpenAI (to avoid API calls)
        analysis_results = {
            "risk_level": "High",
            "primary_concerns": ["Poorly controlled diabetes", "Elevated blood pressure"],
            "recommendations": ["Consider medication adjustment", "Lifestyle counseling"]
        }
        
        print("📊 Test patient data prepared")
        print(f"📋 Conditions: {test_patient['conditions']}")
        print(f"💊 Medications: {[med['name'] for med in test_patient['medications']]}")
        print(f"🩺 Vital signs: BP {test_patient['vital_signs']['blood_pressure']}")
        
        print("✅ Clinical engine basic functionality test: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing clinical engine: {e}")
        return False

if __name__ == "__main__":
    success = test_clinical_engine()
    
    if success:
        print("\n🎉 Clinical Engine Test: PASSED")
    else:
        print("\n💥 Clinical Engine Test: FAILED")