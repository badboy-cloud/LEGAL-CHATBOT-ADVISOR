# Quick Testing Guide - Backend v4.3

## Test These Queries

### Test 1: Labour Query (Should return labour law ONLY)
```
Query: "I am being forced to work overtime without compensation"

✅ CORRECT BEHAVIOR:
- Topic: labour_employment
- Statutes: 2(k), Factories Act, Labour Code (NOT 499/500/498A)
- Cases: 0 (database has no labour law - this is CORRECT, not an error)
- Answer: Discusses workplace rights, overtime law
- NO mention of: defamation, dowry, fraud, murder

❌ WRONG BEHAVIOR:
- Returns 498A (dowry)
- Returns generic answer
- Mentions multiple unrelated domains
```

### Test 2: Defamation Query (Should return defamation law ONLY)
```
Query: "What legal action can be taken against a person spreading false allegations about me?"

✅ CORRECT BEHAVIOR:
- Topic: defamation
- Statutes: 499, 500, 211 (defamation sections)
- Cases: ~1 (2020 (2) SCR 445)
- Answer: Discusses false allegations, reputation damage, IPC 499/500
- NO mention of: labour, dowry, property, fraud

❌ WRONG BEHAVIOR:
- Returns 498A (dowry) or 302 (murder)
- Returns labour law information
- Generic handling without specificity
```

### Test 3: Property Query (Should return property law or empty)
```
Query: "My neighbor is encroaching on my property"

✅ CORRECT BEHAVIOR:
- Topic: property
- Statutes: 379, 380, 426, 427 (theft/property sections)
- Cases: 0 (database has no property law - still CORRECT)
- Answer: Discusses trespassing, property rights, legal remedies
- NO mention of: defamation, labour, dowry

❌ WRONG BEHAVIOR:
- Returns dowry cases
- Returns fraud cases
- Mixed statutes from multiple domains
```

---

## What to Watch For in Logs

### ✅ CORRECT LOG OUTPUT:

```
[STEP2] Semantic topic classification (using InLegalBERT)...
  [TOPIC] defamation (confidence: 92.34%)

[STEP3] Semantic statute prediction...
  [PRIMARY_TOPIC] Using dominant topic: defamation (92.34%)
  [CANDIDATES] Found 3 candidate statutes for defamation
  [DEBUG] Candidates: ['499', '500', '211']
  [STATUTES] ['499', '500'] (89.00%, 89.00%)

[STEP4] Hybrid FAISS retrieval with topic filtering...
  [RETRIEVAL] Predicted topic (from statute_predictor): defamation
  [*] Filtering by legal topic: defamation
  [✓] Found 1 candidates matching topic 'defamation'
  [PRECEDENTS] Retrieved 1 cases (0.83s)

[STEP5] Generating grounded legal advice...
  [LLM] Topic: defamation
  [LLM_RESPONSE] Received in 12.34s
  
[ANSWER GENERATED] Confidence: 0.80
```

### ❌ WRONG LOG OUTPUT (What we're fixing):

```
[TOPIC] general (10.23%)  # ← Topic not detected
[CANDIDATES] Found 15 candidate statutes  # ← Too many (mixed domains)
[FALLBACK] Using best semantic candidates (relax topic filter)  # ← Cross-domain!
[PRECEDENTS] Retrieved 5 cases  # ← Might include unrelated ones
[LLM] No topic context in prompt  # ← Generic answer
```

---

## Quick Verification Steps

### 1. Check logs during startup
```
Look for:
[CONFIG] SIMILARITY_THRESHOLD: 0.65
[IMPROVEMENTS]
  • Cosine similarity with normalized embeddings
  • Primary topic only (prevents mixing labour + fraud statutes)
  • Comprehensive debugging logs throughout pipeline
```

### 2. Send labour query via curl
```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "I am being forced to work overtime without compensation"}'
```

**Check response**:
- `predicted_statutes`: Should be labour-related (2(k), Factories Act)
- `retrieved_precedents`: Should be empty (no labour law in DB - this is OK)
- `answer`: Should discuss workplace rights, NOT dowry/fraud

### 3. Send defamation query
```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "What legal action can be taken against a person spreading false allegations?"}'
```

**Check response**:
- `predicted_statutes`: Should be [499, 500, 211]
- `retrieved_precedents`: Should have ~1 defamation case
- `answer`: Should mention false allegations, defamation, IPC 499/500

### 4. Frontend UI test
- Go to http://localhost:8501
- Enter queries one by one
- Verify each shows DIFFERENT legal analysis
- No repeated outputs

---

## Success Criteria

After the fix, you should see:

| Query | Topic | Statutes | Cases | Confidence |
|-------|-------|----------|-------|-----------|
| Overtime | labour_employment | 2(k), Factories Act | 0 | 0.5 |
| Defamation | defamation | 499, 500 | 1 | 0.8 |
| Property | property | 379, 380 | 0 | 0.5 |

✅ **Each query gets DIFFERENT legal analysis from different domain**
✅ **No repeated "generic" outputs**
✅ **Statutes are domain-specific**
✅ **Cases returned are domain-matched or empty (not cross-pollinated)**

---

## If Still Seeing Issues

### Issue: Still returning wrong statutes
- Check STEP 2 log: Is topic correctly identified?
- If topic wrong, InLegalBERT model might need reload
- Solution: Restart Python environment, clear cache

### Issue: Still mixing domains
- Check STEP 4 log: Is "Filtering by legal topic" showing correct topic?
- If filtering shows correct topic but returns unrelated cases, check database
- Solution: Verify database actually has cases for that topic

### Issue: Empty results
- This is CORRECT if database lacks that legal domain
- Check response shows proper statutes even with 0 cases
- Solution: Use frontend to verify both statutes AND answer text

### Issue: Still getting generic answers
- Check STEP 5 log: Is `[LLM] Topic:` showing correct domain?
- If topic present, DeepSeek might have timed out
- Solution: Check log for `[FALLBACK]` or `[TIMEOUT]`

---

## Quick Commands

### Start backend
```bash
cd c:\Users\sesha\OneDrive\Desktop\chatbot
.\venv\Scripts\Activate.ps1
uvicorn src.main:app --reload --port 8000
```

### Start frontend
```bash
streamlit run frontend/app.py
```

### Test health
```bash
curl http://127.0.0.1:8000/api/health
```

### Expected: 
```json
{
  "status": "healthy",
  "classifier": "loaded",
  "retriever": "loaded",
  "statute_mapper": "loaded"
}
```

---

## Summary

The backend is fixed and ready to test. Use the three test queries above and verify that:
1. Different queries produce DIFFERENT legal analysis
2. Each domain stays pure (no cross-pollution)
3. Statutes match the legal domain
4. Cases (or lack thereof) match the domain

Good luck! 🚀
