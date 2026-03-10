# Task 10 Rules: Overview Page

> 開始前讀 ARCHITECTURE_RULES.md 第 4 節（Frontend 規則 全部）

## 必須遵守的規則

### R1: Chart 組件必須拆 .tsx + .web.tsx
```
EquityCurveChart.tsx       ← 業務邏輯（data transform, props interface）
EquityCurveChart.web.tsx   ← 渲染層（TradingView Lightweight Charts）
```
業務邏輯層不 import 任何 chart library。渲染層才 import。

### R2: 三個狀態都要處理
```tsx
function Overview() {
  const { data, error, isLoading } = useOverview();
  if (isLoading) return <OverviewSkeleton />;           // 1. Loading
  if (error) return <ErrorCard onRetry={mutate} />;     // 2. Error
  if (!data) return <EmptyState title="No trades" />;   // 3. Empty
  return <OverviewContent data={data} />;
}
```

### R3: 不用固定像素寬度
```css
/* ❌ */ .metricRow { width: 1200px; }
/* ✅ */ .metricRow { width: 100%; max-width: 1200px; }
```

### R4: 用 SWR hook（不直接 fetch）
```tsx
// ❌ useEffect + fetch
// ✅ const { data } = useOverview();
```

## 完成前 Checklist

- [ ] EquityCurveChart 有 .tsx + .web.tsx 分離
- [ ] Loading skeleton 狀態
- [ ] Error state + retry 按鈕
- [ ] Empty state（沒 trade 時引導文字）
- [ ] CSS 沒有固定 px 寬度
- [ ] 資料用 SWR hook 取得
