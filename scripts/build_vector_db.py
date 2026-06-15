import os
import sys
import pandas as pd

# Allow relative project importing inside scripts directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import RAW_DATA_PATH
from src.ml.retriever import LegalRetriever

def main():
    if not os.path.exists(RAW_DATA_PATH):
        print(f"Error: Could not locate your dataset CSV at '{RAW_DATA_PATH}'")
        return

    print("Loading data...")
    df = pd.read_csv(RAW_DATA_PATH)
    
    # Standardize columns
    # We assume your CSV contains 'case_facts' (or similar text column), 'citation', and 'applicable_sections'
    text_col = "case_facts" if "case_facts" in df.columns else df.columns[1]
    citation_col = "citation" if "citation" in df.columns else df.columns[0]
    sections_col = "applicable_sections" if "applicable_sections" in df.columns else None
    
    documents = []
    for idx, row in df.iterrows():
        doc = {
            "id": idx,
            "text": str(row[text_col]),
            "citation": str(row[citation_col])
        }
        # Add sections if available
        if sections_col:
            doc["sections"] = str(row[sections_col])
        documents.append(doc)
        
    retriever = LegalRetriever()
    retriever.build_and_save_index(documents)
    
    # Test execution verification
    print("\nRunning quick test index query...")
    test_search = retriever.search("harassment for dowry and suspicious death", top_k=1)
    print(f"Retrieved Result: {test_search}")

if __name__ == "__main__":
    main()