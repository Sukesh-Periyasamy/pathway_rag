# pathway_pubmed_patient_rag.py
import os
import time
import json
import math
import requests
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any

import pathway as pw

# LLM and embedding imports
from pathway.xpacks.llm.embedders import SentenceTransformerEmbedder
from pathway.xpacks.llm import llms

# load env
load_dotenv()

PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "e7f4fd12cf3590ecc551d2341a5af93b2508")  # your provided key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LOCAL_EMBEDDER_MODEL = os.getenv("LOCAL_EMBEDDER_MODEL", "all-mpnet-base-v2")

# PubMed base URLs
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ESEARCH_URL = f"{EUTILS_BASE}/esearch.fcgi"
ESUMMARY_URL = f"{EUTILS_BASE}/esummary.fcgi"
EFETCH_URL = f"{EUTILS_BASE}/efetch.fcgi"

# Rate-limiting: we must be <= 10 req/sec -> sleep 0.12 sec between PubMed requests to be safe.
PUBMED_MIN_DELAY = 0.12

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pathway_pubmed_rag")

# --------------- PUBMED helpers -----------------
def esearch(query: str, retmax: int = 50) -> List[str]:
    """
    Use ESearch to get PMIDs matching the query. Returns list of pmids.
    """
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY

    r = requests.get(ESEARCH_URL, params=params, timeout=15)
    time.sleep(PUBMED_MIN_DELAY)
    r.raise_for_status()
    j = r.json()
    pmids = j.get("esearchresult", {}).get("idlist", [])
    return pmids

def esummary(pmids: List[str]) -> List[Dict[str, Any]]:
    """
    Use ESummary to obtain metadata for PMIDs. Returns list of metadata dicts.
    """
    if not pmids:
        return []
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY
    r = requests.get(ESUMMARY_URL, params=params, timeout=20)
    time.sleep(PUBMED_MIN_DELAY)
    r.raise_for_status()
    j = r.json()
    result = []
    summaries = j.get("result", {})
    for pmid in pmids:
        item = summaries.get(pmid)
        if item:
            # extract DOI from articleids if present
            doi = None
            a_ids = item.get("articleids", [])
            for aid in a_ids:
                if aid.get("IdType") == "doi":
                    doi = aid.get("value")
                    break
            result.append(
                {
                    "pmid": pmid,
                    "title": item.get("title"),
                    "pubdate": item.get("pubdate"),
                    "source": item.get("source"),
                    "doi": doi,
                    "authors": item.get("authors"),
                    "sortdate": item.get("sortdate"),
                    "uid": item.get("uid"),
                }
            )
    return result

def efetch_abstracts(pmids: List[str]) -> Dict[str, str]:
    """
    efetch with rettype=abstract or retmode=xml: try to get abstract text for each pmid.
    We'll parse simple XML pieces — keep it pragmatic.
    Returns mapping pmid -> abstract text (empty if not available).
    """
    if not pmids:
        return {}
    params = {"db": "pubmed", "id": ",".join(pmids), "rettype": "abstract", "retmode": "text"}
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY
    r = requests.get(EFETCH_URL, params=params, timeout=30)
    time.sleep(PUBMED_MIN_DELAY)
    r.raise_for_status()
    txt = r.text
    # The plaintext efetch output can contain multiple abstracts; we'll attempt to split by newline 'PMID: '
    # This is not perfectly robust (real XML parsing is better), but is pragmatic for many cases.
    abstracts = {}
    # A safer approach is to call efetch with retmode=xml and parse; attempt that:
    params_xml = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
    if PUBMED_API_KEY:
        params_xml["api_key"] = PUBMED_API_KEY
    r2 = requests.get(EFETCH_URL, params=params_xml, timeout=30)
    time.sleep(PUBMED_MIN_DELAY)
    r2.raise_for_status()
    xml_text = r2.text
    # Simple XML parsing: extract <PubmedArticle> blocks and capture <PMID> and <AbstractText>
    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring("<root>" + xml_text + "</root>")
        for article in root.findall(".//PubmedArticle"):
            pmid_node = article.find(".//PMID")
            pmid = pmid_node.text if pmid_node is not None else None
            # join all AbstractText nodes
            abstract_texts = [ab.text or "" for ab in article.findall(".//AbstractText")]
            abstract = "\n".join(abstract_texts).strip()
            if pmid:
                abstracts[pmid] = abstract
    except Exception as e:
        logger.warning("XML parsing efetch failed: %s — falling back to plain text parsing", e)
        # fallback: try very naive split
        pieces = txt.split("\n\n")
        for piece in pieces:
            if piece.strip().startswith("PMID:"):
                lines = piece.strip().splitlines()
                first = lines[0]
                pmid = first.split("PMID:")[-1].strip()
                abstract = "\n".join(lines[1:]).strip()
                abstracts[pmid] = abstract
    return abstracts

