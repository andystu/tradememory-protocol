# Task 4 Rules: Core Dashboard API + CORS

> 開始前讀 ARCHITECTURE_RULES.md 第 1 節（分層架構）+ 第 3 節（API 規則）+ 第 6 節（Error Handling）+ 第 8 節（命名規則）

## 必須遵守的規則

### R1: 分層架構 — API 不直接碰 DB
```python
# ❌ API 層直接寫 SQL
@router.get("/dashboard/overview")
async def overview():
    result = await session.execute(text("SELECT * FROM trade_records"))

# ✅ API → Service → Repository
@router.get("/dashboard/overview")
async def overview(service: DashboardService = Depends(get_dashboard_service)):
    return await service.get_overview()
```

### R2: Response 必須是 Pydantic Model
```python
# ❌ return dict
return {"total_pnl": 123.45}

# ✅ return typed model
class OverviewResponse(BaseModel):
    total_trades: int
    total_pnl: float
    win_rate: float
    ...

@router.get("/dashboard/overview", response_model=OverviewResponse)
```

### R3: 具體例外 + HTTPException
```python
# ❌ bare except
except: return {"error": "..."}

# ✅ 具體例外
except DatabaseConnectionError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=503, detail="Database temporarily unavailable")
```

### R4: 檔案結構
```
schemas.py          ← Pydantic request/response models
services/dashboard.py ← DashboardService
repositories/trade.py ← TradeRepository
exceptions.py       ← 自定義例外
dashboard_api.py    ← APIRouter（只做 request/response 轉換）
```

## 完成前 Checklist

- [ ] API endpoint 不直接碰 DB（透過 Service → Repository）
- [ ] 所有 response 用 Pydantic model（response_model 參數）
- [ ] try/except 用具體例外類別（不用 bare except）
- [ ] 所有 error 有 log（不吞掉）
- [ ] exceptions.py 有自定義例外類別
- [ ] CORS middleware 正確設定
