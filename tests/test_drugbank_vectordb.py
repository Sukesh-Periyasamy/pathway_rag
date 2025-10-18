#!/usr/bin/env python3
"""
Test DrugBank Vector Database
"""

from drugbank_vectordb_query import load_drugbank_vectordb

def test_drugbank_vectordb():
    """Test the DrugBank vector database functionality"""
    
    print("Loading DrugBank Vector Database...")
    db = load_drugbank_vectordb()
    print("✅ DrugBank Vector DB loaded successfully!")
    
    # Test search functionality
    print("\n" + "="*50)
    print("Testing Drug Search")
    print("="*50)
    
    search_queries = [
        "aspirin drug interaction",
        "warfarin bleeding risk",
        "diabetes medication metformin",
        "antibiotic penicillin allergy"
    ]
    
    for query in search_queries:
        print(f"\nSearching for: '{query}'")
        results = db.search_drugs(query, top_k=3)
        print(f"Found {len(results)} results:")
        
        for i, result in enumerate(results[:2], 1):
            print(f"  {i}. {result['name']} (score: {result['similarity_score']:.3f})")
            if result.get('indication'):
                print(f"     Indication: {result['indication'][:100]}...")
    
    # Test drug interaction checking
    print("\n" + "="*50)
    print("Testing Drug Interaction Checking")
    print("="*50)
    
    test_medications = ["aspirin", "warfarin"]
    print(f"Checking interactions for: {test_medications}")
    
    interactions = db.find_drug_interactions(test_medications)
    print(f"Critical interactions: {len(interactions['critical_interactions'])}")
    print(f"Moderate interactions: {len(interactions['moderate_interactions'])}")
    print(f"Mild interactions: {len(interactions['mild_interactions'])}")
    
    # Test allergy checking
    print("\n" + "="*50)
    print("Testing Allergy Checking")
    print("="*50)
    
    test_drugs = ["penicillin", "amoxicillin"]
    test_allergies = ["penicillin", "sulfa"]
    print(f"Checking allergies for drugs: {test_drugs}")
    print(f"Known allergies: {test_allergies}")
    
    allergy_warnings = db.check_drug_allergies(test_drugs, test_allergies)
    print(f"Critical warnings: {len(allergy_warnings['critical_warnings'])}")
    print(f"Moderate warnings: {len(allergy_warnings['moderate_warnings'])}")
    
    print("\n" + "="*50)
    print("DrugBank Vector Database Test Completed Successfully!")
    print("="*50)

if __name__ == "__main__":
    test_drugbank_vectordb()