#!/usr/bin/env python3
"""
Test script for ChatGPT integration in the Medical RAG system
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from clinical_decision_orchestrator import generate_doctor_summary, generate_patient_education

def test_gpt_integration():
    """Test the ChatGPT integration with sample data"""
    
    print("🧪 Testing ChatGPT Integration for Medical RAG System")
    print("=" * 60)
    
    # Sample patient data
    patient_data = {
        "name": "John Doe",
        "age": 65,
        "gender": "Male", 
        "conditions": ["Type 2 Diabetes", "Hypertension", "Hyperlipidemia"],
        "medications": [
            {"name": "Metformin", "dosage": "500mg", "frequency": "twice daily"},
            {"name": "Lisinopril", "dosage": "10mg", "frequency": "once daily"},
            {"name": "Simvastatin", "dosage": "20mg", "frequency": "once daily"}
        ],
        "allergies": [
            {"allergen": "Penicillin", "reaction": "Rash"}
        ]
    }
    
    # Sample analysis results
    analysis_results = {
        "unified_alerts": {
            "critical": [
                {
                    "title": "Drug Interaction Warning",
                    "description": "Potential interaction between Metformin and Lisinopril in elderly patients"
                }
            ],
            "high": [],
            "medium": []
        },
        "recommendations": {
            "guideline_based": [
                {
                    "title": "Diabetes Management",
                    "description": "Follow ADA guidelines for HbA1c monitoring"
                }
            ],
            "drug_based": [
                {
                    "title": "Medication Review", 
                    "description": "Regular monitoring of kidney function recommended"
                }
            ],
            "research_based": [
                {
                    "title": "Latest Treatment Options",
                    "description": "Recent studies show benefits of SGLT2 inhibitors"
                }
            ]
        }
    }
    
    # Test doctor summary generation
    print("\n📋 Testing Doctor Summary Generation...")
    doctor_summary = generate_doctor_summary(patient_data, analysis_results)
    
    if doctor_summary.get('success'):
        print("✅ Doctor summary generated successfully!")
        print(f"Summary length: {len(doctor_summary['summary'])} characters")
        print(f"Model used: {doctor_summary.get('model_used', 'Unknown')}")
        print(f"Token count: {doctor_summary.get('token_count', 'Unknown')}")
        print("\nSample output:")
        print("-" * 40)
        print(doctor_summary['summary'][:300] + "..." if len(doctor_summary['summary']) > 300 else doctor_summary['summary'])
        print("-" * 40)
    else:
        print(f"❌ Doctor summary generation failed: {doctor_summary.get('error', 'Unknown error')}")
    
    # Test patient education generation
    print("\n👤 Testing Patient Education Generation...")
    patient_education = generate_patient_education(patient_data, analysis_results)
    
    if patient_education.get('success'):
        print("✅ Patient education generated successfully!")
        print(f"Content length: {len(patient_education['content'])} characters")
        print(f"Model used: {patient_education.get('model_used', 'Unknown')}")
        print(f"Patient friendly: {patient_education.get('patient_friendly', 'Unknown')}")
        print(f"Token count: {patient_education.get('token_count', 'Unknown')}")
        print("\nSample output:")
        print("-" * 40)
        print(patient_education['content'][:300] + "..." if len(patient_education['content']) > 300 else patient_education['content'])
        print("-" * 40)
    else:
        print(f"❌ Patient education generation failed: {patient_education.get('error', 'Unknown error')}")
    
    # Check OpenAI API key
    print("\n🔑 Checking OpenAI Configuration...")
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"✅ OpenAI API key configured (ends with: ...{api_key[-8:]})")
    else:
        print("❌ OpenAI API key not found in environment variables")
        print("Please set OPENAI_API_KEY environment variable")
    
    print("\n🏁 Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_gpt_integration()