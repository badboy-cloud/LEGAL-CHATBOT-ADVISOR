import os
import torch
from dotenv import load_dotenv

# Load local environment variables if any
load_dotenv()

# Set computing device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Pre-trained coordinate models
MODEL_NAME = "law-ai/InLegalBERT"

# Root relative directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_PATH = os.path.join(DATA_DIR, "raw", "case_files.csv")
INDEX_PATH = os.path.join(DATA_DIR, "vector_indices", "legal_index.faiss")
MODEL_SAVE_PATH = os.path.join(BASE_DIR, "models", "saved_classifier")