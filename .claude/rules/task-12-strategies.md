# Task 12 Rules: Strategies Page

> 同 Task 10/11 規則。開始前讀 ARCHITECTURE_RULES.md 第 4 節

## 必須遵守的規則

### R1: Chart 組件拆分
StrategyHeatmap.tsx + .web.tsx（如果用 chart library）。
AdjustmentTimeline 用 CSS 實作的話不需要 .web.tsx。

### R2: 三個狀態
tab 切換後，每個 section 獨立 loading/error/empty。
切換 tab 時 SWR 自動 revalidate。

### R3: 數字用 monospace
交易列表的金額、R-multiple 用 var(--font-mono)。

### R4: 不用固定寬度
heatmap cell 用 relative sizing，不用 `width: 60px`。

## 完成前 Checklist

- [ ] Tab 切換觸發 data refetch
- [ ] 每個 section 有 loading/error/empty
- [ ] 數字用 monospace font
- [ ] heatmap responsive（或 horizontal scroll on mobile）
- [ ] chart 組件有 .tsx + .web.tsx 分離
