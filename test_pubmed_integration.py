#!/usr/bin/env python3
"""
Test script to verify PubMed integration functionality
Tests the complete PubMed RAG pipeline integration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.pathway_pubmed_patient_rag import query_pubmed_for_patient
from src.core.clinical_engine import ClinicalDecisionEngine

def test_pubmed_standalone():
    """Test the standalone PubMed query function"""
    print("🧪 Testing Standalone PubMed Query Function...")
    
    # Test patient data
    test_patient = {
        "name": "Test Patient",
        "age": 45,
        "medical_conditions": ["hypertension", "diabetes type 2"],
        "current_medications": ["metformin", "lisinopril"],
        "symptoms": ["fatigue", "blurred vision"],
        "vital_signs": {
            "blood_pressure": "150/95",
            "blood_sugar": "180 mg/dL"
        }
    }
    
    try:
        result = query_pubmed_for_patient(test_patient, max_results=3)
        
        if result and 'recent_studies' in result:
            print(f"✅ Found {len(result['recent_studies'])} studies")
            
            for i, study in enumerate(result['recent_studies'][:2]):  # Show first 2
                print(f"\n📄 Study {i+1}:")
                print(f"   PMID: {study.get('pmid', 'Unknown')}")
                print(f"   Title: {study.get('title', 'No title')[:100]}...")
                print(f"   Relevance: {study.get('clinical_relevance', 'Unknown')}")
                print(f"   Score: {study.get('relevance_score', 0):.3f}")
            
            print(f"\n🔬 Clinical Summary: {result.get('clinical_summary', 'No summary')[:200]}...")
            return True
        else:
            print("❌ No studies found or invalid result structure")
            return False
            
    except Exception as e:
        print(f"❌ Error in standalone test: {str(e)}")
        return False

def test_clinical_engine_integration():
    """Test PubMed integration through the clinical engine"""
    print("\n🏥 Testing Clinical Engine PubMed Integration...")
    
    try:
        # Initialize clinical engine
        engine = ClinicalDecisionEngine()
        
        # Test patient data
        patient_data = {
            "patient_info": {
                "name": "Integration Test Patient",
                "age": 55,
                "gender": "Female"
            },
            "medical_history": {
                "conditions": ["atrial fibrillation", "chronic kidney disease"],
                "medications": ["warfarin", "metoprolol"],
                "allergies": []
            },
            "current_symptoms": ["palpitations", "shortness of breath"],
            "vital_signs": {
                "heart_rate": "irregular, 95 bpm",
                "blood_pressure": "140/85"
            },
            "lab_results": {
                "creatinine": "1.8 mg/dL",
                "eGFR": "35 mL/min"
            }
        }
        
        # Analyze patient (this should trigger PubMed integration)
        result = engine.analyze_patient(patient_data)
        
        # Check if research recommendations include PubMed results
        research_recs = result.get('recommendations', {}).get('research_based', [])
        
        pubmed_found = False
        for rec in research_recs:
            if rec.get('evidence_source') == 'pubmed_literature':
                pubmed_found = True
                print("✅ Found PubMed research recommendation!")
                print(f"   Title: {rec.get('title', 'Unknown')}")
                print(f"   Priority: {rec.get('priority', 'Unknown')}")
                print(f"   Relevance: {rec.get('relevance_score', 0):.1%}")
                
                supporting_studies = rec.get('supporting_studies', [])
                print(f"   Supporting Studies: {len(supporting_studies)}")
                
                if supporting_studies:
                    first_study = supporting_studies[0]
                    print(f"   First Study PMID: {first_study.get('pmid', 'Unknown')}")
                break
        
        if not pubmed_found:
            print("❌ No PubMed research recommendations found in clinical engine result")
            print("Available recommendations:")
            for rec in research_recs:
                print(f"   - {rec.get('title', 'Unknown')} (source: {rec.get('evidence_source', 'Unknown')})")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error in clinical engine test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all PubMed integration tests"""
    print("🔬 MedCare AI - PubMed Integration Test Suite")
    print("=" * 50)
    
    # Test 1: Standalone PubMed function
    test1_passed = test_pubmed_standalone()
    
    # Test 2: Clinical engine integration
    test2_passed = test_clinical_engine_integration()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Standalone PubMed Query: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   Clinical Engine Integration: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! PubMed integration is working correctly.")
        print("   You can now use the MedCare AI system with PubMed research evidence.")
    else:
        print("\n⚠️ Some tests failed. Please check the configuration and try again.")
    
    return test1_passed and test2_passed

if __name__ == "__main__":
    main()