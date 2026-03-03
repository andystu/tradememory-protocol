# L2 Patterns Table + Automated Pattern Discovery

## Goal
建 patterns table，讓 ReflectionEngine 自動從 backtest 數據發現 patterns，寫入 DB，然後跟手動的 5 條 L2（MR-001 等）比對驗證。

## Step 1: db.py — 加 patterns table + CRUD

在 `_init_schema()` 加 CREATE TABLE：
```sql
CREATE TABLE IF NOT EXISTS patterns (
    pattern_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    confidence REAL NOT NULL,
    sample_size INTEGER NOT NULL,
    date_range TEXT NOT NULL,
    strategy TEXT,
    symbol TEXT,
    source TEXT NOT NULL,
    discovered_at TEXT NOT NULL
)
```
加 index on `(strategy, symbol)`。

新增 3 個 methods：
- `insert_pattern(pattern_data: Dict) -> bool` — INSERT OR REPLACE
- `query_patterns(strategy=None, symbol=None, source=None) -> List[Dict]`
- `get_pattern(pattern_id: str) -> Optional[Dict]`

## Step 2: reflection.py — 加 `discover_patterns_from_backtest()`

在 ReflectionEngine 加新方法，整合 `parse_batch_results.py` 的核心邏輯：

```python
def discover_patterns_from_backtest(self, db_path: str = None) -> List[Dict]:
```

這個方法直接用 SQL 從 `trade_records` 聚合（不依賴 .htm 檔案），做以下分析：

### Pattern Detectors（每個產出 0-N 條 pattern）：

**A. strategy_ranking** — 各策略表現排名
- GROUP BY strategy → avg_pnl, win_rate, profit_factor, sample_size
- 產出：每個 strategy 一條 pattern（profitable 或 unprofitable）
- 對應手動：BATCH-001 的策略排名

**B. direction_bias** — BUY-only vs BOTH
- GROUP BY strategy, direction_filter（從 tags 提取）
- 比較同策略 BUY vs BOTH 的 avg_pnl 差異
- 顯著差異（>5%）→ 產出 pattern
- 對應手動：BATCH-001 方向分析

**C. symbol_fit** — 策略×商品適配性
- GROUP BY strategy, symbol
- 找出同策略在不同商品的表現差異
- 對應手動：FX-001（IM 是 EURUSD 唯一正報酬）、FX-002（VB RR 差距）

**D. mean_reversion_analysis** — MR 特殊分析
- MR 策略按 direction + params 分組
- 找出 profitable vs unprofitable variants
- 對應手動：MR-001（MR BUY-only 在牛市不可行，但特定參數例外）

**E. top_variants** — 最佳參數組合
- 排序所有 variants by pnl（n≥10 篩選）
- Top 5 + Bottom 5 作為 patterns
- 對應手動：BATCH-001 Top 5

每條 pattern 格式：
```python
{
    'pattern_id': 'AUTO-{TYPE}-{N:03d}',  # e.g. AUTO-RANK-001
    'description': '具體描述，含數字',
    'confidence': 0.0-1.0,  # 基於 sample_size 和 consistency
    'sample_size': int,
    'date_range': '2024-01-02 to 2026-02-25',
    'strategy': str or None,
    'symbol': str or None,
    'source': 'backtest_auto',
    'discovered_at': now(),
}
```

Confidence 計算規則：
- n < 10: 0.3 (low)
- n 10-50: 0.5 (medium)
- n 50-200: 0.7 (high)
- n > 200: 0.85 (very high)
- Consistency bonus: 如果 >80% variants 方向一致，+0.1

## Step 3: server.py — 加 API endpoint

`POST /reflect/discover_patterns` — 觸發 pattern discovery，回傳結果
`GET /patterns` — 查詢已發現的 patterns

## Step 4: 驗證腳本

新增 `scripts/validate_l2_patterns.py`：
- 從 DB 讀出所有 `source='backtest_auto'` 的 patterns
- 比對手動的 5 條（MR-001, MR-002, FX-001, FX-002, BATCH-001）
- 輸出對照表：手動 ID | 自動 ID | 是否 match | 差異說明

匹配邏輯：
- MR-001 → 找 strategy=MeanReversion + direction bias patterns
- MR-002 → 找 MR + lot sizing / ATR 相關（可能無法自動發現，因為 lot size 資訊在原始資料中）
- FX-001 → 找 symbol=EURUSD + strategy comparison
- FX-002 → 找 strategy=VolBreakout + symbol comparison（RR）
- BATCH-001 → 找 strategy ranking patterns

## Step 5: 跑完後 commit + 回報

## 修改的檔案
1. `src/tradememory/db.py` — 加 patterns table + 3 methods
2. `src/tradememory/reflection.py` — 加 discover_patterns_from_backtest()
3. `src/tradememory/server.py` — 加 2 endpoints
4. `scripts/validate_l2_patterns.py` — 新檔案
5. `tests/test_patterns.py` — 新檔案，測 patterns CRUD + discovery

## 不動的
- `parse_batch_results.py` — 保留作為獨立分析工具，不刪除
- `backtest_importer.py` — 不動
- `mcp_server.py` — 這期不加 MCP tool（先驗證 DB 層）
