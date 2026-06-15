# Indian Legal Advisor - Setup & Configuration Guide

## Project Overview

The Indian Legal Advisor is an AI-powered legal document analysis system that:
- Predicts applicable IPC (Indian Penal Code) sections
- Retrieves similar legal cases using semantic search
- Provides confidence scores and detailed analysis results

### Technology Stack

- **Backend**: FastAPI + Python
- **Frontend**: Streamlit
- **ML Models**: InLegalBERT (Hugging Face), FAISS (Vector Search)
- **Data Processing**: PyTorch, Transformers, scikit-learn
- **Vector DB**: FAISS (CPU or GPU)

---

## Project Structure

```
chatbot/
├── app.py                          # Main entrypoint (routes to backend/frontend)
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (configured)
├── README.md                       # Project documentation
│
├── src/                           # Backend source code
│   ├── __init__.py
│   ├── config.py                  # Global configuration (reads from .env)
│   ├── main.py                    # FastAPI application entrypoint
│   │
│   ├── api/                       # API layer
│   │   ├── __init__.py
│   │   ├── routes.py              # API endpoints (/analyze, /status, /sections)
│   │   └── schemas.py             # Pydantic validation models
│   │
│   └── ml/                        # Machine learning engines
│       ├── __init__.py
│       ├── classifier.py          # InLegalBERT classifier for IPC prediction
│       ├── retriever.py           # FAISS retriever for semantic search
│       └── pooling.py             # Mean pooling for BERT embeddings
│
├── frontend/
│   └── app.py                     # Streamlit UI application
│
├── scripts/                       # Standalone scripts
│   ├── train_classifier.py        # Fine-tune classifier on IPC data
│   ├── train_classifier_new.py    # Alternative training script
│   ├── build_vector_db.py         # Build FAISS index from documents
│   ├── build_vector_db_new.py     # Alternative vector DB builder
│   └── notebooks/                 # Jupyter notebooks for experimentation
│
├── models/
│   └── saved_classifier/          # Saved classifier checkpoints
│
└── data/
    ├── raw/                       # Raw input data
    │   └── case_files_total.csv
    ├── processed/                 # Processed documents for FAISS indexing
    └── vector_indices/            # Saved FAISS indices
        └── legal_index.faiss      # Main vector index
```

---

## Configuration Files

### `.env` - Environment Variables

Located in project root. Stores configuration for:

**API Configuration:**
```env
API_HOST=0.0.0.0              # API host address
API_PORT=8000                 # API port
DEBUG=False                   # Debug mode (disable in production)
CORS_ORIGINS=*                # CORS allowed origins
WORKERS=4                     # Number of worker processes
```

**Model Configuration:**
```env
MODEL_NAME=law-ai/InLegalBERT # HF model identifier
MAX_SEQ_LENGTH=512            # BERT tokenizer max length
BATCH_SIZE=32                 # Training/inference batch size
LEARNING_RATE=0.00002        # Fine-tuning learning rate
NUM_EPOCHS=3                  # Training epochs
NUM_LABELS=50                 # Number of IPC sections
```

**FAISS Configuration:**
```env
EMBEDDING_DIM=768             # InLegalBERT embedding dimension
FAISS_USE_GPU=True            # Use GPU for FAISS (requires CUDA)
TOP_K_RETRIEVAL=5             # Number of similar cases to retrieve
RETRIEVAL_THRESHOLD=0.5       # Minimum similarity threshold
```

**Logging:**
```env
LOG_LEVEL=INFO                # Logging level (DEBUG, INFO, WARNING, ERROR)
```

### `src/config.py` - Global Configuration

Reads from `.env` and sets up:
- **Paths**: Project directories, data paths, model paths
- **Device**: CUDA if available, else CPU
- **Model parameters**: Loaded from environment
- **API settings**: Host, port, CORS configuration
- **Directory creation**: Automatically creates necessary directories

