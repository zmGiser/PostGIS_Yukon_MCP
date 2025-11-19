# API 文档

本文档详细说明了 PostGIS MCP 服务器提供的所有工具接口。

## 目录

- [空间查询工具](#空间查询工具)
- [几何操作工具](#几何操作工具)
- [空间分析工具](#空间分析工具)

---

## 空间查询工具

### query_nearby

查询指定坐标附近的地理要素。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| longitude | float | 是 | - | 经度 |
| latitude | float | 是 | - | 纬度 |
| radius | float | 是 | - | 搜索半径（米） |
| table_name | string | 是 | - | 数据表名 |
| geometry_column | string | 否 | "geom" | 几何列名 |
| limit | integer | 否 | 100 | 返回结果数量限制 |

**返回值:**

```json
{
  "success": true,
  "count": 5,
  "features": [
    {
      "id": 1,
      "name": "要素名称",
      "geom": "POINT(120.123 30.456)",
      "distance": 250.5
    }
  ]
}
```

### query_bbox

查询边界框内的地理要素。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| min_x | float | 是 | - | 最小经度 |
| min_y | float | 是 | - | 最小纬度 |
| max_x | float | 是 | - | 最大经度 |
| max_y | float | 是 | - | 最大纬度 |
| table_name | string | 是 | - | 数据表名 |
| geometry_column | string | 否 | "geom" | 几何列名 |
| limit | integer | 否 | 100 | 返回结果数量限制 |

**返回值:**

```json
{
  "success": true,
  "count": 10,
  "features": [...]
}
```

### query_attribute

根据属性查询地理要素。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| table_name | string | 是 | - | 数据表名 |
| attribute_name | string | 是 | - | 属性名 |
| attribute_value | any | 是 | - | 属性值 |
| geometry_column | string | 否 | "geom" | 几何列名 |
| limit | integer | 否 | 100 | 返回结果数量限制 |

**返回值:**

```json
{
  "success": true,
  "count": 3,
  "features": [...]
}
```

---

## 几何操作工具

### buffer_geometry

创建几何缓冲区。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| geometry_wkt | string | 是 | - | WKT格式的几何对象 |
| distance | float | 是 | - | 缓冲距离（米） |
| srid | integer | 否 | 4326 | 空间参考系统ID |

**返回值:**

```json
{
  "success": true,
  "buffer_geometry": "POLYGON(...)",
  "area_sqm": 3141592.65
}
```

### get_area

计算几何对象的面积。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| geometry_wkt | string | 是 | - | WKT格式的几何对象 |
| srid | integer | 否 | 4326 | 空间参考系统ID |

**返回值:**

```json
{
  "success": true,
  "area_square_meters": 1234567.89,
  "area_square_kilometers": 1.23
}
```

### get_length

计算几何对象的长度。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| geometry_wkt | string | 是 | - | WKT格式的几何对象 |
| srid | integer | 否 | 4326 | 空间参考系统ID |

**返回值:**

```json
{
  "success": true,
  "length_meters": 15678.9,
  "length_kilometers": 15.68
}
```

### transform_coords

转换几何对象的坐标系统。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| geometry_wkt | string | 是 | - | WKT格式的几何对象 |
| from_srid | integer | 是 | - | 源空间参考系统ID |
| to_srid | integer | 是 | - | 目标空间参考系统ID |

**返回值:**

```json
{
  "success": true,
  "transformed_geometry": "POINT(...)",
  "from_srid": 4326,
  "to_srid": 3857
}
```

### simplify_geom

简化几何对象。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| geometry_wkt | string | 是 | - | WKT格式的几何对象 |
| tolerance | float | 是 | - | 简化容差 |
| srid | integer | 否 | 4326 | 空间参考系统ID |

**返回值:**

```json
{
  "success": true,
  "simplified_geometry": "LINESTRING(...)",
  "original_point_count": 1000,
  "simplified_point_count": 100,
  "reduction_ratio": 0.9
}
```

---

## 空间分析工具

### measure_distance

计算两个几何对象之间的距离。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| geom1_wkt | string | 是 | - | 第一个几何对象的WKT格式 |
| geom2_wkt | string | 是 | - | 第二个几何对象的WKT格式 |
| srid | integer | 否 | 4326 | 空间参考系统ID |

**返回值:**

```json
{
  "success": true,
  "distance_meters": 15678.9,
  "distance_kilometers": 15.68
}
```

### test_intersection

检查两个几何对象是否相交。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| geom1_wkt | string | 是 | - | 第一个几何对象的WKT格式 |
| geom2_wkt | string | 是 | - | 第二个几何对象的WKT格式 |
| srid | integer | 否 | 4326 | 空间参考系统ID |

**返回值:**

```json
{
  "success": true,
  "intersects": true,
  "intersection_geometry": "POLYGON(...)"
}
```

### test_containment

检查一个几何对象是否包含另一个。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| container_wkt | string | 是 | - | 容器几何对象的WKT格式 |
| contained_wkt | string | 是 | - | 被包含几何对象的WKT格式 |
| srid | integer | 否 | 4326 | 空间参考系统ID |

**返回值:**

```json
{
  "success": true,
  "contains": true,
  "within": true
}
```

### union_geoms

合并多个几何对象。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| geometries_wkt | array[string] | 是 | - | WKT格式的几何对象列表 |
| srid | integer | 否 | 4326 | 空间参考系统ID |

**返回值:**

```json
{
  "success": true,
  "union_geometry": "POLYGON(...)",
  "area_square_meters": 5678.9
}
```

### get_centroid

计算几何对象的质心。

**参数:**

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| geometry_wkt | string | 是 | - | WKT格式的几何对象 |
| srid | integer | 否 | 4326 | 空间参考系统ID |

**返回值:**

```json
{
  "success": true,
  "centroid_geometry": "POINT(120.05 30.05)",
  "longitude": 120.05,
  "latitude": 30.05
}
```

---

## 错误响应格式

当操作失败时，所有工具都返回以下格式:

```json
{
  "success": false,
  "error": "错误描述信息"
}
```

## 常见错误

- **数据库连接失败**: 检查 `.env` 文件中的数据库配置
- **表不存在**: 确认表名正确且数据库中存在该表
- **几何列不存在**: 检查 `geometry_column` 参数是否正确
- **无效的WKT格式**: 确保提供的WKT字符串格式正确
- **SRID不支持**: 使用数据库支持的SRID值

## 性能提示

1. 为几何列创建空间索引: `CREATE INDEX idx_geom ON table_name USING GIST(geom);`
2. 对于大范围查询，考虑增加 `limit` 参数
3. 使用适当的SRID进行距离和面积计算
4. 定期运行 `VACUUM ANALYZE` 优化数据库性能