# --------------- Text chunking (simple) -----------------
def chunk_text(text: str, max_chars: int = 800) -> List[str]:
    """
    Simple paragraph/sentence chunker — split by paragraphs and then by approximate size.
    For more precise token-based chunking use TokenCountSplitter from Pathway.xpacks.llm.splitters.
    """
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    cur = ""
    for p in paragraphs:
        if len(cur) + len(p) + 1 <= max_chars:
            cur = (cur + " " + p).strip()
        else:
            if cur:
                chunks.append(cur)
            if len(p) <= max_chars:
                cur = p
            else:
                # break long paragraph into slices
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i : i + max_chars])
                cur = ""
    if cur:
        chunks.append(cur)
    return chunks

# --------------- Embedding & ranking -----------------
# We'll use the SentenceTransformerEmbedder from Pathway xpack which wraps sentence-transformers.
# We will compute patient embedding and chunk embeddings, then cosine similarity.

def cosine_similarity_vecs(a, b):
    import numpy as np

    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    return float(np.dot(a, b) / denom)

# Initialize a local embedder (Pathway wrapper exposes a callable; for ease we will use the underlying model directly)
# But for simplicity outside a Pathway expression we can use sentence_transformers library directly:
from sentence_transformers import SentenceTransformer

# We will create a model instance once and reuse it
EMBED_MODEL = None


def get_embedding_model():
    global EMBED_MODEL
    if EMBED_MODEL is None:
        logger.info("Loading embedding model: %s", LOCAL_EMBEDDER_MODEL)
        EMBED_MODEL = SentenceTransformer(LOCAL_EMBEDDER_MODEL)
    return EMBED_MODEL


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_embedding_model()
    embs = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embs.tolist()

# --------------- Summarization via OpenAI (optional) -----------------
def openai_summarize(prompt_text: str) -> str:
    if not OPENAI_API_KEY:
        return None
    # Use the Pathway llms.OpenAIChat wrapper or direct openai package.
    # We'll use direct requests to OpenAI to keep dependency light:
    try:
        import openai

        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=512,
            temperature=0.0,
        )
        # extract text
        choices = response.get("choices", [])
        if choices:
            return choices[0]["message"]["content"].strip()
    except Exception as e:
        logger.exception("OpenAI call failed: %s", e)
    return None

# --------------- Query builder for PubMed -----------------
def build_pubmed_queries_from_patient(patient: Dict[str, Any]) -> List[str]:
    """
    Build multiple PubMed queries: diagnoses combined, medications interactions, and generic guideline queries.
    Returns list of queries (strings).
    """
    queries = []
    diagnoses = patient.get("diagnoses") or []
    meds = patient.get("medications") or []
    labs = patient.get("lab_results") or {}

    # primary combined query: diagnoses AND medications (if exist)
    if diagnoses:
        diag_q = " AND ".join([f'("{d}")' for d in diagnoses])
        queries.append(f"({diag_q})")
        # diagnosis + medication
        for m in meds:
            if isinstance(m, dict):
                med_name = m.get('name', '')
            else:
                med_name = str(m)
            if med_name:
                queries.append(f'({diag_q}) AND ("{med_name}")')

    # medication interactions and adverse events
    for m in meds:
        if isinstance(m, dict):
            med_name = m.get('name', '')
        else:
            med_name = str(m)
        if med_name:
            queries.append(f'("{med_name}" AND ("drug interaction" OR "adverse effect" OR "contraindication" OR "adverse events"))')

    # labs: e.g., "A1C" high/low (just include name)
    for lab_name, lab_value in labs.items():
        queries.append(f'("{lab_name}" AND ("{lab_value}" OR abnormal OR elevated OR decreased))')

    # guidelines search (diagnosis + guideline/consensus)
    for d in diagnoses:
        queries.append(f'("{d}" AND (guideline OR consensus OR "practice guideline"))')

    # deduplicate and return
    uniq = []
    for q in queries:
        if q not in uniq:
            uniq.append(q)
    return uniq

