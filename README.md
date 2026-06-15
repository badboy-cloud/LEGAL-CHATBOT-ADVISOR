# Indian Legal Advisor AI

A production-style AI legal advisor chatbot for Indian law using InLegalBERT, FAISS, and Ollama Qwen3:8B.

## 🎯 Features

- **InLegalBERT Embeddings**: Deep legal semantic understanding
- **FAISS Vector Search**: Fast retrieval of relevant precedents
- **Topic-Aware Classification**: Accurate legal domain classification (10 topics)
- **Statute Prediction**: Hybrid scoring for relevant IPC sections
- **Qwen3 Reasoning**: Context-grounded legal advice and FIR analysis generation
- **FIR Document Analysis**: Upload scanned FIRs (PDF, JPG, PNG) for text extraction, OCR, structured metadata parsing, and legal risk assessment
- **Precedent Retrieval**: 3 most similar cases with citation and facts
- **Clean Architecture**: Modular, maintainable codebase
- **Performance Optimized**: 10-30 second response times

## 📋 Supported Legal Topics

- Defamation (IPC 499-500)
- Labour & Employment
- Property Law
- Cyber Law (IT Act)
- Family Law
- Criminal Law
- Contract Law
- Consumer Law
- Constitutional Law
- Civil Law

## 🏗️ Architecture

```
Indian Legal Advisor
├── Frontend (Streamlit)
│   └── User-friendly interface (Legal Advice & FIR tabs)
│
├── Backend (FastAPI)
│   ├── Routes & API endpoints (including FIR analysis)
│   └── Legal Pipeline orchestration
│
└── ML Components
    ├── InLegalBERT Engine (embeddings)
    ├── Topic Classifier (hybrid: embedding + keyword)
    ├── Statute Predictor (IPC section mapping)
    ├── FAISS Retriever (precedent search)
    ├── Regex FIR Parser (No LLM, regex-based metadata extraction)
    └── LLM Engine (Qwen3:8B via Ollama, called once for legal analysis)
```

### FIR Analysis Pipeline Architecture:
```text
FIR Upload
→ OCR/PDF Extraction (pypdf / pytesseract)
→ Regex FIR Parser (No LLM, < 1s extraction)
→ InLegalBERT Classification (legal domain & confidence)
→ FAISS Retrieval (similar precedents, cases, FIR examples)
→ Qwen3 Legal Analysis (LLM called once with structured context)
→ Streamlit Dashboard (timing performance & advisory reports)
```

Data Layer
├── Statutes (statutes.json)
├── Topics (topic_mapping.json)
└── Precedents (precedents.json)

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- CUDA/GPU recommended (but CPU works)
- Ollama installed with qwen3:8b model
- Tesseract OCR installed and active in system PATH (for image analysis)

### Installation

1. **Clone repository**
```bash
cd chatbot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/Scripts/activate  # Windows
# or
source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Download InLegalBERT model**
```bash
python -c "from transformers import AutoTokenizer, AutoModel; \
AutoTokenizer.from_pretrained('law-ai/InLegalBERT'); \
AutoModel.from_pretrained('law-ai/InLegalBERT')"
```

### Running the System

**Terminal 1: Start Ollama Qwen3**
```bash
ollama run qwen3:8b
```

**Terminal 2: Start FastAPI Backend**
```bash
python src/main.py
```

API will be available at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`

**Terminal 3: Start Streamlit Frontend**
```bash
streamlit run frontend/app.py
```

Frontend will be available at `http://localhost:8501`

## 📚 Usage

### Web Interface (Streamlit)

1. Open `http://localhost:8501`
2. **Legal Query Advisory Tab**:
   - Enter your legal query (e.g., "I was forced to work overtime without compensation")
   - Click "Analyze Query"
   - View AI legal advice, identified legal topic, applicable statutes, and retrieved precedents.
3. **FIR Document Analysis Tab**:
   - Upload an FIR document (PDF, JPG, PNG)
   - Click "Analyze FIR Document"
   - View extracted metadata (FIR No, Police Station, Parties, Statutes) and AI Legal Advisory Report with risk level assessment.

### API Usage

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "False allegations damaged my reputation",
    "domain_threshold": 0.3
  }'
```

## 🔧 Configuration

### Statute Prediction Thresholds
- **HIGH_CONFIDENCE**: ≥ 0.75
- **MEDIUM_CONFIDENCE**: ≥ 0.55
- **LOW_CONFIDENCE**: < 0.55

### FAISS Retrieval
- **Similarity Threshold**: 0.65
- **Top-K Results**: 3
- **Topic Filtering**: Ensures only same-topic cases retrieved

### Qwen3 LLM
- **Model**: qwen3:8b
- **Temperature**: 0.3 (deterministic)
- **Max Tokens**: 250 (fast responses)
- **Timeout**: 180 seconds

## 🧪 Testing

```python
# Test individual components
python src/ml/inlegalbert_engine.py
python src/ml/legal_topic_classifier.py
python src/ml/statute_predictor.py
python src/ml/faiss_retriever.py
python src/services/legal_pipeline.py
```

## 📊 Performance

Typical response times:
- Domain validation: 0.5-1s
- Topic classification: 1-2s
- Statute prediction: 1-2s
- FAISS retrieval: 0.5-1s
- LLM generation: 5-15s
- **Total: 10-30 seconds**

## 🛠️ Troubleshooting

### Ollama Connection Error
```
Error: Cannot connect to Ollama
Solution: Ensure Ollama is running: ollama run qwen3:8b
```

### FAISS Index Error
```
Error: No precedents found
Solution: Verify precedents.json exists in data/ directory
```

### Memory Issues
```
Error: Out of memory with InLegalBERT
Solution: Use GPU (CUDA) or reduce batch size
```

## ⚖️ Legal Disclaimer

This system provides AI-generated legal information for educational purposes only. It does **NOT** constitute legal advice. Always consult a qualified Indian lawyer for specific guidance on your legal matter.

## 🤝 Contributing

Contributions welcome! Please ensure PEP 8 guidelines and comprehensive logging/error handling.

## 📜 License

[MIT License](LICENSE)

## 👥 Authors

- AI Development Team
- Legal Domain Experts

## 🔗 References

- [InLegalBERT](https://huggingface.co/law-ai/InLegalBERT)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Ollama](https://ollama.ai)
- [FastAPI](https://fastapi.tiangolo.com)
- [Streamlit](https://streamlit.io)

---

**Last Updated**: June 2026
**Version**: 1.0.0
