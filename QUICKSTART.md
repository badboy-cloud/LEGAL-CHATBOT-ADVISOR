# ⚡ Quick Start - 5 Minutes

## Prerequisites Installed?
- [ ] Python 3.10+
- [ ] Ollama (from https://ollama.ai)
- [ ] Git/terminal

## 🚀 Go! (Copy-Paste These Commands)

### Step 1: Prepare Environment
```bash
cd c:\Users\sesha\OneDrive\Desktop\chatbot
python -m venv venv
venv\Scripts\activate.bat
pip install --upgrade pip setuptools wheel
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Download Models
```bash
python -c "from transformers import AutoTokenizer, AutoModel; AutoTokenizer.from_pretrained('law-ai/InLegalBERT'); AutoModel.from_pretrained('law-ai/InLegalBERT'); print('✓ InLegalBERT ready')"
```

## 🎮 Run (3 Terminal Windows)

### Terminal 1: Ollama
```bash
ollama run deepseek-r1:7b
```
Wait until you see: `send a message`

### Terminal 2: Backend
```bash
cd c:\Users\sesha\OneDrive\Desktop\chatbot
venv\Scripts\activate.bat
python src/main.py
```
Wait until you see: `Uvicorn running on 0.0.0.0:8000`

### Terminal 3: Frontend
```bash
cd c:\Users\sesha\OneDrive\Desktop\chatbot
venv\Scripts\activate.bat
streamlit run frontend/app.py
```
Should auto-open: http://localhost:8501

## 🧪 Test It!

Try these queries:

1. **"False allegations damaged my reputation"**
   - Expected: Defamation, IPC 499/500

2. **"I was forced to work overtime without pay"**
   - Expected: Labour, Code of Wages

3. **"What's the weather?"**
   - Expected: Domain rejection

## ✅ Done!

Your system is live. Check:
- Backend: http://localhost:8000/health
- Frontend: http://localhost:8501
- API Docs: http://localhost:8000/docs

## 🆘 Issues?

| Problem | Fix |
|---------|-----|
| Port already in use | Change port in `src/main.py` or `frontend/app.py` |
| Ollama not found | Download from https://ollama.ai |
| InLegalBERT slow | First run downloads 600MB model |
| Connection error | Ensure all 3 services running |

## 📞 Full Docs
See `SETUP_GUIDE.md` for complete setup and `BUILD_COMPLETE.md` for architecture.

**Enjoy your Indian Legal Advisor!** ⚖️