Key exports:
```python
DEVICE              # "cuda" or "cpu"
USE_GPU             # Boolean: whether GPU is available
PROJECT_ROOT        # Root project directory
DATA_DIR            # Data directory path
MODELS_DIR          # Models directory path
MODEL_NAME          # InLegalBERT model name
FAISS_INDEX_PATH    # Path to FAISS index file
# ... and many more configuration variables
```

### `requirements.txt` - Dependencies

**Core ML Dependencies:**
- `torch==2.0.0` - PyTorch framework
- `transformers==4.30.0` - Hugging Face transformers
- `sentence-transformers==2.2.2` - Sentence embeddings
- `faiss-cpu==1.7.4` - Vector search (or `faiss-gpu` for GPU support)

**Web Framework:**
- `fastapi==0.100.0` - Backend API
- `uvicorn==0.23.1` - ASGI server
- `pydantic==2.0.0` - Data validation

**Frontend:**
- `streamlit==1.28.0` - UI framework

**Data Processing:**
- `numpy`, `pandas`, `scikit-learn`, `scipy`

**Utilities:**
- `python-dotenv==1.0.0` - Load .env files
- `tqdm==4.65.0` - Progress bars
- `PyYAML==6.0` - YAML parsing

---

## Running the Application

### Option 1: Development Mode (Recommended)

**Terminal 1 - Start Backend API:**
```bash
cd c:\Users\SATHISH\OneDrive\Desktop\chatbot
python src/main.py
```
Backend will run at: `http://localhost:8000`
API docs: `http://localhost:8000/docs`

**Terminal 2 - Start Frontend:**
```bash
cd c:\Users\SATHISH\OneDrive\Desktop\chatbot
streamlit run frontend/app.py
```
Frontend will run at: `http://localhost:8501`

### Option 2: Using Root App.py

```bash
cd c:\Users\SATHISH\OneDrive\Desktop\chatbot
python app.py
```
This will start the backend API server.

### Option 3: Using Uvicorn Directly

```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Machine Learning Components

### 1. Classifier (`src/ml/classifier.py`)

**Purpose:** Predict applicable IPC sections from legal text

**Class:** `SequenceClassifier`

```python
from src.ml.classifier import SequenceClassifier

classifier = SequenceClassifier()
predictions = classifier.predict(
    texts=["legal document text"],
    threshold=0.5
)
# Output: [{"sections": [302, 304], "scores": [0.8, 0.6], ...}]
```

**Key Methods:**
- `__init__()` - Load InLegalBERT model
- `predict(texts, threshold)` - Get IPC section predictions
- `train()` - Fine-tune on custom data

### 2. Retriever (`src/ml/retriever.py`)

**Purpose:** Semantic similarity search using FAISS

**Class:** `FAISSRetriever`

```python
from src.ml.retriever import FAISSRetriever

retriever = FAISSRetriever()
retriever.load_index()  # Load from disk
similar = retriever.search(
    query_embeddings,
    k=5  # Top 5 similar documents
)
```

**Key Methods:**
- `create_index(embeddings)` - Create FAISS index
- `load_index()` - Load saved index
- `search(embeddings, k)` - Semantic search

### 3. Pooling (`src/ml/pooling.py`)

**Purpose:** Convert BERT token embeddings to document embeddings

**Function:** `mean_pooling(model_output, attention_mask)`

Applies mean pooling considering attention mask to exclude padding.

---

## API Endpoints

### Base URL: `http://localhost:8000`

#### 1. POST `/api/analyze`

Analyze a legal document and predict IPC sections.

**Request:**
```json
{
  "text": "The accused intentionally...",
  "threshold": 0.5
}
```

**Response:**
```json
{
  "predictions": {
    "sections": [302, 304],
    "scores": [0.85, 0.72],
    "raw_probabilities": [0.85, 0.72, ...]
  },
  "similar_cases": [],
  "confidence": 0.785
}
```

#### 2. GET `/health`

Check backend health and model status.

**Response:**
```json
{
  "status": "healthy",
  "classifier_loaded": true,
  "retriever_loaded": true
}
```

