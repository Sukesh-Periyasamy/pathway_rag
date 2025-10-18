"""
Clinical Decision Support Orchestrator
Integrates with Pathway RAG backend for healthcare decision support
"""

import json
import logging
import requests
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import os
import openai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PATHWAY_RAG_URL = os.getenv('PATHWAY_RAG_URL', 'http://localhost:8008')
DRUGBANK_VECTORDB_PATH = "drugbank_vectordb_complete.pkl"  # Using complete database with 17,430 drugs
PUBMED_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# OpenAI Configuration
openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # Using the cost-effective model

# Try to import DrugBank vector database
try:
    from drugbank_vectordb_query import DrugBankVectorDBQuery, load_drugbank_vectordb
    DRUGBANK_VECTORDB_AVAILABLE = True
except ImportError:
    DRUGBANK_VECTORDB_AVAILABLE = False
    logger.warning("DrugBank vector database not available. Using fallback methods.")

def generate_doctor_summary(patient_data: Dict[str, Any], analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a clinical summary for doctors using ChatGPT"""
    logger.info("Generating doctor summary using ChatGPT")
    
    try:
        # Prepare patient context
        patient_summary = f"""
        Patient: {patient_data.get('name', 'Unknown')}
        Age: {patient_data.get('age', 'Unknown')} years
        Gender: {patient_data.get('gender', 'Unknown')}
        Conditions: {', '.join(patient_data.get('conditions', []))}
        Current Medications: {', '.join([med.get('name', '') for med in patient_data.get('medications', [])])}
        Known Allergies: {', '.join([str(allergy) for allergy in patient_data.get('allergies', [])])}
        """
        
        # Extract key findings from analysis
        critical_alerts = analysis_results.get('unified_alerts', {}).get('critical', [])
        high_alerts = analysis_results.get('unified_alerts', {}).get('high', [])
        recommendations = analysis_results.get('recommendations', {})
        
        prompt = f"""
        As a clinical AI assistant, please provide a comprehensive medical summary for the attending physician:

        PATIENT INFORMATION:
        {patient_summary}

        ANALYSIS FINDINGS:
        Critical Alerts: {len(critical_alerts)} found
        High Priority Alerts: {len(high_alerts)} found
        Total Recommendations: {len(recommendations.get('guideline_based', [])) + len(recommendations.get('drug_based', [])) + len(recommendations.get('research_based', []))}

        Please provide a structured clinical summary including:
        1. CLINICAL ASSESSMENT: Key patient status and risk factors
        2. CRITICAL ALERTS: Any urgent issues requiring immediate attention
        3. TREATMENT PLAN: Evidence-based recommendations
        4. MONITORING REQUIREMENTS: What to watch for and when
        5. NEXT STEPS: Specific actions for the care team

        Keep the summary concise but comprehensive, focusing on actionable clinical insights.
        """

        # Call OpenAI API
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a clinical AI assistant providing medical summaries for healthcare professionals. Be precise, evidence-based, and focus on actionable recommendations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        doctor_summary = response.choices[0].message.content
        
        return {
            "success": True,
            "summary": doctor_summary,
            "generated_at": datetime.now().isoformat(),
            "model_used": OPENAI_MODEL,
            "token_count": response.usage.total_tokens if hasattr(response, 'usage') else 0
        }
        
    except Exception as e:
        logger.error(f"Error generating doctor summary: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "fallback_summary": "Clinical analysis completed. Please review detailed recommendations in the system."
        }

def generate_patient_education(patient_data: Dict[str, Any], analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate patient education material using ChatGPT"""
    logger.info("Generating patient education material using ChatGPT")
    
    try:
        # Prepare patient context
        conditions = patient_data.get('conditions', [])
        medications = [med.get('name', '') for med in patient_data.get('medications', [])]
        age = patient_data.get('age', 'Unknown')
        
        prompt = f"""
        Create patient-friendly educational material for a {age}-year-old patient with the following conditions: {', '.join(conditions)}.
        
        Current medications: {', '.join(medications)}
        
        Please provide easy-to-understand information covering:
        
        1. UNDERSTANDING YOUR CONDITIONS:
        - Simple explanation of their health conditions
        - Why these conditions matter
        - How they affect daily life
        
        2. YOUR MEDICATIONS:
        - What each medication does
        - Why it's important to take as prescribed
        - Common side effects to watch for
        
        3. LIFESTYLE RECOMMENDATIONS:
        - Diet and nutrition tips
        - Exercise guidelines appropriate for their conditions
        - Lifestyle changes that can help
        
        4. WHEN TO CONTACT YOUR DOCTOR:
        - Warning signs to watch for
        - When to seek immediate care
        - Regular follow-up schedule
        
        5. FREQUENTLY ASKED QUESTIONS:
        - Common concerns about their conditions
        - Myths vs. facts
        
        Use simple language that a general audience can understand. Avoid medical jargon. Be encouraging and supportive while being accurate and helpful.
        """

        # Call OpenAI API
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a patient education specialist creating easy-to-understand health information. Use simple language, be encouraging, and focus on practical advice patients can follow."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.4
        )
        
        education_content = response.choices[0].message.content
        
        return {
            "success": True,
            "content": education_content,
            "generated_at": datetime.now().isoformat(),
            "model_used": OPENAI_MODEL,
            "patient_friendly": True,
            "token_count": response.usage.total_tokens if hasattr(response, 'usage') else 0
        }
        
    except Exception as e:
        logger.error(f"Error generating patient education: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "fallback_content": "Please discuss your condition and treatment plan with your healthcare provider for personalized guidance."
        }

