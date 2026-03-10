# Task 7 Rules: Reflections + Beliefs + Dreams API

> 開始前讀 ARCHITECTURE_RULES.md 第 1 節（分層）+ 第 6 節（Error Handling）

## 必須遵守的規則

### R1: 分層架構不變
即使讀 markdown 檔案（reflections）也走 Service → Repository 模式。
Repository 負責 file system access，Service 負責 parsing logic。

### R2: 永遠不要吞掉錯誤
```python
# ❌
try:
    parse_markdown(path)
except:
    pass

# ✅
try:
    return parse_markdown(path)
except MarkdownParseError as e:
    logger.warning(f"Failed to parse reflection {path}: {e}")
    return None  # 明確的降級：跳過這個檔案
```

### R3: 路徑不存在 = 回空列表，不是 error
dream-results 路徑不存在、daily_reviews/ 不存在 → return []。
這是正常狀態（還沒跑 daily_review.py），不是 500 error。

### R4: Response 都是 Pydantic model
beliefs 的 confidence = alpha/(alpha+beta) 計算在 Service 層。

## 完成前 Checklist

- [ ] 分層：API → Service → Repository
- [ ] 路徑不存在回空列表（不是 500）
- [ ] 沒有吞掉的 exception（都有 log）
- [ ] markdown parse 失敗不影響其他結果
- [ ] 每個 endpoint 有 happy + empty + edge case tests