#### 3. GET `/api/status`

Get detailed backend status.

**Response:**
```json
{
  "status": "operational",
  "device": "cuda",
  "gpu_available": true,
  "retriever_ready": true
}
```

#### 4. GET `/api/sections`

Get available IPC sections (placeholder).

#### 5. POST `/api/batch-analyze`

Analyze multiple documents in batch.

**Request:**
```json
[
  {"text": "document 1", "threshold": 0.5},
  {"text": "document 2", "threshold": 0.5}
]
```

#### 6. GET `/`

Root endpoint with API information.

---

## Data Preparation

### Building Vector Database

Before using the retriever, build the FAISS index:

```bash
python scripts/build_vector_db.py
```

This script:
1. Loads processed documents from `data/processed/`
2. Generates InLegalBERT embeddings
3. Creates FAISS index
4. Saves index to `data/vector_indices/legal_index.faiss`

### Training Classifier

Fine-tune InLegalBERT on your labeled IPC data:

```bash
python scripts/train_classifier.py
```

This script:
1. Loads training data with IPC labels
2. Fine-tunes InLegalBERT model
3. Saves checkpoint to `models/saved_classifier/`

---

## Frontend UI Features

### Analyze Tab
- Enter legal text or case facts
- Set confidence threshold and retrieval parameters
- View predicted IPC sections with scores
- See similar legal cases

### Batch Process Tab
- Upload CSV with legal documents
- Or paste multiple documents
- Process multiple documents at once

### Help Tab
- Usage instructions
- Result interpretation guide
- System status and diagnostics

---

## Troubleshooting

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'torch'`
- Solution: Run `pip install -r requirements.txt`

**Error:** `Cannot connect to API`
- Check if backend is running: `python src/main.py`
- Verify API_HOST and API_PORT in `.env`

### Classifier Not Loading

**Error:** `Classifier not loaded`
- Download InLegalBERT from Hugging Face: Model is auto-downloaded on first use
- Check internet connectivity for model download
- Verify HF_HOME environment variable if using custom cache

### FAISS Index Not Found

**Error:** `FAISS index not found - build it with scripts/build_vector_db.py`
- Solution: Run `python scripts/build_vector_db.py` to create index
- Ensure processed documents exist in `data/processed/`

### CUDA/GPU Issues

**Problem:** FAISS not using GPU
- Ensure FAISS_USE_GPU=True in `.env`
- Install CUDA and cuDNN
- Use `faiss-gpu` instead of `faiss-cpu` in requirements.txt

---

## Development Workflow

### 1. Setup Environment
```bash
pip install -r requirements.txt
```

### 2. Configure Settings
Edit `.env` as needed for your setup

### 3. Prepare Data
- Place raw documents in `data/raw/`
- Process and save to `data/processed/`
- Run `python scripts/build_vector_db.py`

### 4. Train Model (Optional)
```bash
python scripts/train_classifier.py
```

### 5. Start Backend
```bash
python src/main.py
```

### 6. Start Frontend
```bash
streamlit run frontend/app.py
```

### 7. Test API
Visit `http://localhost:8000/docs` for interactive documentation

---

## Production Deployment

### Using Gunicorn (Recommended)

```bash
gunicorn -w 4 -b 0.0.0.0:8000 --access-logfile - src.main:app
```

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/main.py"]
```

Build and run:
```bash
docker build -t legal-advisor .
docker run -p 8000:8000 legal-advisor
```

---

## Performance Tips

1. **Batch Processing**: Process documents in batches for better throughput
2. **GPU Usage**: Enable FAISS_USE_GPU=True for faster retrieval
3. **Caching**: Streamlit caches model loading - subsequent requests are faster
4. **CORS Optimization**: Set specific CORS_ORIGINS instead of "*" in production

---

## Support & Contributing

For issues, bug reports, or contributions, please refer to the GitHub repository or contact the development team.

---

**Version:** 0.1.0  
**Last Updated:** May 30, 2026
