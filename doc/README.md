# Indian Legal Advisor

An AI-powered legal document analyzer that predicts applicable Indian Penal Code (IPC) sections and retrieves similar legal cases using semantic search.

## Features

- **Multi-label IPC Section Classification**: Automatically identifies relevant IPC sections from legal documents using fine-tuned InLegalBERT
- **Semantic Case Retrieval**: Finds similar legal cases using FAISS vector search
- **FastAPI Backend**: RESTful API for document analysis
- **Streamlit UI**: User-friendly interface for legal professionals and students
- **Scalable Architecture**: Modular design for easy extension and maintenance

## Project Structure

```
indian-legal-advisor/
├── data/
│   ├── raw/                       # Raw Indian legal datasets
│   ├── processed/                 # Tokenized and cleaned text files
│   └── vector_indices/            # FAISS index files
├── models/
│   └── saved_classifier/          # Fine-tuned InLegalBERT weights
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   └── 02_classifier_training.ipynb
├── src/
│   ├── config.py                  # Global settings
│   ├── ml/
│   │   ├── classifier.py          # Sequence Classifier
│   │   ├── pooling.py             # Embedding pooling
│   │   └── retriever.py           # FAISS retrieval
│   ├── api/
│   │   ├── routes.py              # API endpoints
│   │   └── schemas.py             # Pydantic models
│   └── main.py                    # FastAPI entrypoint
├── frontend/
│   └── app.py                     # Streamlit application
├── scripts/
│   ├── train_classifier.py        # Model fine-tuning
│   └── build_vector_db.py         # Build FAISS index
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

## Installation

### Prerequisites

- Python 3.8+
- pip or conda
- CUDA (optional, for GPU acceleration)

### Setup

1. **Clone the repository**
   ```bash
   cd indian-legal-advisor
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env .env.local
   # Edit .env.local with your settings
   ```

## Usage

### 1. Data Preparation

Prepare your legal documents:
- Place raw documents in `data/raw/`
- Preprocess and save to `data/processed/`

### 2. Build Vector Database

```bash
python scripts/build_vector_db.py
```

Creates FAISS index for semantic search over your legal documents.

### 3. Train Classifier (Optional)

Fine-tune the model on your specific IPC sections:

```bash
python scripts/train_classifier.py
```

### 4. Start the Backend

```bash
python src/main.py
```

The API will be available at `http://localhost:8000`

API endpoints:
- `POST /api/analyze` - Analyze legal document
- `GET /api/sections` - Get available IPC sections
- `GET /health` - Health check

### 5. Run the Frontend

In another terminal:

```bash
streamlit run frontend/app.py
```

Access the UI at `http://localhost:8501`

## API Documentation

### Analyze Document

**Endpoint**: `POST /api/analyze`

**Request**:
```json
{
  "text": "Your legal document text here...",
  "threshold": 0.5
}
```

**Response**:
```json
{
  "predictions": {
    "sections": [302, 304, 326],
    "scores": [0.85, 0.72, 0.68],
    "raw_probabilities": [...]
  },
  "similar_cases": [...],
  "confidence": 0.75
}
```

## Model Details

- **Base Model**: InLegalBERT (specialized for Indian legal text)
- **Task**: Multi-label sequence classification
- **Embedding Dimension**: 768
- **Max Sequence Length**: 512 tokens
- **Vector Search**: FAISS with L2 distance

## Configuration

Edit `src/config.py` or `.env` to customize:

- Model name and hyperparameters
- API host and port
- Batch size and learning rate
- FAISS index settings

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/ frontend/ scripts/
```

### Linting

```bash
flake8 src/ frontend/ scripts/
```

## Troubleshooting

### GPU Memory Issues

- Reduce `BATCH_SIZE` in `config.py`
- Use CPU by setting environment: `CUDA_VISIBLE_DEVICES=-1`

### FAISS Index Not Found

- Ensure you've run `scripts/build_vector_db.py`
- Check that `data/processed/` contains documents

### Model Download Issues

- Ensure internet connection for downloading InLegalBERT
- Models will be cached in `~/.cache/huggingface/`

## Performance

- Classification inference: ~100-500ms per document (depends on length and hardware)
- FAISS search: <10ms for retrieval of top-k results
- Embedding generation: ~50-100 docs/second (batch processing)

## Future Enhancements

- [ ] Multi-language support (Hindi, Tamil, etc.)
- [ ] Judgment summarization
- [ ] Case law precedent tracking
- [ ] Interactive case comparison tool
- [ ] Batch document processing API
- [ ] Web-based case law annotation tool

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: support@legalaiadvisor.com

## Citation

If you use this project in your research, please cite:

```bibtex
@software{indian_legal_advisor,
  title={Indian Legal Advisor: AI-Powered Legal Document Analysis},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/indian-legal-advisor}
}
```

## Disclaimer

This tool is designed to assist legal professionals and students. It should not be used as a substitute for professional legal advice. Always consult with qualified legal experts for important legal matters.
