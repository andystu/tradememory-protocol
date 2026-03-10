# Task 8 Rules: pgvector Hybrid Recall

> 開始前讀 ARCHITECTURE_RULES.md 第 7 節（Hybrid Recall 規則）+ 第 6 節（Error Handling）

## 必須遵守的規則

### R1: hybrid_recall() 是 pure function，不寫 DB
```python
# ❌ recall 函數裡面寫 DB
def hybrid_recall(query, memories):
    results = compute_scores(query, memories)
    db.insert_recall_event(results)  # side effect
    return results

# ✅ pure function 只算分
def hybrid_recall(query, memories, alpha=0.3) -> list[ScoredMemory]:
    """Pure function: compute scores only. No side effects."""
    candidates = pgvector_search(query.embedding, limit=50)
    scored = outcome_weighted_recall(query.context, candidates)
    return rerank(candidates, scored, alpha)
```

### R2: Embedding 必須可以降級
```python
# 如果 sentence-transformers 沒裝 → 自動降級為 pure OWM recall
def hybrid_recall(query, memories, alpha=0.3):
    if query.embedding is not None and has_vector_support():
        candidates = pgvector_search(query.embedding, limit=50)
    else:
        candidates = memories  # fallback: 全部丟給 OWM
    return outcome_weighted_recall(query.context, candidates)
```

### R3: EmbeddingBackend 是 Protocol（可換 backend）
```python
class EmbeddingBackend(Protocol):
    def embed(self, text: str) -> list[float]: ...

# 現在: SentenceTransformerBackend (PyTorch ~2GB)
# 未來: OnnxBackend (ONNX Runtime ~200MB)
```

### R4: 永遠不要吞掉 embedding 錯誤
```python
# ❌
try: embedding = model.encode(text)
except: pass

# ✅
try: embedding = model.encode(text)
except Exception as e:
    logger.warning(f"Embedding failed for trade {trade_id}: {e}")
    embedding = None  # 明確降級：走 pure OWM
```

## 完成前 Checklist

- [ ] hybrid_recall() 沒有 side effect（不寫 DB）
- [ ] 沒有 sentence-transformers 時能 fallback 到 pure OWM
- [ ] EmbeddingBackend 是 Protocol（可換 backend）
- [ ] 所有 exception 有 log + 明確降級策略
- [ ] 有 empty DB edge case test
- [ ] 有 no-vector fallback test
- [ ] 有 alpha=0 (pure OWM) 和 alpha=1 (pure vector) test
- [ ] ensure_negative_balance 有 test
