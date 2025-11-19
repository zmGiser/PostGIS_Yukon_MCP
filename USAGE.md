# 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

复制 `.env.example` 为 `.env` 并配置数据库连接:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
POSTGIS_HOST=localhost
POSTGIS_PORT=5432
POSTGIS_DATABASE=your_database
POSTGIS_USER=your_username
POSTGIS_PASSWORD=your_password
```

### 3. 启动服务

```bash
python -m src.server
```

或使用命令行工具:

```bash
yukon-mcp
```

## MCP 工具使用示例

### 空间查询工具

#### 查询附近要素

```python
result = await mcp.call_tool(
    "query_nearby",
    {
        "longitude": 120.123,
        "latitude": 30.456,
        "radius": 1000,
        "table_name": "poi",
        "geometry_column": "geom",
        "limit": 10
    }
)
```

#### 边界框查询

```python
result = await mcp.call_tool(
    "query_bbox",
    {
        "min_x": 120.0,
        "min_y": 30.0,
        "max_x": 120.5,
        "max_y": 30.5,
        "table_name": "boundaries",
        "limit": 50
    }
)
```

#### 属性查询

```python
result = await mcp.call_tool(
    "query_attribute",
    {
        "table_name": "cities",
        "attribute_name": "name",
        "attribute_value": "杭州",
        "limit": 10
    }
)
```

### 几何操作工具

#### 创建缓冲区

```python
result = await mcp.call_tool(
    "buffer_geometry",
    {
        "geometry_wkt": "POINT(120.0 30.0)",
        "distance": 500,
        "srid": 4326
    }
)
```

#### 计算面积

```python
result = await mcp.call_tool(
    "get_area",
    {
        "geometry_wkt": "POLYGON((120 30, 120.1 30, 120.1 30.1, 120 30.1, 120 30))",
        "srid": 4326
    }
)
```

#### 计算长度

```python
result = await mcp.call_tool(
    "get_length",
    {
        "geometry_wkt": "LINESTRING(120 30, 120.1 30.1)",
        "srid": 4326
    }
)
```

#### 坐标转换

```python
result = await mcp.call_tool(
    "transform_coords",
    {
        "geometry_wkt": "POINT(120.0 30.0)",
        "from_srid": 4326,
        "to_srid": 3857
    }
)
```

#### 简化几何

```python
result = await mcp.call_tool(
    "simplify_geom",
    {
        "geometry_wkt": "LINESTRING(120 30, 120.01 30.01, 120.02 30.02, 120.1 30.1)",
        "tolerance": 0.001,
        "srid": 4326
    }
)
```

### 空间分析工具

#### 计算距离

```python
result = await mcp.call_tool(
    "measure_distance",
    {
        "geom1_wkt": "POINT(120.0 30.0)",
        "geom2_wkt": "POINT(120.1 30.1)",
        "srid": 4326
    }
)
```

#### 相交检查

```python
result = await mcp.call_tool(
    "test_intersection",
    {
        "geom1_wkt": "POLYGON((120 30, 120.1 30, 120.1 30.1, 120 30.1, 120 30))",
        "geom2_wkt": "POLYGON((120.05 30.05, 120.15 30.05, 120.15 30.15, 120.05 30.15, 120.05 30.05))",
        "srid": 4326
    }
)
```

#### 包含关系检查

```python
result = await mcp.call_tool(
    "test_containment",
    {
        "container_wkt": "POLYGON((120 30, 120.2 30, 120.2 30.2, 120 30.2, 120 30))",
        "contained_wkt": "POINT(120.1 30.1)",
        "srid": 4326
    }
)
```

#### 合并几何

```python
result = await mcp.call_tool(
    "union_geoms",
    {
        "geometries_wkt": [
            "POLYGON((120 30, 120.1 30, 120.1 30.1, 120 30.1, 120 30))",
            "POLYGON((120.05 30.05, 120.15 30.05, 120.15 30.15, 120.05 30.15, 120.05 30.05))"
        ],
        "srid": 4326
    }
)
```

#### 计算质心

```python
result = await mcp.call_tool(
    "get_centroid",
    {
        "geometry_wkt": "POLYGON((120 30, 120.1 30, 120.1 30.1, 120 30.1, 120 30))",
        "srid": 4326
    }
)
```

## WKT 格式说明

WKT (Well-Known Text) 是一种文本标记语言,用于表示矢量几何对象:

- **点**: `POINT(120.0 30.0)`
- **线**: `LINESTRING(120.0 30.0, 120.1 30.1)`
- **多边形**: `POLYGON((120 30, 120.1 30, 120.1 30.1, 120 30.1, 120 30))`
- **多点**: `MULTIPOINT((120 30), (120.1 30.1))`
- **多线**: `MULTILINESTRING((120 30, 120.1 30.1), (120.2 30.2, 120.3 30.3))`
- **多多边形**: `MULTIPOLYGON(((120 30, 120.1 30, 120.1 30.1, 120 30.1, 120 30)))`

## 常见 SRID

- **4326**: WGS84 (GPS坐标系统)
- **3857**: Web Mercator (网络地图投影)
- **4490**: CGCS2000 (中国大地坐标系)

## 返回值格式

所有工具调用都返回包含以下字段的字典:

```python
{
    "success": True/False,  # 操作是否成功
    "error": "错误信息",     # 失败时的错误信息
    ...                     # 其他结果数据
}
```

## 错误处理

建议在调用工具时进行错误处理:

```python
result = await mcp.call_tool("query_nearby", {...})

if result.get("success"):
    # 处理成功结果
    features = result.get("features", [])
else:
    # 处理错误
    error = result.get("error")
    print(f"操作失败: {error}")
```

## 性能优化建议

1. **限制返回结果数量**: 使用 `limit` 参数控制返回的要素数量
2. **创建空间索引**: 在数据库表的几何列上创建空间索引
3. **选择合适的 SRID**: 使用投影坐标系统(如3857)进行距离和面积计算
4. **批量操作**: 对于多个几何对象的操作,考虑使用批量处理

## 调试

启用详细日志:

```python
from loguru import logger

logger.add("debug.log", level="DEBUG")
```

查看日志文件在 `logs/` 目录下。