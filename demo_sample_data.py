"""
MedCare AI CDSS - Quick Demo Script
===================================

This script demonstrates how to interact with the sample patient data
that has been loaded into the system.

Sample Patients Available:
1. Margaret Johnson (68F) - Diabetes, HTN, AFib - Complex drug interactions
2. Robert Chen (72M) - CAD, COPD - Respiratory + cardiac management
3. Sarah Williams (28F) - Anxiety, Hypothyroid - Young adult mental health
4. James Rodriguez (85M) - CHF, DM, CKD - Geriatric polypharmacy  
5. Emily Chen (45F) - Cancer survivor - Oncology follow-up care
6. David Rodriguez (19M) - T1DM, Depression - Pediatric transition care
7. Linda Thompson (62F) - COPD, Depression - Chronic disease management
8. Michael Kim (35M) - HTN, Obesity, Sleep Apnea - Cardiovascular risk

Demo Workflow:
=============

1. Access the application at: http://localhost:8505

2. Navigate to "Patient Records Management" 

3. You should see 8 pre-loaded patient records with the following information:
   - Patient demographics
   - Current diagnoses and medications  
   - Vital signs and lab results
   - Clinical notes and history

4. Select any patient and click "🔍 Analyze" to run the clinical decision support analysis

5. The system will analyze:
   - Drug interactions and safety alerts
   - Clinical guidelines compliance
   - Risk assessments and recommendations
   - Generate AI-powered summaries

6. Review the generated reports:
   - Clinical summary for healthcare providers
   - Patient education materials
   - Downloadable PDF reports

Recommended Demo Patients:
=========================

For Drug Interaction Demo:
- Margaret Johnson: Warfarin + multiple medications (bleeding risk)
- James Rodriguez: Complex polypharmacy in elderly patient

For Clinical Guidelines Demo:  
- Robert Chen: COPD + CAD management guidelines
- David Rodriguez: Diabetes management in young adults

For AI Summary Generation Demo:
- Emily Chen: Cancer survivorship care coordination  
- Linda Thompson: Complex chronic disease management

The system includes 17,430+ drug entries in the vector database for 
comprehensive drug interaction analysis and clinical decision support.
"""

print(__doc__)

# Sample API test for Pathway integration
import requests
import json

def test_pathway_connection():
    """Test the Pathway RAG backend connection"""
    try:
        response = requests.post(
            'http://localhost:8008/v1/pw_ai_answer',
            headers={'Content-Type': 'application/json'},
            json={'prompt': 'What are the drug interactions for warfarin?'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Pathway RAG Backend: CONNECTED")
            print(f"Response: {result.get('response', 'No response')}")
        else:
            print(f"⚠️ Pathway RAG Backend: HTTP {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Pathway RAG Backend: CONNECTION FAILED - {e}")

def test_medcare_frontend():
    """Test the MedCare AI frontend"""
    try:
        response = requests.get('http://localhost:8505', timeout=10)
        if response.status_code == 200:
            print(f"✅ MedCare AI Frontend: ACCESSIBLE")
        else:
            print(f"⚠️ MedCare AI Frontend: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ MedCare AI Frontend: CONNECTION FAILED - {e}")

if __name__ == "__main__":
    print("\n🏥 MedCare AI CDSS - System Status Check")
    print("=" * 50)
    
    test_pathway_connection()
    test_medcare_frontend() 
    
    print("\n📋 Demo Ready!")
    print("Navigate to http://localhost:8505 to begin the demonstration")