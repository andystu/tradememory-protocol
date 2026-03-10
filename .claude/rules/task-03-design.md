# Task 3 Rules: Mnemox Design System + Layout

> 開始前讀 ARCHITECTURE_RULES.md 第 4.4 節（CSS 規則）

## 必須遵守的規則

### R1: 不用固定像素寬度
```css
/* ❌ */ .card { width: 350px; }
/* ✅ */ .card { width: 100%; max-width: 400px; }
```

### R2: CSS Module，不用 inline style
```tsx
/* ❌ */ <div style={{ color: 'red', fontSize: '14px' }}>
/* ✅ */ <div className={styles.card} style={{ '--accent': color }}>
```
只有動態計算的值才用 inline style（且用 CSS variable）。

### R3: 所有顏色走 CSS variable
不要在 component 裡 hardcode hex color。全部用 var(--cyan) 等 design token。

### R4: Nav 用 react-router-dom NavLink
不要用 <a> 或自己寫 router。用 NavLink + isActive 做 active state。

## 完成前 Checklist

- [ ] CSS 沒有固定 px 寬度（width: Npx 禁止）
- [ ] 沒有 inline style（除了動態 CSS variable）
- [ ] 所有顏色用 CSS variable
- [ ] Nav 用 NavLink
- [ ] dark mode only（沒有 light mode 切換）