# --------------- Standalone function for integration -----------------
def query_pubmed_for_patient(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standalone function to query PubMed for a patient and return results.
    This can be called directly from the clinical engine.
    """
    try:
        logger.info("Processing PubMed query for patient: %s", patient_data.get("patient_id", "unknown"))

        # Compose a patient text to embed (name, diagnoses, meds, labs)
        text_parts = []
        diagnoses = patient_data.get("diagnoses", [])
        medications = patient_data.get("medications", patient_data.get("current_medications", []))
        lab_results = patient_data.get("lab_results", {})
        
        if diagnoses:
            text_parts.append("Diagnoses: " + ", ".join(diagnoses))
        if medications:
            med_names = []
            for med in medications:
                if isinstance(med, dict):
                    med_names.append(med.get('name', ''))
                else:
                    med_names.append(str(med))
            text_parts.append("Medications: " + ", ".join(med_names))
        if lab_results:
            text_parts.append("Labs: " + json.dumps(lab_results))
        
        patient_text = "\n".join(text_parts)

        # Build PubMed queries
        queries_built = build_pubmed_queries_from_patient(patient_data)
        logger.info("Built %d PubMed queries", len(queries_built))

        # We'll collect candidate PMIDs from all queries (de-duplicated)
        candidate_pmids = []
        MAX_PER_QUERY = 20  # keep moderate for faster response
        for q in queries_built[:5]:  # limit to first 5 queries to avoid too many API calls
            try:
                pmids = esearch(q, retmax=MAX_PER_QUERY)
                for pmid in pmids:
                    if pmid not in candidate_pmids:
                        candidate_pmids.append(pmid)
            except Exception as e:
                logger.warning("esearch failed for query %s: %s", q, e)
        
        logger.info("Found %d candidate PMIDs", len(candidate_pmids))

        # Get metadata and abstracts for these PMIDs
        metadata_list = esummary(candidate_pmids) if candidate_pmids else []
        abstracts_map = efetch_abstracts(candidate_pmids) if candidate_pmids else {}

        # Build list of chunks (each chunk: pmid, doi, pubdate, title, chunk_text)
        all_chunks = []
        for md in metadata_list:
            pmid = md.get("pmid") or md.get("uid")
            title = md.get("title")
            pubdate = md.get("pubdate")
            doi = md.get("doi")
            abstract = abstracts_map.get(pmid, "") or ""
            if not abstract:
                # skip items without abstract to avoid empty chunks
                continue
            chunks = chunk_text(abstract, max_chars=600)  # smaller chunks for better matching
            for idx, ch in enumerate(chunks):
                all_chunks.append(
                    {
                        "pmid": pmid,
                        "title": title,
                        "doi": doi,
                        "pubdate": pubdate,
                        "chunk_index": idx,
                        "text": ch,
                    }
                )

        logger.info("Total chunks extracted: %d", len(all_chunks))
        
        if not all_chunks:
            return {
                "patient_id": patient_data.get("patient_id"),
                "summary": "No relevant PubMed articles found for this patient's conditions and medications.",
                "top_chunks": [],
                "queries_used": queries_built,
                "note": "No abstracts found for patient queries on PubMed.",
            }

        # Build embeddings for patient text and chunk texts
        texts = [c["text"] for c in all_chunks]
        # embed texts and patient
        embed_model = get_embedding_model()
        chunk_embs = embed_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        patient_emb = embed_model.encode([patient_text], convert_to_numpy=True, show_progress_bar=False)[0]

        # Score chunks by cosine similarity
        import numpy as np

        scores = []
        for i, emb in enumerate(chunk_embs):
            sim = float(np.dot(emb, patient_emb) / ((np.linalg.norm(emb) * np.linalg.norm(patient_emb)) + 1e-12))
            scores.append(sim)

        # Attach scores and pick top_k
        for i, s in enumerate(scores):
            all_chunks[i]["score"] = s

        TOP_K = 8
        top_chunks = sorted(all_chunks, key=lambda x: x["score"], reverse=True)[:TOP_K]

        # Build a context string from top_chunks
        context_pieces = []
        for i, c in enumerate(top_chunks):
            snippet = c["text"][:800].replace("\n", " ")
            context_pieces.append(f"### Evidence {i+1}\nPMID: {c.get('pmid')}\nDOI: {c.get('doi')}\nDate: {c.get('pubdate')}\nTitle: {c.get('title')}\nSnippet: {snippet}\nRelevance Score: {c.get('score'):.4f}\n")
        context_text = "\n\n".join(context_pieces)

        # Build prompt for LLM summarization
        prompt = (
            "You are a clinical research assistant. Based on the patient's conditions and medications, "
            "and the following PubMed evidence, provide:\n\n"
            "1) A concise clinical summary of relevant evidence\n"
            "2) Any drug interactions or contraindications found\n"
            "3) Clinical recommendations based on current literature\n"
            "4) Key references (PMID/DOI) supporting the recommendations\n\n"
            f"Patient profile: {patient_text}\n\nEvidence from PubMed:\n{context_text}\n\n"
            "Clinical Assessment:"
        )

        summary_text = None
        if OPENAI_API_KEY:
            logger.info("Calling OpenAI for clinical literature summary")
            try:
                summary_text = openai_summarize(prompt)
            except Exception as e:
                logger.exception("OpenAI summarization failed: %s", e)
                summary_text = f"Unable to generate AI summary. Found {len(top_chunks)} relevant PubMed articles for review."

        # Build response payload
        result = {
            "patient_id": patient_data.get("patient_id"),
            "summary": summary_text or f"Found {len(top_chunks)} relevant research articles. Manual review recommended.",
            "top_chunks": [
                {
                    "pmid": c["pmid"],
                    "doi": c.get("doi"),
                    "pubdate": c.get("pubdate"),
                    "title": c.get("title"),
                    "snippet": c.get("text")[:600],
                    "score": c.get("score"),
                    "relevance": "High" if c.get("score", 0) > 0.7 else "Medium" if c.get("score", 0) > 0.5 else "Low"
                }
                for c in top_chunks
            ],
            "queries_used": queries_built,
            "total_articles_found": len(candidate_pmids),
            "success": True
        }

        logger.info("PubMed research completed for patient %s", patient_data.get("patient_id"))
        return result

    except Exception as e:
        logger.exception("Failed to process PubMed query for patient: %s", e)
        return {
            "patient_id": patient_data.get("patient_id"),
            "summary": f"Error retrieving PubMed research: {str(e)}",
            "top_chunks": [],
            "queries_used": [],
            "success": False,
            "error": str(e)
        }

# --------------- Main Pathway pipeline (optional - for standalone service) -----------------
def main():
    # Create REST connector to receive patient JSON
    class PatientSchema(pw.Schema):
        patient_id: str
        age: int = None
        gender: str = None
        diagnoses: list = None
        medications: list = None
        lab_results: dict = None

    webserver = pw.io.http.PathwayWebserver(host="0.0.0.0", port=8012)

    # queries table and writer
    queries, response_writer = pw.io.http.rest_connector(
        webserver=webserver,
        schema=PatientSchema,
        autocommit_duration_ms=50,
        delete_completed_queries=False,
    )

    # We will subscribe to queries and process the fetch + retrieval in the callback.
    def process_patient_row(key, row, time_, is_addition):
        """
        Called when new patient query arrives.
        """
        if not is_addition:
            return  # only handle additions

        try:
            patient = dict(row)
            result = query_pubmed_for_patient(patient)
            
            # send via response_writer: wrap into dataframe -> Pathway table
            import pandas as pd
            df = pd.DataFrame([result])
            tbl = pw.debug.table_from_pandas(df)
            response_writer(tbl)
            
        except Exception as e:
            logger.exception("Failed to process patient: %s", e)
            # return an error payload
            import pandas as pd
            df = pd.DataFrame([{"patient_id": row.get("patient_id"), "error": str(e)}])
            response_writer(pw.debug.table_from_pandas(df))

    # Subscribe to queries
    pw.io.subscribe(queries, lambda *args, **kwargs: process_patient_row(*args, **kwargs))

    # Run Pathway — this will start the HTTP server and wait for requests
    logger.info("Pathway PubMed RAG service starting on port 8012 ...")
    pw.run()


if __name__ == "__main__":
    main()