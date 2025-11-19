# PostGIS MCP Server

基于 fastMCP 框架的 PostGIS 工具 MCP 服务器实现。

## 🌟 新功能: Text-to-SQL

现在支持使用自然语言查询PostGIS数据库！无需编写复杂的SQL语句，只需用中文或英文描述您的查询需求。

**示例：**
- "查询表:buildings 坐标120.5,30.2 附近500米的建筑"
- "为表:roads创建100米缓冲区"
- "计算表:parks的面积"

详细信息请查看 [Text-to-SQL文档](docs/TEXT_TO_SQL.md)

## 项目简介

本项目使用 fastMCP 框架封装 PostGIS 地理空间数据库工具,通过 MCP (Model Context Protocol) 协议提供标准化的工具接口。

## 项目结构

```
yukon_mcp_service/
├── src/
│   ├── __init__.py           # 包初始化
│   ├── server.py             # MCP 服务器主入口
│   ├── tools/                # 工具模块
│   │   ├── __init__.py
│   │   ├── spatial_query.py  # 空间查询工具
│   │   ├── geometry.py       # 几何操作工具
│   │   └── analysis.py       # 空间分析工具
│   └── config/
│       ├── __init__.py
│       └── database.py       # 数据库配置
├── tests/                    # 测试文件
│   ├── __init__.py
│   └── test_tools.py
├── pyproject.toml            # 项目配置
├── requirements.txt          # 依赖列表
└── README.md                 # 项目说明
```

## 功能特性

### 空间查询工具（3个）
- `query_nearby` - 根据坐标查询附近的地理要素
- `query_bbox` - 空间范围查询
- `query_attribute` - 根据属性查询要素

### 几何操作工具（5个）
- `buffer_geometry` - 创建几何缓冲区
- `get_area` - 计算几何面积
- `get_length` - 计算几何长度
- `transform_coords` - 坐标系统转换
- `simplify_geom` - 简化几何对象

### 空间分析工具（5个）
- `measure_distance` - 计算两个几何对象之间的距离
- `test_intersection` - 检查几何对象相交关系
- `test_containment` - 检查几何对象包含关系
- `union_geoms` - 合并多个几何对象
- `get_centroid` - 计算几何对象质心

### 数据库管理工具（9个）
- `postgis_version` - 获取 PostGIS 版本信息
- `list_extensions` - 列出已安装的数据库扩展
- `discover_spatial_tables` - 发现包含空间字段的表
- `table_info` - 获取表的详细空间信息
- `create_index` - 为空间列创建 GIST 索引
- `analyze` - 分析表以更新统计信息
- `vacuum` - 清理表以回收空间
- `spatial_extent` - 获取表的空间范围
- `validate_geometries` - 检查几何对象有效性

### 高级空间分析工具（8个）
- `join_spatial` - 执行空间连接操作
- `find_nearest` - 查找最近的K个邻居
- `cluster_spatial` - 使用 DBSCAN 进行空间聚类
- `compute_convex_hull` - 计算凸包
- `generate_voronoi` - 生成 Voronoi 多边形
- `interpolate_line` - 沿线段插值点
- `snap_geometry` - 将几何对象捕捉到网格
- `split_line` - 使用点分割线段

### Text-to-SQL 工具（2个）
- `nl_to_sql` - 将自然语言转换为PostGIS SQL语句
- `execute_sql` - 安全执行SQL查询（需用户确认）

**共计 32 个专业 PostGIS 工具**

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

在使用前需要配置 PostGIS 数据库连接信息:

```python
# src/config/database.py
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "your_database",
    "user": "your_user",
    "password": "your_password"
}
```

## 运行服务

```bash
python -m src.server
```

## 使用示例

通过 MCP 协议调用工具:

```python
# 查询指定坐标附近的要素
result = await mcp_client.call_tool(
    "query_nearby",
    {
        "longitude": 120.123,
        "latitude": 30.456,
        "radius": 1000
    }
)
```

## 开发指南

### 添加新工具

1. 在 `src/tools/` 目录下创建新的工具模块
2. 使用 `@mcp.tool()` 装饰器定义工具函数
3. 在 `server.py` 中注册新工具

示例:

```python
@mcp.tool()
async def my_spatial_tool(param1: str, param2: float) -> dict:
    """工具描述"""
    # 实现逻辑
    return {"result": "data"}
```

## 技术栈

- Python 3.8+
- fastMCP
- PostGIS
- psycopg2
- asyncio

## 许可证

MIT License