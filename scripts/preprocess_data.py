import os
import sys
import pandas as pd
from sklearn.model_selection import train_test_split

# Set base import paths so python can find your src/ config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import RAW_DATA_PATH, DATA_DIR

def clean_text(text: str) -> str:
    """Removes double spacings, tabs, and standardizes case text format."""
    if not isinstance(text, str):
        return ""
    # Remove excessive white spaces and newlines
    text = " ".join(text.split())
    return text

def chunk_text(text: str, max_words: int = 350, overlap: int = 100) -> list[str]:
    """
    Segments long legal text into overlapping windows.
    This ensures that documents longer than BERT's 512-token limit 
    are not truncated, preserving critical facts near the end of cases.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text]
    
    chunks = []
    start = 0
    while start < len(words):
        end = start + max_words
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += (max_words - overlap)
        
        # Prevent infinite loops on tiny final increments
        if start + (max_words - overlap) >= len(words):
            break
            
    return chunks

def preprocess_dataset():
    if not os.path.exists(RAW_DATA_PATH):
        print(f"Error: Raw CSV not found at '{RAW_DATA_PATH}'. Please place your actual CSV file there.")
        return

    print("Reading raw dataset...")
    df = pd.read_csv(RAW_DATA_PATH)

    # 1. Identify and standardize active columns
    text_col = "case_facts" if "case_facts" in df.columns else df.columns[1]
    label_col = "applicable_sections" if "applicable_sections" in df.columns else df.columns[2]
    
    print(f"Using text column: '{text_col}' and label column: '{label_col}'")

    # 2. Drop rows with null values in core text columns
    df = df.dropna(subset=[text_col])
    
    processed_records = []
    print("Cleaning, formatting, and segmenting long case texts...")
    
    for idx, row in df.iterrows():
        raw_text = str(row[text_col])
        cleaned = clean_text(raw_text)
        
        # Segment long narratives into manageable overlapping chunks
        text_chunks = chunk_text(cleaned, max_words=350, overlap=100)
        
        # Save each chunk as a separate training/retrieval instance with the parent labels
        for chunk_idx, chunk in enumerate(text_chunks):
            processed_records.append({
                "parent_id": idx,
                "chunk_id": chunk_idx,
                "processed_text": chunk,
                "labels": str(row[label_col]) if label_col in df.columns else ""
            })

    processed_df = pd.DataFrame(processed_records)
    
    # Create target directory for processed files
    processed_dir = os.path.join(DATA_DIR, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # 3. Create training and validation splits for the model classifier
    print("Splitting dataset into training and validation sets...")
    train_df, val_df = train_test_split(processed_df, test_size=0.2, random_state=42)

    # Save to CSV files
    train_path = os.path.join(processed_dir, "train_split.csv")
    val_path = os.path.join(processed_dir, "val_split.csv")
    full_processed_path = os.path.join(processed_dir, "processed_cases.csv")

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    processed_df.to_csv(full_processed_path, index=False)

    print("\nPreprocessing complete:")
    print(f" -> Full processed corpus saved to: {full_processed_path} ({len(processed_df)} rows)")
    print(f" -> Train split saved to: {train_path} ({len(train_df)} rows)")
    print(f" -> Validation split saved to: {val_path} ({len(val_df)} rows)")

if __name__ == "__main__":
    preprocess_dataset()