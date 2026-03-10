# Task 6 Rules: Intelligence + Strategy API

> 開始前讀 ARCHITECTURE_RULES.md 第 1 節（分層）+ 第 7.1 節（Pure function + side effect 分離）

## 必須遵守的規則

### R1: recall event logging 是 side effect，在 MCP handler 層做
```python
# ❌ 在 recall 函數裡寫 DB
def hybrid_recall(query, memories):
    results = compute_scores(query, memories)
    db.insert_recall_event(results)  # side effect 混在 pure function
    return results

# ✅ MCP tool handler / API handler 才做 side effect
@router.post("/owm/recall")
async def recall(request, service, recall_event_repo):
    results = service.recall(request)
    await recall_event_repo.log_event(request, results)  # side effect 在這裡
    return results
```

### R2: Strategy baselines 是常數，放在 Service 或 config
```python
BATCH_001_BASELINES = {
    "VolBreakout": {"pf": 1.17, "wr": 0.55},
    "IntradayMomentum": {"pf": 1.78, "wr": 0.58},
    "Pullback": {"pf": 1.45, "wr": 0.52},
}
```

### R3: 具體例外處理 strategy not found
```python
except StrategyNotFoundError:
    raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
```

## 完成前 Checklist

- [ ] recall event logging 在 handler 層，不在 recall function 裡
- [ ] recall logging 失敗不影響 recall response（try/except + log）
- [ ] strategy/{name} 有 404 處理
- [ ] 每個 endpoint 有 happy + empty + edge case tests
- [ ] 分層架構：API → Service → Repository
