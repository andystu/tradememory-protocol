# Task 13 Rules: Reflections + Dreams Pages

> 同前端規則。開始前讀 ARCHITECTURE_RULES.md 第 4 節

## 必須遵守的規則

### R1: 三個狀態
兩個頁面都要 loading/error/empty state。
Empty state 要有引導文字（告訴使用者怎麼產生資料）。

### R2: DreamComparison chart 拆分
DreamComparison.tsx + DreamComparison.web.tsx（Recharts 實作）。

### R3: Markdown 渲染不用 dangerouslySetInnerHTML
用 react-markdown library，不要手動塞 HTML。

### R4: Empty state 要有意義
```tsx
// Reflections empty:
"No reflections yet. Run daily_review.py to generate AI-powered trade reviews."

// Dreams empty:
"Trade Dreaming Phase 2 is planned. This page will show A/B test results."
```

## 完成前 Checklist

- [ ] 兩個頁面都有 loading/error/empty
- [ ] DreamComparison 有 .tsx + .web.tsx 分離
- [ ] Markdown 用 react-markdown（不是 dangerouslySetInnerHTML）
- [ ] Empty state 有引導文字
- [ ] grade badge 顏色用 CSS variable
