# Task 2 Rules: Scaffold Vite + React

> 這是基礎建設 task，規則較少。重點是不要引入未來會違規的結構。

## 必須遵守的規則

### R1: 目錄結構先對
```
dashboard/
  src/
    api/          ← hooks.ts, client.ts, types.ts（Task 9 建）
    components/
      charts/     ← .tsx + .web.tsx 分離（Task 10+ 建）
      cards/
      layout/
      ui/
    pages/
    theme/
    mock/
    hooks/
    utils/
```

### R2: .gitignore 要完整
dashboard/node_modules/ 和 dashboard/dist/ 都要加入 root .gitignore。

### R3: vite.config.ts proxy 設定
開發時 /dashboard/* 請求 proxy 到 FastAPI backend (localhost:8000)。

## 完成前 Checklist

- [ ] npm run dev 能啟動
- [ ] npm run build 能產出 dist/
- [ ] node_modules 和 dist 在 .gitignore 裡
- [ ] vite.config.ts 有 proxy 設定
