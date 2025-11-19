# Vanna AI REST API 服务使用指南

## 架构概述

基于 REST API 的 Vanna AI 服务架构：

```
┌─────────────────────────────────────────────────────────┐
│         MCP 工具 (vanna_mcp_adapter.py)                 │
│    通过异步 HTTP 调用 REST API                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│    Flask REST API 服务 (vanna_service.py)               │
│    - 训练数据管理                                        │
│    - SQL 生成和执行                                      │
│    - 本地 ChromaDB 存储                                  │
└────────────┬──────────────────────────────────┬─────────┘
             │                                  │
             ▼                                  ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│  训练脚本                 │    │  数据库连接              │
│(vanna_postgis.py)        │    │(GaussDB+Yukon)      │
│- DDL 训练                │    │                          │
│- 文档训练                │    │                          │
│- SQL 示例训练            │    │                          │
└──────────────────────────┘    └──────────────────────────┘
             │                                  │
             └──────────────┬───────────────────┘
                            ▼
              ┌─────────────────────────┐
              │   yukon_db (本地存储)   │
              │  - ChromaDB 向量库      │
              │  - 训练数据             │
              └─────────────────────────┘
```

## 文件说明

| 文件 | 功能 | 说明 |
|------|------|------|
| `vanna_postgis.py` | 训练脚本 | 初始化 Vanna 模型，执行 DDL/文档/SQL 示例训练 |
| `vanna_service.py` | Flask 服务 | 提供 REST API 接口，管理训练会话和数据 |
| `vanna_mcp_adapter.py` | MCP 适配器 | 异步调用 REST API，提供 MCP 工具接口 |
| `vanna_postgis_trainer.py` | 训练器包装 | 包装器函数，为 MCP 工具提供接口 |

## 使用流程

### 1. 启动 REST API 服务

```bash
# 进入项目目录
cd e:/ai/yukon_mcp_service

# 启动 Vanna 服务（默认监听 http://localhost:5000）
python -m src.vanna_server.vanna_service
```

服务启动时会自动初始化，输出类似：

```
============================================================
Vanna 服务启动中...
============================================================

初始化结果: Vanna 初始化成功,训练数据目录: E:\ai\yukon_mcp_service\yukon_db

服务已启动,可用接口:
  - GET  /health                              - 健康检查
  - POST /api/vanna/init                      - 初始化Vanna
  - POST /api/vanna/train/ddl/preview         - 预览DDL训练
  - POST /api/vanna/train/documentation/preview - 预览文档训练
  - POST /api/vanna/train/sql/preview         - 预览SQL示例训练
  - POST /api/vanna/train/confirm             - 确认并执行训练
  - POST /api/vanna/train/cancel              - 取消训练会话
  - POST /api/vanna/generate_sql              - 生成SQL
  - POST /api/vanna/execute_sql               - 执行SQL
  - GET  /api/vanna/training_data             - 获取训练数据
  - DELETE /api/vanna/training_data/<id>      - 删除训练数据

============================================================
```

### 2. 运行训练脚本（可选）

如果需要初始化训练数据，可以运行训练脚本：

```bash
python -m src.vanna_server.vanna_postgis
```

### 3. 训练模型（三步法）

#### 第一步：预览训练数据

**预览 DDL 训练：**
```bash
curl -X POST http://localhost:5000/api/vanna/train/ddl/preview \
  -H "Content-Type: application/json" \
  -d '{"schema": "public"}'
```

**预览文档训练：**
```bash
curl -X POST http://localhost:5000/api/vanna/train/documentation/preview \
  -H "Content-Type: application/json" \
  -d '{"documentation": "buildings表存储建筑物信息，包括高度、面积等"}'
```

**预览 SQL 示例训练：**
```bash
curl -X POST http://localhost:5000/api/vanna/train/sql/preview \
  -H "Content-Type: application/json" \
  -d '{
    "question": "查询所有高度超过100米的建筑",
    "sql": "SELECT * FROM buildings WHERE height > 100"
  }'
```

响应示例：

```json
{
  "success": true,
  "session_id": "training_a1b2c3d4",
  "training_type": "sql_example",
  "preview": {
    "question": "查询所有高度超过100米的建筑",
    "sql": "SELECT * FROM buildings WHERE height > 100"
  },
  "message": "请检查SQL示例,使用 /api/vanna/train/confirm 确认"
}
```

#### 第二步：确认训练

