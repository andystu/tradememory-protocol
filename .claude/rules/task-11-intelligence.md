# Task 11 Rules: Intelligence Page

> 同 Task 10 規則。開始前讀 ARCHITECTURE_RULES.md 第 4 節

## 必須遵守的規則

### R1: 每個 chart 組件拆 .tsx + .web.tsx
MemoryGrowth、OWMScoreTrend、ConfidenceCalibration、ResonanceGauge — 全部拆。
BayesianBeliefs 是 card 組件，不需要拆（不用 chart library）。

### R2: 每個 section 有三個狀態
Intelligence 頁有 5 個 section，每個都要獨立處理 loading/error/empty。
不要因為一個 section 沒資料就整頁空白。

### R3: CSS responsive
2-column grid desktop → single column mobile。
```css
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
```

### R4: 不用 inline style
顏色、大小全走 CSS variable 或 CSS Module。

## 完成前 Checklist

- [ ] 4 個 chart 組件有 .tsx + .web.tsx 分離
- [ ] 每個 section 獨立處理 loading/error/empty
- [ ] responsive layout（desktop 2 col → mobile 1 col）
- [ ] 沒有 inline style（除了動態 CSS variable）
- [ ] 沒有固定 px 寬度
