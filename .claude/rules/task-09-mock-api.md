# Task 9 Rules: Mock Data + API Layer + Router

> 開始前讀 ARCHITECTURE_RULES.md 第 4.2 節（不在 component 裡直接 fetch）

## 必須遵守的規則

### R1: 用 SWR hook，不在 component 裡直接 fetch
```tsx
// ❌
function Overview() {
  const [data, setData] = useState(null);
  useEffect(() => { fetch('/dashboard/overview').then(...) }, []);
}

// ✅
export function useOverview() {
  return useSWR<OverviewResponse>('/dashboard/overview', fetcher);
}
```

### R2: Mock 切換在 hooks 層，不在 component 層
component 不需要知道資料來自 API 還是 mock。切換邏輯在 hooks.ts 裡。

### R3: TypeScript types 必須跟後端 Pydantic model 一致
types.ts 的 interface 名稱和欄位要跟 schemas.py 的 Pydantic model 完全對應。

### R4: Mock 數據要漂亮
mock JSON 用於截圖和 demo，數據要 realistic 且 tell a story（equity 上升、memory 成長）。

## 完成前 Checklist

- [ ] 所有 data fetching 在 hooks.ts（不在 component 裡）
- [ ] VITE_USE_MOCK=true 時能切換到 mock
- [ ] types.ts interface 跟後端 Pydantic model 一致
- [ ] mock JSON 數據 realistic（不是隨機數）
- [ ] 5 個 page component 都有 placeholder
