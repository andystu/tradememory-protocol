# Task 15 Rules: Animations + Tooltips + CSV Export

> 開始前讀 ARCHITECTURE_RULES.md 第 4.4 節（CSS 規則）

## 必須遵守的規則

### R1: 動畫用 CSS transition，不用 JS animation library
```css
.reveal { opacity: 0; transform: translateY(20px); transition: all 0.5s ease-out; }
.reveal.visible { opacity: 1; transform: translateY(0); }
```
IntersectionObserver 觸發 class 切換就好。

### R2: Tooltip 用 CSS variable 配色
Tooltip 背景 var(--bg-card)，邊框 var(--cyan)，文字 var(--text)。

### R3: CSV export 是 utility function，不綁 component
```ts
// utils/csvExport.ts — pure function
export function downloadCSV(data: Record<string,any>[], filename: string): void
```

### R4: 不用 inline style
tooltip 和 animation 都走 CSS Module。

## 完成前 Checklist

- [ ] scroll-reveal 用 IntersectionObserver + CSS（不是 JS library）
- [ ] tooltip 配色走 CSS variable
- [ ] CSV export 是 pure utility function
- [ ] 沒有新增 inline style
- [ ] 動畫不影響頁面效能（GPU accelerated transform/opacity）
