# Vanna AI集成使用指南

本文档介绍如何使用基于Vanna AI的自然语言到SQL转换功能。

## 概述

Vanna AI是一个开源的RAG(Retrieval-Augmented Generation)框架,通过训练学习数据库结构和查询模式,提供准确的SQL生成能力。本项目已集成Vanna并针对PostGIS进行了优化。

## 核心特性

1. **RAG增强**: 基于训练数据的检索增强生成
2. **PostGIS优化**: 专门支持PostGIS空间扩展
3. **训练数据持久化**: 训练成果自动保存到文件
4. **用户确认机制**: 所有训练和SQL执行都需要用户确认
5. **灵活训练**: 支持DDL、文档、SQL示例多种训练方式

## 使用流程

### 1. 初始化Vanna模型

```python
# 初始化模型(需要Vanna API密钥)
result = await vanna_init(
    model_name="postgis-model",
    api_key="your_vanna_api_key"  # 或设置环境变量VANNA_API_KEY
)
```

### 2. 训练模型

#### 方式1: DDL训练(推荐首先执行)

```python
# 预览DDL训练
result = await vanna_train_ddl(schema="public")
# 返回: {"session_id": "training_1", ...}

# 确认并执行训练
await vanna_confirm_training(session_id="training_1")
```

#### 方式2: 文档训练

```python
# 预览文档训练
result = await vanna_train_documentation(
    documentation="buildings表存储建筑物信息,height字段表示建筑高度(米)"
)

# 确认训练
await vanna_confirm_training(session_id=result["session_id"])
```

#### 方式3: SQL示例训练

```python
# 预览SQL示例训练
result = await vanna_train_sql_example(
    question="查询所有高度超过100米的建筑",
    sql="SELECT * FROM buildings WHERE height > 100"
)

# 确认训练
await vanna_confirm_training(session_id=result["session_id"])
```

### 3. 生成SQL查询

```python
# 生成SQL(带预览)
result = await vanna_generate_sql(
    question="统计每个城市的建筑数量,按数量降序排列"
)

# 返回:
# {
#   "success": True,
#   "generated_sql": "SELECT city, COUNT(*) as count FROM buildings GROUP BY city ORDER BY count DESC",
#   "session_id": "training_2",
#   ...
# }
```

### 4. 执行SQL

```python
# 检查生成的SQL后执行
result = await execute_sql(
    sql="SELECT city, COUNT(*) as count FROM buildings GROUP BY city ORDER BY count DESC",
    confirmed=True  # 必须设置为True
)
```

## 完整工作流程示例

```python
# 步骤1: 初始化
await vanna_init(api_key="your_key")

# 步骤2: 训练数据库结构
ddl_result = await vanna_train_ddl(schema="public")
await vanna_confirm_training(session_id=ddl_result["session_id"])

# 步骤3: 添加业务知识
doc_result = await vanna_train_documentation(
    documentation="""
    buildings表存储建筑物信息:
    - height: 建筑高度(米)
    - area: 建筑面积(平方米)
    - city: 所在城市
    """
)
await vanna_confirm_training(session_id=doc_result["session_id"])

# 步骤4: 添加查询示例
example_result = await vanna_train_sql_example(
    question="查询杭州市的所有高层建筑",
    sql="SELECT * FROM buildings WHERE city='杭州' AND height > 100"
)
await vanna_confirm_training(session_id=example_result["session_id"])

# 步骤5: 生成新的查询
sql_result = await vanna_generate_sql(
    question="统计每个城市超过50米的建筑数量"
)

# 步骤6: 检查并执行
print(f"生成的SQL: {sql_result['generated_sql']}")
data_result = await execute_sql(
    sql=sql_result['generated_sql'],
    confirmed=True
)
```

## 管理训练数据

### 查看训练数据

```python
# 获取所有训练数据
result = await vanna_get_training_data()
print(f"共有 {result['count']} 条训练数据")
```

### 删除训练数据

```python
# 删除指定的训练数据
await vanna_remove_training_data(id="training_data_id")
```

### 取消训练会话

```python
# 如果不想执行某个训练,可以取消
await vanna_cancel_training(session_id="training_1")
```

## 训练数据持久化

所有训练数据会自动保存到`vanna_training_data.json`文件中,包括:

- DDL结构信息
- 业务文档
- SQL示例

下次启动时会自动加载这些数据。

## 最佳实践

1. **先训练DDL**: 首先使用`vanna_train_ddl`训练数据库结构
2. **添加业务知识**: 使用`vanna_train_documentation`添加字段含义等业务信息
3. **提供示例**: 通过`vanna_train_sql_example`提供典型查询示例
4. **检查SQL**: 生成的SQL一定要检查后再执行
5. **持续优化**: 成功的查询可以作为新的训练示例

## 注意事项

1. 需要Vanna API密钥,可在https://vanna.ai注册获取
2. 所有训练操作都需要用户确认才会执行
3. 生成的SQL需要使用`execute_sql(confirmed=True)`执行
4. 训练数据保存在本地文件中
5. 模型质量取决于训练数据的质量和数量

## 故障排除

### 问题: "Vanna AI未安装"

```bash
pip install vanna
```

### 问题: "未提供Vanna API密钥"

设置环境变量:
```bash
export VANNA_API_KEY="your_key"
```

或在调用时提供:
```python
await vanna_init(api_key="your_key")
```

### 问题: 生成的SQL不准确

- 增加更多训练数据
- 提供更多SQL示例
- 添加详细的文档说明
- 使用`allow_llm_to_see_data=True`提高准确性

## 工具列表

| 工具名称 | 功能 | 需要确认 |
|---------|------|---------|
| `vanna_init` | 初始化模型 | 否 |
| `vanna_train_ddl` | DDL训练预览 | 是 |
| `vanna_train_documentation` | 文档训练预览 | 是 |
| `vanna_train_sql_example` | SQL示例训练预览 | 是 |
| `vanna_confirm_training` | 确认并执行训练 | - |
| `vanna_cancel_training` | 取消训练会话 | - |
| `vanna_generate_sql` | 生成SQL | 否 |
| `execute_sql` | 执行SQL | 是 |
| `vanna_get_training_data` | 获取训练数据 | 否 |
| `vanna_remove_training_data` | 删除训练数据 | 否 |