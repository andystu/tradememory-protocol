# Task 16 Rules: Build Integration + Deploy

> 開始前讀 ARCHITECTURE_RULES.md 第 9 節（向後相容）+ 第 10 節（驗收 Checklist）

## 必須遵守的規則

### R1: 向後相容 — 不動 db.py
```
db.py（SQLite）           → 保留，不動，MCP tools 繼續用
database.py（PostgreSQL） → dashboard API + hybrid recall 用
```
static file mount 不能影響現有 API endpoint。

### R2: catch-all route 要排除 API prefix
```python
# static SPA routing 的 catch-all 必須排除所有 API prefix：
# /dashboard/, /trade/, /state/, /reflect/, /mt5/, /risk/,
# /patterns/, /adjustments/, /owm/, /health
```

### R3: 現有 tests 必須全部通過
跑 `python -m pytest tests/ -x -q`。如果新 import 導致 fail，修 import，不改 test。

### R4: dashboard/dist/ 不進 git
build artifact 加進 .gitignore。

## 完成前 Checklist（最終驗收）

- [ ] `python -m tradememory` 能同時 serve API + dashboard
- [ ] http://localhost:8000/ 顯示 dashboard
- [ ] http://localhost:8000/intelligence refresh 不 404（SPA routing）
- [ ] http://localhost:8000/dashboard/overview 回傳 JSON（API 不被 catch-all 吃掉）
- [ ] http://localhost:8000/health 正常（不被 static 影響）
- [ ] 現有 tests 全部通過（python -m pytest tests/ -x -q）
- [ ] dashboard/dist/ 在 .gitignore
- [ ] ROADMAP.md 更新了 Phase 7
