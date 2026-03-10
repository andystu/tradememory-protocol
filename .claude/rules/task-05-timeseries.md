# Task 5 Rules: Time Series + Memory Growth API

> 繼承 Task 4 的分層規則。開始前讀 ARCHITECTURE_RULES.md 第 1 節 + 第 3 節 + 第 5 節（測試規則）

## 必須遵守的規則

### R1: 分層架構不變
每個新 endpoint 都走 API → Service → Repository。不要因為「只是查詢」就在 API 層直接寫 SQL。

### R2: 查詢用 SQLAlchemy ORM/Core
```python
# ✅
result = await session.execute(
    select(TradeRecordModel)
    .where(TradeRecordModel.pnl.isnot(None))
    .order_by(TradeRecordModel.timestamp.asc())
)
```

### R3: 每個 Service method 三種 test
```python
async def test_equity_curve_happy_path(service, sample_trades): ...
async def test_equity_curve_empty_db(service): ...          # 空 DB 不 crash
async def test_equity_curve_single_trade(service, one_trade): ...  # 邊界值
```

### R4: 計算邏輯在 Service 層
drawdown 計算、rolling window、regime 分組 — 這些是業務邏輯，放 Service，不放 Repository。

## 完成前 Checklist

- [ ] 每個 endpoint 走 API → Service → Repository
- [ ] 查詢用 SQLAlchemy（不是 raw SQL）
- [ ] 每個 endpoint 有 happy path + empty + edge case tests
- [ ] 計算邏輯在 Service 層（Repository 只做 data access）
- [ ] Response 都是 Pydantic model
