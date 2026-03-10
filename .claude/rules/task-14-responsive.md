# Task 14 Rules: Responsive + Loading + Error States

> 開始前讀 ARCHITECTURE_RULES.md 第 4.3 節 + 第 4.4 節

## 必須遵守的規則

### R1: 三個斷點
```css
@media (max-width: 640px)  { /* mobile */ }
@media (max-width: 1024px) { /* tablet */ }
@media (min-width: 1025px) { /* desktop */ }
```

### R2: Loading 用 skeleton，不是 spinner
Skeleton 用 shimmer animation（linear-gradient sweep）。

### R3: Error state 有 retry
```tsx
<ErrorState message="Failed to load" onRetry={() => mutate()} />
```

### R4: 不用固定寬度
全部審查一遍，確認沒有 `width: Npx`。

## 完成前 Checklist

- [ ] Nav 有 mobile hamburger menu
- [ ] MetricCard 有 responsive grid
- [ ] 所有 chart container full width on mobile
- [ ] Skeleton 有 shimmer animation
- [ ] Error state 有 retry 按鈕
- [ ] Empty state 有引導文字
- [ ] 沒有固定 px 寬度
