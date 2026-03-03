# FB Post — TradeMemory Protocol v0.3.0

---

🔬 TradeMemory Protocol v0.3.0 — L3 Strategy Adjustments

上週分享了 AI 交易記憶系統，這週最大進展：**系統現在會自己調整策略了。**

之前的流程是：
1. EA 交易 → 記錄到 L1
2. Reflection Engine 分析 → 發現 L2 patterns
3. 然後⋯⋯我手動看 patterns，自己決定要不要調參數

現在 v0.3.0 加了 L3：
1. EA 交易 → L1
2. 反思引擎 → L2 patterns
3. **5 條規則自動產出策略調整 → L3** ← 新的

實際跑一次的結果（10,169 筆回測數據）：
- MeanReversion 平均 PnL -494% → **自動建議停用** ✅
- IntradayMomentum +1690% → **自動建議優先使用** ✅
- MR 在 XAUUSD 牛市 SELL 方向虧更多 → **自動建議限制為 BUY-only** ✅

9 個自動產出的調整，跟我手動分析的結論 **完全一致**。

這就是 tradememory 的核心價值：不是取代你的判斷，是把你的判斷自動化。

技術細節：
- 5 條確定性規則（不用 LLM）
- 需要 n≥50 筆交易才會觸發（防過擬合）
- 調整有生命週期：proposed → approved → applied
- 181 個測試全過
- CI 自動發布到 PyPI

GitHub: https://github.com/mnemox-ai/tradememory-protocol
PyPI: pip install tradememory-protocol

#量化交易 #AI #MCP #開源 #tradememory
