# Task 1 Rules: Docker + PostgreSQL + Alembic

> 開始前讀 ARCHITECTURE_RULES.md 第 2 節（Database 規則）+ 第 8 節（命名規則）

## 必須遵守的規則

### R1: 絕對不用 raw CREATE TABLE
所有 schema 用 Alembic migration，不用 `conn.execute("CREATE TABLE ...")`。

### R2: SQLAlchemy 2.0 async
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10)
async_session = async_sessionmaker(engine, expire_on_commit=False)
```

### R3: timestamp 用 TIMESTAMPTZ
```python
timestamp = Column(DateTime(timezone=True), server_default=func.now())
```

### R4: JSONB 取代 JSON-in-TEXT
舊 SQLite 用 TEXT 存 JSON 是因為限制。新 PostgreSQL code 用原生 JSONB：
```python
context_json = Column(JSONB, nullable=False, default=dict)
```

### R5: Model 命名
```python
class TradeRecordModel(Base):       # PascalCase + Model suffix
    __tablename__ = "trade_records"
```

## 完成前 Checklist

- [ ] 沒有 raw SQL 字串（全用 SQLAlchemy ORM）
- [ ] 沒有 raw CREATE TABLE（全用 Alembic migration）
- [ ] 所有 timestamp 欄位用 TIMESTAMPTZ
- [ ] context_json / history_json 等欄位用 JSONB（不是 TEXT）
- [ ] Model class 命名: `XxxModel`
- [ ] `alembic upgrade head` 能成功執行
- [ ] `docker-compose up -d` 能啟動 PostgreSQL
