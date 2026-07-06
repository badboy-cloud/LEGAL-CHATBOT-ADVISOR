# Indian Legal Advisor AI

A production-grade AI legal advisory SaaS platform for Indian law, utilizing InLegalBERT, FAISS vector search, and Ollama Qwen3:8B reasoning. Equipped with enterprise security, document OCR pipelines, and an interactive chat assistant.

---

## 🎯 Features

- **Decoupled Frontend Dashboard:** Modern, glassmorphic dark-theme HTML5/CSS3/JavaScript (ES6) dashboard built with Bootstrap 5 and Font Awesome.
- **Enterprise-Grade Security:**
  - **Bcrypt Hashing:** Salted password storage.
  - **JWT Authentication:** Stateful token lifecycles checking active user sessions.
  - **Role-Based Access Control (RBAC):** Restricts administrative functions (e.g. audit logs, document metadata, role updates) to Admin users.
  - **AES-256 Symmetric Encryption:** Transparently encrypts uploaded PDF/images and sensitive database columns (usernames, audit records, file paths).
  - **Anti-Malware File Inspection:** Enforces <10MB size limits, validates magic bytes to block masqueraded scripts/binaries, and scans files via Windows Defender CLI (`MpCmdRun.exe`).
  - **API Rate Limiting:** Enforces a maximum of 20 requests per minute per IP or authenticated user.
  - **Custom Security Headers:** CORS configuration, HSTS, Content-Security-Policy (CSP), X-Frame-Options (DENY), and X-Content-Type-Options (nosniff).
- **InLegalBERT & FAISS RAG Retrieval:** Classifies legal queries and retrieves similar precedents.
- **FIR Document Analysis:** Uploads scanned FIRs for OCR text extraction, timeline generation, and risk assessment.
- **Legal Notice Scanner:** Extracts sender/recipient details, key allegations, cited provisions, and exports formatted markdown briefings.
- **Contextual & Standalone Case Chat:** Chat directly inside the parsed document context or ask general statutory questions.

---

## 🏗️ Architecture

```text
Indian Legal Advisor
├── Web Frontend (SaaS Dashboard)
│   ├── HTML5 / CSS3 (Bootstrap 5, Glassmorphism, Responsive)
│   └── JavaScript ES6 (Fetch REST client, LocalStorage JWT credentials)
│
├── API Server (FastAPI Backend)
│   ├── JWT Auth & Bcrypt password manager
│   ├── Security Headers Middleware & Rate Limiting
│   └── Route controllers (FIR, Notice, Query, Chat, Admin logs)
│
└── ML & Storage Layers
    ├── SQLite DB (Column-Level Encrypted users, documents, audit_logs)
    ├── Encrypted Cache (Symmetric AES-256 disk cache for LLM answers)
    ├── InLegalBERT Embeddings Engine
    ├── FAISS Vector Index (precedents search)
    └── LLM Engine (Qwen3:8B via Ollama, invoked once per analytical query)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Ollama installed with `qwen3:8b` model
- Tesseract OCR installed and active in system PATH (required for scanned document text extraction)

### Installation

1. **Clone the repository & enter the folder**
   ```bash
   cd chatbot
   ```

2. **Set up the virtual environment**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows
   # or
   source venv/bin/activate      # On Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify environment variables (`.env`)**
   Ensure `.env` in the root folder contains valid cryptographic keys:
   ```ini
   JWT_SECRET=e2c637dc3181d5e5c3731929862bf6e0ee3f44e33ee099d3599a0df292e155a0
   ENCRYPTION_KEY=RTvWb4G9tEMLej5DfW5xNvufXVjP735X23rVt9kfRR8=
   DATABASE_URL=data/legal_advisor.db
   RATE_LIMIT_RPM=20
   SSL_ENABLED=False
   ```

---

## 💻 Running the System

To launch the complete application, open two separate terminal windows:

### Terminal 1: Start FastAPI Backend
Ensure the virtual environment is active and launch the server:
```bash
python src/main.py
```
- API will be active at `http://127.0.0.1:8000`
- Interactive Swagger docs at `http://127.0.0.1:8000/docs`

### Terminal 2: Serve SaaS HTML Frontend
Launch a local web server to serve the frontend files from the `frontend/` directory (e.g., using Python's static server or `npx`):
```bash
python -m http.server -d frontend 5500
```
- Open your browser and navigate to: **`http://localhost:5500`**
- You will be gated by the Secure Sign-in panel. Register a new account (choose Admin role if you want to inspect audit tables) and sign in.

---

## 📚 Security Configurations & Auditing

Full documentation on security implementations, including cryptographic schemas, temporary cleanup routines, malware scanners, and database definitions is located in [doc/SECURITY.md](file:///c:/Users/sesha/OneDrive/Desktop/chatbot/doc/SECURITY.md).

---

## ⚖️ Legal Disclaimer

This platform provides AI-assisted legal research and educational reference information only. It does **NOT** constitute professional legal advice. Always consult a qualified advocate for official counsel on your legal matters.