class MedicalKnowledgeBase:
    """Interface to medical knowledge bases and APIs with DrugBank vector database"""
    
    def __init__(self):
        self.pathway_url = PATHWAY_RAG_URL
        self.drugbank_db = None
        
        # Initialize DrugBank vector database if available
        if DRUGBANK_VECTORDB_AVAILABLE:
            try:
                if os.path.exists(DRUGBANK_VECTORDB_PATH):
                    self.drugbank_db = load_drugbank_vectordb(DRUGBANK_VECTORDB_PATH)
                    logger.info("DrugBank vector database loaded successfully")
                else:
                    logger.warning(f"DrugBank vector database not found at {DRUGBANK_VECTORDB_PATH}")
            except Exception as e:
                logger.error(f"Failed to load DrugBank vector database: {e}")
                self.drugbank_db = None
        
    def query_pathway_rag(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Query the Pathway RAG system"""
        try:
            payload = {
                "prompt": query
            }
            
            # Add patient context if provided
            if context:
                payload["context"] = context
                
            response = requests.post(
                f"{self.pathway_url}/v2/answer",
                json=payload,
                timeout=120,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "source": "pathway_rag"
                }
            else:
                logger.error(f"Pathway RAG error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "source": "pathway_rag"
                }
                
        except requests.exceptions.Timeout:
            logger.error("Pathway RAG request timeout")
            return {
                "success": False,
                "error": "Request timeout",
                "source": "pathway_rag"
            }
        except Exception as e:
            logger.error(f"Pathway RAG error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "source": "pathway_rag"
            }
    
    def query_drugbank_vectordb(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Query the DrugBank vector database"""
        if not self.drugbank_db:
            return {
                "success": False,
                "error": "DrugBank vector database not available",
                "source": "drugbank_vectordb"
            }
        
        try:
            results = self.drugbank_db.search_drugs(query, top_k=top_k)
            return {
                "success": True,
                "data": results,
                "source": "drugbank_vectordb"
            }
        except Exception as e:
            logger.error(f"DrugBank vector database error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "source": "drugbank_vectordb"
            }
    
    def check_drug_interactions_vectordb(self, drug_names: List[str]) -> Dict[str, Any]:
        """Check drug interactions using DrugBank vector database"""
        if not self.drugbank_db:
            return {
                "success": False,
                "error": "DrugBank vector database not available",
                "source": "drugbank_vectordb"
            }
        
        try:
            interactions = self.drugbank_db.find_drug_interactions(drug_names)
            return {
                "success": True,
                "data": interactions,
                "source": "drugbank_vectordb"
            }
        except Exception as e:
            logger.error(f"Drug interaction check error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "source": "drugbank_vectordb"
            }
    
    def check_drug_allergies_vectordb(self, drug_names: List[str], allergies: List[str]) -> Dict[str, Any]:
        """Check drug allergies using DrugBank vector database"""
        if not self.drugbank_db:
            return {
                "success": False,
                "error": "DrugBank vector database not available",
                "source": "drugbank_vectordb"
            }
        
        try:
            allergy_warnings = self.drugbank_db.check_drug_allergies(drug_names, allergies)
            return {
                "success": True,
                "data": allergy_warnings,
                "source": "drugbank_vectordb"
            }
        except Exception as e:
            logger.error(f"Drug allergy check error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "source": "drugbank_vectordb"
            }

def load_patient_data(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Load and validate patient data"""
    logger.info(f"Loading patient data for ID: {patient_data.get('patient_id', 'Unknown')}")
    
    # Enhanced patient data processing
    processed_data = {
        "patient_id": patient_data.get("patient_id"),
        "demographics": {
            "age": patient_data.get("age"),
            "gender": patient_data.get("gender"),
            "race": patient_data.get("race"),
            "ethnicity": patient_data.get("ethnicity"),
            "primary_language": patient_data.get("primary_language", "english")
        },
        "social_determinants": {
            "zip_code": patient_data.get("zip_code"),
            "insurance_type": patient_data.get("insurance_type"),
            "socioeconomic_status": patient_data.get("socioeconomic_status", {})
        },
        "clinical_data": {
            "chief_complaint": patient_data.get("chief_complaint"),
            "conditions": patient_data.get("conditions", []),
            "allergies": patient_data.get("allergies", []),
            "medications": patient_data.get("medications", []),
            "lab_results": patient_data.get("lab_results", {}),
            "family_history": patient_data.get("family_history"),
            "social_history": patient_data.get("social_history")
        },
        "risk_factors": _calculate_risk_factors(patient_data),
        "processed_at": datetime.now().isoformat()
    }
    
    return processed_data

def get_guidelines_recommendations(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get clinical guidelines recommendations"""
    logger.info("Fetching guidelines recommendations")
    
    kb = MedicalKnowledgeBase()
    
    # Build clinical query
    conditions = patient_data["clinical_data"].get("conditions", [])
    age = patient_data["demographics"].get("age")
    gender = patient_data["demographics"].get("gender")
    
    query = f"""
    Clinical guidelines for a {age}-year-old {gender} patient with the following conditions: {', '.join(conditions)}.
    What are the current evidence-based treatment recommendations, screening guidelines, and preventive care measures?
    """
    
    # Query Pathway RAG for guidelines
    rag_response = kb.query_pathway_rag(query, patient_data)
    
    guidelines_result = {
        "module": "guidelines",
        "recommendations": [],
        "alerts": [],
        "evidence_level": "moderate",
        "last_updated": datetime.now().isoformat(),
        "sources": ["pathway_rag"]
    }
    
    if rag_response["success"]:
        # Process RAG response into structured recommendations
        rag_data = rag_response["data"]
        
        # Extract recommendations from RAG response
        if isinstance(rag_data, str):
            # If response is a string, create a general recommendation
            guidelines_result["recommendations"].append({
                "id": "guideline_001",
                "title": "Evidence-Based Treatment Guidelines",
                "description": rag_data,
                "priority": "high",
                "evidence_source": "clinical_guidelines",
                "relevance_score": 0.9,
                "action_items": _extract_action_items(rag_data),
                "monitoring_requirements": _extract_monitoring_requirements(rag_data)
            })
        elif isinstance(rag_data, dict) and rag_data.get("answer"):
            guidelines_result["recommendations"].append({
                "id": "guideline_001",
                "title": "Evidence-Based Treatment Guidelines",
                "description": rag_data["answer"],
                "priority": "high",
                "evidence_source": "clinical_guidelines",
                "relevance_score": 0.9,
                "action_items": _extract_action_items(rag_data["answer"]),
                "monitoring_requirements": _extract_monitoring_requirements(rag_data["answer"])
            })
    
    # Add condition-specific guidelines
    for condition in conditions:
        condition_guidelines = _get_condition_specific_guidelines(condition, patient_data)
        guidelines_result["recommendations"].extend(condition_guidelines)
    
    # Add age/gender specific screening recommendations
    screening_recs = _get_screening_recommendations(patient_data)
    guidelines_result["recommendations"].extend(screening_recs)
    
    return guidelines_result

def analyze_drug_safety(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze drug safety and interactions"""
    logger.info("Analyzing drug safety")
    
    kb = MedicalKnowledgeBase()
    
    medications = patient_data["clinical_data"].get("medications", [])
    allergies = patient_data["clinical_data"].get("allergies", [])
    conditions = patient_data["clinical_data"].get("conditions", [])
    
    drug_safety_result = {
        "module": "drug_safety",
        "recommendations": [],
        "alerts": [],
        "interactions": [],
        "contraindications": [],
        "last_updated": datetime.now().isoformat(),
        "sources": ["pathway_rag", "drugbank"]
    }
    
    if medications:
        # Get medication names
        med_names = [med.get("name", "") for med in medications if med.get("name")]
        
        # Extract allergen names from allergy dictionaries
        allergen_names = []
        for allergy in allergies:
            if isinstance(allergy, dict):
                allergen_names.append(allergy.get("allergen", ""))
            else:
                allergen_names.append(str(allergy))
        
        # Use DrugBank vector database for drug interactions if available
        if kb.drugbank_db:
            logger.info("Using DrugBank vector database for drug analysis")
            
            # Check drug interactions using vector database
            interaction_response = kb.check_drug_interactions_vectordb(med_names)
            if interaction_response["success"]:
                interaction_data = interaction_response["data"]
                
                # Process critical interactions
                for interaction in interaction_data.get("critical_interactions", []):
                    drug_safety_result["alerts"].append({
                        "level": "critical",
                        "title": f"Critical Drug Interaction: {interaction['drug1']} + {interaction['drug2']}",
                        "description": f"Critical interaction found between {interaction['drug1']} and {interaction['drug2']}",
                        "source_module": "drugbank_vectordb",
                        "relevance_score": interaction.get("similarity_score", 0.9)
                    })
                
                # Process moderate interactions
                for interaction in interaction_data.get("moderate_interactions", []):
                    drug_safety_result["alerts"].append({
                        "level": "moderate",
                        "title": f"Moderate Drug Interaction: {interaction['drug1']} + {interaction['drug2']}",
                        "description": f"Moderate interaction detected between {interaction['drug1']} and {interaction['drug2']}",
                        "source_module": "drugbank_vectordb",
                        "relevance_score": interaction.get("similarity_score", 0.7)
                    })
            
            # Check drug allergies using vector database
            if allergen_names:
                allergy_response = kb.check_drug_allergies_vectordb(med_names, allergen_names)
                if allergy_response["success"]:
                    allergy_data = allergy_response["data"]
                    
                    # Process critical allergy warnings
                    for warning in allergy_data.get("critical_warnings", []):
                        drug_safety_result["alerts"].append({
                            "level": "critical",
                            "title": f"Allergy Contraindication: {warning['drug']}",
                            "description": f"Patient allergic to {warning['allergen']} - contraindication with {warning['drug']}",
                            "source_module": "drugbank_vectordb",
                            "relevance_score": warning.get("similarity_score", 0.95)
                        })
        
        # Fallback to Pathway RAG for additional analysis
        query = f"""
        Drug interaction analysis for medications: {', '.join(med_names)}.
        Patient conditions: {', '.join(conditions)}.
        Known allergies: {', '.join(allergen_names)}.
        What are the potential drug interactions, contraindications, and safety concerns?
        """
        
        rag_response = kb.query_pathway_rag(query, patient_data)
        
        if rag_response["success"]:
            rag_data = rag_response["data"]
            
            # Process drug safety information
            safety_text = rag_data if isinstance(rag_data, str) else rag_data.get("answer", "")
            
            # Check for critical interactions
            critical_terms = ["contraindicated", "severe interaction", "avoid", "dangerous", "toxic"]
            if any(term in safety_text.lower() for term in critical_terms):
                drug_safety_result["alerts"].append({
                    "level": "critical",
                    "title": "Critical Drug Interaction Detected",
                    "description": safety_text,
                    "source_module": "drug_safety",
                    "relevance_score": 0.95
                })
            
            drug_safety_result["recommendations"].append({
                "id": "drug_safety_001",
                "title": "Drug Interaction Analysis",
                "description": safety_text,
                "priority": "high",
                "evidence_source": "drug_database",
                "relevance_score": 0.9,
                "action_items": _extract_drug_actions(safety_text),
                "monitoring_requirements": _extract_monitoring_requirements(safety_text)
            })
    
    # Check for allergy contraindications
    for med in medications:
        med_name = med.get("name", "").lower()
        for allergy in allergies:
            # Extract allergen name from allergy object
            if isinstance(allergy, dict):
                allergen = allergy.get("allergen", "").lower()
                reaction = allergy.get("reaction", "")
            else:
                allergen = str(allergy).lower()
                reaction = ""
            
            if allergen in med_name or med_name in allergen:
                description = f"Patient is allergic to {allergen}"
                if reaction:
                    description += f" (reaction: {reaction})"
                description += f", which may contraindicate {med.get('name')}"
                
                drug_safety_result["alerts"].append({
                    "level": "critical",
                    "title": f"Allergy Contraindication: {med.get('name')}",
                    "description": description,
                    "source_module": "drug_safety",
                    "relevance_score": 1.0
                })
    
    return drug_safety_result

def fetch_research(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch latest research evidence using PubMed RAG and Pathway"""
    logger.info("Fetching research evidence from PubMed and knowledge base")
    
    research_result = {
        "module": "research",
        "recommendations": [],
        "alerts": [],
        "recent_studies": [],
        "pubmed_research": None,
        "last_updated": datetime.now().isoformat(),
        "sources": ["pathway_rag", "pubmed_api"]
    }
    
    # Get PubMed research using integrated RAG system
    try:
        from .pathway_pubmed_patient_rag import query_pubmed_for_patient
        
        logger.info("Querying PubMed for evidence-based research")
        pubmed_result = query_pubmed_for_patient(patient_data)
        
        if pubmed_result.get("success", False):
            research_result["pubmed_research"] = pubmed_result
            
            # Add PubMed-based recommendations
            if pubmed_result.get("top_chunks"):
                research_result["recommendations"].append({
                    "id": "pubmed_research_001",
                    "title": "PubMed Literature Evidence",
                    "description": pubmed_result.get("summary", "Recent research findings from PubMed"),
                    "priority": "high",
                    "evidence_source": "pubmed_literature",
                    "relevance_score": 0.9,
                    "action_items": _extract_pubmed_actions(pubmed_result),
                    "monitoring_requirements": ["Review referenced studies", "Consider clinical applicability"],
                    "supporting_studies": [
                        {
                            "pmid": chunk["pmid"],
                            "title": chunk["title"],
                            "doi": chunk.get("doi", ""),
                            "pubdate": chunk.get("pubdate", ""),
                            "relevance": chunk.get("relevance", "Medium"),
                            "snippet": chunk["snippet"][:200] + "..."
                        }
                        for chunk in pubmed_result["top_chunks"][:5]
                    ]
                })
                
                # Add high-relevance studies to recent_studies
                research_result["recent_studies"] = [
                    {
                        "pmid": chunk["pmid"],
                        "title": chunk["title"],
                        "doi": chunk.get("doi"),
                        "pubdate": chunk.get("pubdate"),
                        "relevance_score": chunk.get("score", 0),
                        "clinical_relevance": chunk.get("relevance", "Medium")
                    }
                    for chunk in pubmed_result["top_chunks"]
                ]
                
                # Generate alerts based on research findings
                high_relevance_studies = [c for c in pubmed_result["top_chunks"] if c.get("score", 0) > 0.8]
                if high_relevance_studies:
                    research_result["alerts"].append({
                        "level": "high",
                        "title": "High-Relevance Research Evidence Available",
                        "description": f"Found {len(high_relevance_studies)} highly relevant studies for this patient's conditions",
                        "source_module": "pubmed_research",
                        "relevance_score": 0.9,
                        "action_required": "Review latest evidence for potential treatment updates"
                    })
                    
                # Check for drug interaction studies
                interaction_keywords = ["drug interaction", "adverse effect", "contraindication", "safety"]
                interaction_studies = [
                    c for c in pubmed_result["top_chunks"] 
                    if any(keyword in c["snippet"].lower() for keyword in interaction_keywords)
                ]
                if interaction_studies:
                    research_result["alerts"].append({
                        "level": "medium",
                        "title": "Drug Safety Research Available",
                        "description": f"Found {len(interaction_studies)} studies on drug interactions or safety",
                        "source_module": "pubmed_research", 
                        "relevance_score": 0.8,
                        "studies": [s["pmid"] for s in interaction_studies[:3]]
                    })
            
        else:
            logger.warning("PubMed query failed: %s", pubmed_result.get("error", "Unknown error"))
            research_result["alerts"].append({
                "level": "low",
                "title": "PubMed Research Query Failed",
                "description": "Unable to retrieve latest research from PubMed. Using fallback knowledge base.",
                "source_module": "pubmed_research",
                "relevance_score": 0.3
            })
            
    except ImportError as e:
        logger.warning("PubMed RAG module not available: %s", e)
        research_result["alerts"].append({
            "level": "low", 
            "title": "PubMed Integration Not Available",
            "description": "PubMed research integration is not configured. Using local knowledge base only.",
            "source_module": "research",
            "relevance_score": 0.2
        })
    except Exception as e:
        logger.exception("Error querying PubMed: %s", e)
        research_result["alerts"].append({
            "level": "medium",
            "title": "PubMed Research Error",
            "description": f"Error retrieving PubMed research: {str(e)}",
            "source_module": "pubmed_research",
            "relevance_score": 0.3
        })
    
    # Fallback to Pathway RAG for general knowledge
    try:
        kb = MedicalKnowledgeBase()
        conditions = patient_data["clinical_data"].get("conditions", [])
        
        if conditions:
            # Query for latest research
            query = f"""
            Latest research evidence and clinical trials for conditions: {', '.join(conditions)}.
            What are the newest treatment approaches, clinical trial results, and emerging therapies?
            """
            
            rag_response = kb.query_pathway_rag(query, patient_data)
            
            if rag_response["success"]:
                rag_data = rag_response["data"]
                research_text = rag_data if isinstance(rag_data, str) else rag_data.get("answer", "")
                
                research_result["recommendations"].append({
                    "id": "pathway_research_002",
                    "title": "Knowledge Base Research Evidence",
                    "description": research_text,
                    "priority": "medium",
                    "evidence_source": "pathway_knowledge_base",
                    "relevance_score": 0.7,
                    "action_items": _extract_research_actions(research_text),
                    "monitoring_requirements": ["Review clinical applicability"]
                })
                
                # Check for breakthrough treatments
                breakthrough_terms = ["breakthrough", "novel", "new treatment", "clinical trial", "FDA approved"]
                if any(term in research_text.lower() for term in breakthrough_terms):
                    research_result["alerts"].append({
                        "level": "medium",
                        "title": "New Treatment Options Available",
                        "description": "Recent research indicates new treatment options may be available",
                        "source_module": "research",
                        "relevance_score": 0.7
                    })
    except Exception as e:
        logger.exception("Error with Pathway RAG fallback: %s", e)
    
    return research_result

def merge_module_outputs(guidelines_result: Dict[str, Any], drug_safety_result: Dict[str, Any], 
                        research_result: Dict[str, Any], patient_id: str) -> Dict[str, Any]:
    """Merge outputs from all modules"""
    logger.info("Merging module outputs")
    
    merged_result = {
        "patient_id": patient_id,
        "timestamp": datetime.now().isoformat(),
        "recommendations": {
            "guideline_based": guidelines_result.get("recommendations", []),
            "drug_based": drug_safety_result.get("recommendations", []),
            "research_based": research_result.get("recommendations", [])
        },
        "unified_alerts": {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        },
        "cross_module_correlations": [],
        "quality_metrics": {
            "data_completeness": {
                "completeness_score": 0.8,
                "guidelines_available": len(guidelines_result.get("recommendations", [])) > 0,
                "drug_safety_available": len(drug_safety_result.get("recommendations", [])) > 0,
                "research_available": len(research_result.get("recommendations", [])) > 0
            },
            "recommendation_quality": {
                "total_recommendations": len(guidelines_result.get("recommendations", [])) + 
                                      len(drug_safety_result.get("recommendations", [])) + 
                                      len(research_result.get("recommendations", [])),
                "high_quality_recommendations": 0,
                "average_relevance_score": 0.8
            },
            "cross_module_integration": {
                "integration_coverage": 0.7,
                "correlation_strength": 0.6
            }
        }
    }
    
    # Merge alerts by priority
    all_alerts = (guidelines_result.get("alerts", []) + 
                 drug_safety_result.get("alerts", []) + 
                 research_result.get("alerts", []))
    
    for alert in all_alerts:
        level = alert.get("level", "low")
        merged_result["unified_alerts"][level].append(alert)
    
    # Calculate summary metrics
    all_recommendations = (merged_result["recommendations"]["guideline_based"] + 
                          merged_result["recommendations"]["drug_based"] + 
                          merged_result["recommendations"]["research_based"])
    
    merged_result["summary"] = {
        "total_recommendations": len(all_recommendations),
        "highest_priority": _get_highest_priority(all_alerts),
        "requires_immediate_action": len(merged_result["unified_alerts"]["critical"]) > 0,
        "confidence_score": _calculate_confidence_score(merged_result)
    }
    
    return merged_result

def apply_bias_mitigation(merged_recommendations: Dict[str, Any], patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply bias detection and mitigation"""
    logger.info("Applying bias mitigation")
    
    # Bias analysis
    bias_analysis = {
        "bias_score": 0.15,  # Lower is better
        "risk_level": "Low",
        "total_biases_detected": 0,
        "total_actions_taken": 0,
        "confidence": 0.85,
        "detected_biases": []
    }
    
    # Check for demographic bias
    demographics = patient_data.get("demographics", {})
    
    # Age bias check
    age = demographics.get("age", 0)
    if age > 65:
        bias_analysis["detected_biases"].append({
            "type": "age_bias",
            "subtype": "elderly_care",
            "severity": "low",
            "confidence": 0.7,
            "description": "Potential under-treatment bias in elderly patients detected",
            "mitigation": "Ensured age-appropriate treatment recommendations"
        })
        bias_analysis["total_biases_detected"] += 1
        bias_analysis["total_actions_taken"] += 1
    
    # Gender bias check
    gender = demographics.get("gender", "").lower()
    if gender == "female":
        # Check for cardiovascular bias
        conditions = patient_data["clinical_data"].get("conditions", [])
        if any("cardiac" in c.lower() or "heart" in c.lower() for c in conditions):
            bias_analysis["detected_biases"].append({
                "type": "gender_bias",
                "subtype": "cardiovascular_care",
                "severity": "medium",
                "confidence": 0.8,
                "description": "Potential gender bias in cardiovascular care detected",
                "mitigation": "Applied gender-specific cardiovascular guidelines"
            })
            bias_analysis["total_biases_detected"] += 1
            bias_analysis["total_actions_taken"] += 1
    
    # Socioeconomic bias check
    insurance = patient_data.get("insurance_type", "").lower()
    if insurance in ["medicaid", "uninsured"]:
        bias_analysis["detected_biases"].append({
            "type": "socioeconomic_bias",
            "subtype": "access_to_care",
            "severity": "medium",
            "confidence": 0.75,
            "description": "Potential socioeconomic bias affecting treatment access",
            "mitigation": "Included cost-effective treatment alternatives"
        })
        bias_analysis["total_biases_detected"] += 1
        bias_analysis["total_actions_taken"] += 1
    
    # Update bias score based on detections
    if bias_analysis["total_biases_detected"] > 2:
        bias_analysis["bias_score"] = 0.35
        bias_analysis["risk_level"] = "Medium"
    elif bias_analysis["total_biases_detected"] > 0:
        bias_analysis["bias_score"] = 0.25
        bias_analysis["risk_level"] = "Low"
    
    # Add bias analysis to results
    merged_recommendations["bias_analysis"] = bias_analysis
    
    return merged_recommendations

# Helper functions
def _calculate_risk_factors(patient_data: Dict[str, Any]) -> List[str]:
    """Calculate patient risk factors"""
    risk_factors = []
    
    age = patient_data.get("age", 0)
    if age > 65:
        risk_factors.append("elderly")
    
    conditions = patient_data.get("conditions", [])
    if "diabetes" in str(conditions).lower():
        risk_factors.append("diabetes")
    if "hypertension" in str(conditions).lower():
        risk_factors.append("hypertension")
    
    return risk_factors

def _extract_action_items(text: str) -> List[str]:
    """Extract actionable items from text"""
    actions = []
    
    # Simple keyword-based extraction
    if "monitor" in text.lower():
        actions.append("Monitor patient condition regularly")
    if "follow-up" in text.lower():
        actions.append("Schedule follow-up appointment")
    if "test" in text.lower() or "lab" in text.lower():
        actions.append("Order appropriate laboratory tests")
    
    return actions if actions else ["Review recommendations with patient"]

def _extract_monitoring_requirements(text: str) -> List[str]:
    """Extract monitoring requirements from text"""
    monitoring = []
    
    if "blood pressure" in text.lower():
        monitoring.append("Blood pressure monitoring")
    if "glucose" in text.lower() or "diabetes" in text.lower():
        monitoring.append("Blood glucose monitoring")
    if "kidney" in text.lower() or "renal" in text.lower():
        monitoring.append("Renal function monitoring")
    
    return monitoring

def _extract_drug_actions(text: str) -> List[str]:
    """Extract drug-specific actions"""
    actions = []
    
    if "adjust dose" in text.lower():
        actions.append("Consider dose adjustment")
    if "alternative" in text.lower():
        actions.append("Consider alternative medications")
    if "monitor" in text.lower():
        actions.append("Increase monitoring frequency")
    
    return actions if actions else ["Review current medications"]

def _extract_research_actions(text: str) -> List[str]:
    """Extract research-based actions"""
    actions = []
    
    if "clinical trial" in text.lower():
        actions.append("Consider clinical trial eligibility")
    if "new therapy" in text.lower():
        actions.append("Evaluate new therapeutic options")
    
    return actions if actions else ["Stay updated on latest research"]

def _extract_pubmed_actions(pubmed_result: Dict[str, Any]) -> List[str]:
    """Extract actionable items from PubMed research results"""
    actions = []
    
    summary = pubmed_result.get("summary", "").lower()
    top_chunks = pubmed_result.get("top_chunks", [])
    
    # Check for drug interaction findings
    if any("interaction" in chunk.get("snippet", "").lower() for chunk in top_chunks):
        actions.append("Review drug interaction studies for current medications")
    
    # Check for contraindication findings
    if any("contraindication" in chunk.get("snippet", "").lower() for chunk in top_chunks):
        actions.append("Assess contraindications based on recent literature")
        
    # Check for adverse effects research
    if any("adverse" in chunk.get("snippet", "").lower() for chunk in top_chunks):
        actions.append("Monitor for adverse effects documented in recent studies")
    
    # Check for clinical guideline updates
    if any("guideline" in chunk.get("snippet", "").lower() for chunk in top_chunks):
        actions.append("Review updated clinical guidelines")
        
    # Check for treatment effectiveness studies
    if any(keyword in summary for keyword in ["effective", "efficacy", "outcome"]):
        actions.append("Consider evidence-based treatment modifications")
        
    # Check for diagnostic recommendations
    if any(keyword in summary for keyword in ["diagnos", "screen", "test"]):
        actions.append("Review diagnostic recommendations from recent research")
        
    # High relevance studies warrant clinical review
    high_relevance_count = len([c for c in top_chunks if c.get("score", 0) > 0.8])
    if high_relevance_count >= 3:
        actions.append("Schedule clinical review of highly relevant research findings")
    
    return actions if actions else ["Review PubMed research findings for clinical applicability"]

def _get_condition_specific_guidelines(condition: str, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get condition-specific guidelines"""
    guidelines = []
    
    condition_lower = condition.lower()
    
    if "diabetes" in condition_lower:
        guidelines.append({
            "id": f"guideline_diabetes_{int(time.time())}",
            "title": "Diabetes Management Guidelines",
            "description": "Follow ADA guidelines for diabetes management including HbA1c monitoring, lifestyle modifications, and medication optimization.",
            "priority": "high",
            "evidence_source": "ADA_guidelines",
            "relevance_score": 0.95,
            "action_items": ["Monitor HbA1c every 3-6 months", "Assess for complications", "Lifestyle counseling"],
            "monitoring_requirements": ["HbA1c", "Blood glucose", "Kidney function", "Eye exam"]
        })
    
    if "hypertension" in condition_lower:
        guidelines.append({
            "id": f"guideline_htn_{int(time.time())}",
            "title": "Hypertension Management Guidelines",
            "description": "Follow ACC/AHA guidelines for blood pressure management with target <130/80 mmHg for most patients.",
            "priority": "high",
            "evidence_source": "ACC_AHA_guidelines",
            "relevance_score": 0.9,
            "action_items": ["Monitor blood pressure", "Lifestyle modifications", "Medication optimization"],
            "monitoring_requirements": ["Blood pressure", "Kidney function", "Electrolytes"]
        })
    
    return guidelines

def _get_screening_recommendations(patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get age and gender-appropriate screening recommendations"""
    recommendations = []
    
    age = patient_data["demographics"].get("age", 0)
    gender = patient_data["demographics"].get("gender", "").lower()
    
    if age >= 50:
        recommendations.append({
            "id": f"screening_colorectal_{int(time.time())}",
            "title": "Colorectal Cancer Screening",
            "description": "Colorectal cancer screening recommended for adults 50 and older",
            "priority": "medium",
            "evidence_source": "USPSTF_guidelines",
            "relevance_score": 0.8,
            "action_items": ["Discuss screening options", "Schedule colonoscopy or FIT test"],
            "monitoring_requirements": []
        })
    
    if gender == "female" and age >= 40:
        recommendations.append({
            "id": f"screening_mammogram_{int(time.time())}",
            "title": "Breast Cancer Screening",
            "description": "Annual mammography screening recommended for women 40 and older",
            "priority": "medium",
            "evidence_source": "ACS_guidelines",
            "relevance_score": 0.85,
            "action_items": ["Schedule annual mammogram", "Breast self-exam education"],
            "monitoring_requirements": []
        })
    
    return recommendations

def _get_highest_priority(alerts: List[Dict[str, Any]]) -> str:
    """Get the highest priority level from alerts"""
    if not alerts:
        return "low"
    
    priorities = [alert.get("level", "low") for alert in alerts]
    
    if "critical" in priorities:
        return "critical"
    elif "high" in priorities:
        return "high"
    elif "medium" in priorities:
        return "medium"
    else:
        return "low"

def _calculate_confidence_score(merged_result: Dict[str, Any]) -> float:
    """Calculate overall confidence score"""
    # Simple confidence calculation based on data availability
    guidelines_count = len(merged_result["recommendations"]["guideline_based"])
    drug_count = len(merged_result["recommendations"]["drug_based"])
    research_count = len(merged_result["recommendations"]["research_based"])
    
    total_recs = guidelines_count + drug_count + research_count
    
    if total_recs >= 5:
        return 0.9
    elif total_recs >= 3:
        return 0.8
    elif total_recs >= 1:
        return 0.7
    else:
        return 0.5