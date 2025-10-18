# test_pubmed_standalone.py - Standalone PubMed testing without Pathway dependencies
import os
import time
import requests
import json
from typing import List, Dict, Any

# PubMed E-Utilities configuration
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ESEARCH_URL = f"{EUTILS_BASE}/esearch.fcgi"
ESUMMARY_URL = f"{EUTILS_BASE}/esummary.fcgi"
EFETCH_URL = f"{EUTILS_BASE}/efetch.fcgi"

# Rate limiting - NCBI requires ≤10 req/sec
PUBMED_MIN_DELAY = 0.12

def esearch(query: str, retmax: int = 10) -> List[str]:
    """Search PubMed and return PMIDs matching the query."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
    }
    
    try:
        response = requests.get(ESEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        pmids = data.get("esearchresult", {}).get("idlist", [])
        print(f"🔍 Found {len(pmids)} articles for query: '{query}'")
        
        # Rate limiting
        time.sleep(PUBMED_MIN_DELAY)
        return pmids
        
    except Exception as e:
        print(f"❌ Error in esearch: {e}")
        return []

def esummary(pmids: List[str]) -> Dict[str, Any]:
    """Get summaries for a list of PMIDs."""
    if not pmids:
        return {}
    
    params = {
        "db": "pubmed", 
        "id": ",".join(pmids),
        "retmode": "json"
    }
    
    try:
        response = requests.get(ESUMMARY_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        summaries = {}
        result = data.get("result", {})
        
        for pmid in pmids:
            if pmid in result:
                article = result[pmid]
                summaries[pmid] = {
                    "title": article.get("title", ""),
                    "authors": [author.get("name", "") for author in article.get("authors", [])],
                    "pubdate": article.get("pubdate", ""),
                    "journal": article.get("source", ""),
                    "doi": article.get("doi", "")
                }
        
        print(f"📚 Retrieved {len(summaries)} article summaries")
        
        # Rate limiting
        time.sleep(PUBMED_MIN_DELAY)
        return summaries
        
    except Exception as e:
        print(f"❌ Error in esummary: {e}")
        return {}

def test_pubmed_integration():
    """Test the PubMed E-Utilities integration."""
    print("🧪 Testing PubMed E-Utilities Integration")
    print("=" * 50)
    
    # Test conditions
    test_conditions = ["diabetes", "hypertension"]
    query = " AND ".join(test_conditions) + " AND treatment"
    
    print(f"📋 Test query: '{query}'")
    print()
    
    # Step 1: Search for articles
    pmids = esearch(query, retmax=5)
    
    if not pmids:
        print("❌ No articles found - check your internet connection or PubMed API status")
        return False
    
    print(f"✅ Found {len(pmids)} PMIDs: {pmids[:3]}...")
    print()
    
    # Step 2: Get article summaries
    summaries = esummary(pmids)
    
    if not summaries:
        print("❌ Could not retrieve article summaries")
        return False
    
    print("✅ Successfully retrieved article summaries")
    print()
    
    # Step 3: Display sample results
    print("📄 Sample Article Results:")
    print("-" * 30)
    
    for i, (pmid, article) in enumerate(summaries.items()):
        if i >= 2:  # Show only first 2 articles
            break
            
        print(f"🔗 PMID: {pmid}")
        print(f"📖 Title: {article['title'][:100]}...")
        print(f"📅 Date: {article['pubdate']}")
        print(f"📰 Journal: {article['journal']}")
        if article['doi']:
            print(f"🔗 DOI: {article['doi']}")
        print()
    
    return True

if __name__ == "__main__":
    success = test_pubmed_integration()
    
    if success:
        print("🎉 PubMed Integration Test: PASSED")
    else:
        print("💥 PubMed Integration Test: FAILED")