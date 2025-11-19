# Vanna 服务自动启动配置

## 概述

MCP 服务器现在支持在启动时自动启动 Vanna AI 服务。这使得 Text-to-SQL 功能可以无缝集成到 MCP 服务中。

## 配置方法

### 1. 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# 启用 Vanna 服务自动启动
ENABLE_VANNA_SERVICE=true

# Vanna 服务 URL（默认: http://localhost:5000）
VANNA_SERVICE_URL=http://localhost:5000

# Vanna AI 配置
VANNA_CONFIG_TYPE=openai_proxy
PROXY_API_KEY=your-api-key
PROXY_MODEL=your-model-name
PROXY_BASE_URL=your-api-base-url

# 数据库配置（Vanna 服务使用）
POSTGIS_HOST=172.16.12.179
POSTGIS_PORT=15432
POSTGIS_DATABASE=yukon_mcp
POSTGIS_USER=zhangming1
POSTGIS_PASSWORD=Huawei@123
```

### 2. 启用/禁用 Vanna 服务

**启用**:
```bash
ENABLE_VANNA_SERVICE=true
```

**禁用**（默认）:
```bash
ENABLE_VANNA_SERVICE=false
```
或者不设置该环境变量。

## 工作原理

1. **启动检查**: MCP 服务器启动时会检查 `ENABLE_VANNA_SERVICE` 环境变量
2. **服务探测**: 检查 Vanna 服务是否已经在运行（通过健康检查端点）
3. **自动启动**: 如果服务未运行，则自动启动 `vanna_service.py`
4. **健康检查**: 等待最多 30 秒确认服务成功启动
5. **优雅关闭**: MCP 服务器关闭时会自动停止 Vanna 服务

## 使用流程

### 正常启动流程

```bash
# 1. 配置环境变量
export ENABLE_VANNA_SERVICE=true

# 2. 启动 MCP 服务器
python src/server.py --stdio
```

**日志输出示例**:
```
2025-11-19 11:15:00 - INFO - 启动 PostGIS MCP 服务器...
2025-11-19 11:15:00 - INFO - 正在启动Vanna服务...
2025-11-19 11:15:05 - INFO - ✓ Vanna服务启动成功 (耗时 5秒)
2025-11-19 11:15:05 - INFO - 正在初始化数据库连接...
2025-11-19 11:15:05 - INFO - 数据库连接成功!
```

### 服务已运行情况

如果 Vanna 服务已经在运行：

```
2025-11-19 11:15:00 - INFO - 启动 PostGIS MCP 服务器...
2025-11-19 11:15:00 - INFO - 检测到Vanna服务已运行
2025-11-19 11:15:00 - INFO - 正在初始化数据库连接...
```

### 服务未启用情况

如果 `ENABLE_VANNA_SERVICE=false` 或未设置：

```
2025-11-19 11:15:00 - INFO - 启动 PostGIS MCP 服务器...
2025-11-19 11:15:00 - INFO - Vanna服务未启用(设置 ENABLE_VANNA_SERVICE=true 启用)
2025-11-19 11:15:00 - INFO - 正在初始化数据库连接...
```

## 故障排除

### 问题 1: Vanna 服务启动失败

**可能原因**:
- 端口 5000 已被占用
- 缺少必要的依赖包
- 数据库连接配置错误

**解决方法**:
1. 检查端口占用: `netstat -ano | findstr :5000`
2. 确认依赖安装: `pip install -r requirements.txt`
3. 验证数据库配置

### 问题 2: 服务启动超时

**可能原因**:
- 首次启动需要初始化 ChromaDB
- 数据库连接慢

**解决方法**:
- 等待更长时间（默认超时 30 秒）
- 检查网络连接
- 查看 Vanna 服务日志

### 问题 3: MCP 服务器无法连接 Vanna 服务

**可能原因**:
- Vanna 服务 URL 配置错误
- 防火墙阻止连接

**解决方法**:
1. 验证 URL: `curl http://localhost:5000/health`
2. 检查防火墙设置
3. 确认 `VANNA_SERVICE_URL` 环境变量正确

## 手动管理 Vanna 服务

### 手动启动

```bash
python src/vanna_server/vanna_service.py
```

### 手动停止

按 `Ctrl+C` 或使用进程管理器终止进程。

### 独立运行

Vanna 服务可以独立于 MCP 服务器运行：

```bash
# 终端 1: 启动 Vanna 服务
python src/vanna_server/vanna_service.py

# 终端 2: 启动 MCP 服务器（Vanna 服务检测为已运行）
python src/server.py --stdio
```

## 相关工具

启用 Vanna 服务后，以下 MCP 工具可用：

- `vanna_init`: 初始化 Vanna 模型
- `vanna_train_ddl`: 训练数据库结构
- `vanna_train_documentation`: 训练业务文档
- `vanna_train_sql_example`: 训练 SQL 示例
- `vanna_generate_sql`: 生成 SQL 查询
- `vanna_ask`: 完整问答流程

详细使用方法请参考 [VANNA_USAGE.md](./VANNA_USAGE.md)

## 注意事项

1. **性能**: Vanna 服务启动需要几秒钟时间，特别是首次启动
2. **资源**: Vanna 服务会占用额外的内存和 CPU 资源
3. **安全**: 确保 API 密钥安全存储在 `.env` 文件中
4. **日志**: Vanna 服务日志输出到独立的进程，可通过进程管理器查看

## 更多信息

- [Vanna 服务 API 文档](./VANNA_SERVICE_USAGE.md)
- [Text-to-SQL 使用指南](./TEXT_TO_SQL.md)
- [Vanna AI 官方文档](https://vanna.ai/docs/)