```bash
curl -X POST http://localhost:5000/api/vanna/train/confirm \
  -H "Content-Type: application/json" \
  -d '{"session_id": "training_a1b2c3d4"}'
```

#### 第三步：取消训练（如需要）

```bash
curl -X POST http://localhost:5000/api/vanna/train/cancel \
  -H "Content-Type: application/json" \
  -d '{"session_id": "training_a1b2c3d4"}'
```

### 4. 生成和执行 SQL

#### 生成 SQL（预览）

```bash
curl -X POST http://localhost:5000/api/vanna/generate_sql \
  -H "Content-Type: application/json" \
  -d '{
    "question": "查询距离坐标120.5,30.2 500米范围内的城市",
    "allow_llm_to_see_data": false
  }'
```

#### 执行 SQL

```bash
curl -X POST http://localhost:5000/api/vanna/execute_sql \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT c.name FROM cities c WHERE ST_DWithin(c.geom::geography, '\''POINT(120.5 30.2)'\''::geography, 500)",
    "confirmed": true
  }'
```

### 5. 管理训练数据

#### 获取所有训练数据

```bash
curl -X GET http://localhost:5000/api/vanna/training_data
```

#### 删除特定训练数据

```bash
curl -X DELETE http://localhost:5000/api/vanna/training_data/{data_id}
```

## 通过 MCP 工具使用

MCP 工具已自动集成到 `src/server.py`，通过以下 MCP 工具调用：

- `vanna_init()` - 初始化 Vanna 模型
- `vanna_train_ddl()` - 预览 DDL 训练
- `vanna_train_documentation()` - 预览文档训练
- `vanna_train_sql_example()` - 预览 SQL 示例训练
- `vanna_confirm_training()` - 确认并执行训练
- `vanna_cancel_training()` - 取消训练会话
- `vanna_generate_sql()` - 生成 SQL
- `execute_sql()` - 执行 SQL（需要 confirmed=True）
- `vanna_get_training_data()` - 获取训练数据
- `vanna_remove_training_data()` - 删除训练数据

## 环境变量配置

在 `.env` 文件中配置：

```env
# LLM 配置
PROXY_API_KEY=your-api-key
PROXY_MODEL=gpt-3.5-turbo
PROXY_BASE_URL=https://fast.catsapi.com/v1

# 或使用 OpenAI 官方
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4-turbo

# 数据库配置
POSTGIS_HOST=172.16.12.179
POSTGIS_PORT=15432
POSTGIS_DATABASE=yukon_mcp
POSTGIS_USER=zhangming1
POSTGIS_PASSWORD=Huawei@123

# Vanna 服务
VANNA_SERVICE_URL=http://localhost:5000
```

## 数据存储

- **本地 ChromaDB**: `./yukon_db/` - 所有训练数据保存在这个目录
- **格式**: 向量库格式，自动管理
- **持久化**: 数据在服务重启后仍然保存

## 常见问题

### Q: 如何更改 Vanna 服务端口？

修改 `vanna_service.py` 最后一行：

```python
app.run(host='0.0.0.0', port=8000, debug=False)  # 改为 8000
```

同时更新 `.env` 中的 `VANNA_SERVICE_URL`。

### Q: 如何重新初始化训练数据？

删除 `yukon_db` 目录并重启服务：

```bash
rm -rf ./yukon_db
python -m src.vanna_server.vanna_service
```

### Q: 如何检查服务是否正常？

```bash
curl http://localhost:5000/health
```

### Q: MCP 工具找不到 REST API 服务？

检查：
1. REST API 服务是否已启动：`python -m src.vanna_server.vanna_service`
2. `.env` 中 `VANNA_SERVICE_URL` 是否正确
3. 网络连接是否正常

## 总结

| 场景 | 流程 |
|------|------|
| 独立训练脚本 | 直接运行 `vanna_postgis.py` |
| Flask 服务 | 启动 `vanna_service.py`，通过 REST API 调用 |
| MCP 工具集成 | 通过 `vanna_mcp_adapter.py` 调用 REST API |
| 完整工作流 | REST 服务 + MCP 适配器 + MCP Server |

## 架构优势

✅ **模块化**: 训练、服务、工具分离  
✅ **本地存储**: 所有数据保存在本地 ChromaDB  
✅ **REST API**: 易于集成和扩展  
✅ **异步支持**: MCP 工具支持异步操作  
✅ **安全性**: SQL 执行需要显式确认  
✅ **灵活配置**: 支持多种 LLM 和 API 端点