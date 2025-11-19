# Text-to-SQL 功能文档

## 概述

Text-to-SQL功能允许用户使用自然语言描述查询需求，系统会自动将其转换为PostGIS SQL语句。这大大简化了空间查询的使用门槛，用户无需掌握复杂的SQL语法即可进行空间分析。

## 核心特性

### 1. 自然语言理解
- 支持中英文查询描述
- 自动识别查询意图（附近、缓冲区、面积、距离等）
- 智能提取关键参数（表名、坐标、距离等）

### 2. SQL生成
- 自动生成标准PostGIS SQL语句
- 包含详细注释说明
- 保证SQL语法正确性和安全性

### 3. 预览与确认机制
- 生成SQL后先返回预览
- 用户可检查SQL语句
- 需显式确认后才执行

### 4. 安全保护
- 仅支持SELECT查询
- 禁止危险操作（DROP、DELETE等）
- 自动添加结果数量限制

## 使用方法

### 基本工作流程

```
用户自然语言查询 
  ↓
nl_to_sql工具解析并生成SQL
  ↓
返回SQL预览给用户
  ↓
用户检查确认
  ↓
execute_sql工具执行查询
  ↓
返回结果
```

### 工具1: nl_to_sql

将自然语言转换为SQL语句。

**参数:**
- `query` (必需): 自然语言查询描述
- `table_name` (可选): 目标表名（如果查询中未指定）
- `schema` (可选): 数据库模式名，默认"public"

**返回:**
```json
{
  "success": true,
  "message": "SQL生成成功。请检查以下SQL语句...",
  "query_type": "nearby",
  "table_name": "buildings",
  "schema": "public",
  "generated_sql": "SELECT * FROM ...",
  "parameters": {
    "longitude": 120.5,
    "latitude": 30.2,
    "radius_meters": 500
  },
  "original_query": "查询120.5,30.2附近500米的建筑",
  "warning": "⚠️ 请仔细检查SQL语句后再执行..."
}
```

### 工具2: execute_sql

执行SQL查询语句。

**参数:**
- `sql` (必需): 要执行的SQL语句
- `limit` (可选): 结果数量限制，默认100
- `confirmed` (必需): 确认标志，必须设置为true

**返回:**
```json
{
  "success": true,
  "row_count": 5,
  "results": [...]
}
```

## 支持的查询类型

### 1. 附近查询 (nearby)

查找指定位置附近的要素。

**自然语言示例:**
```
"查询表:buildings 坐标120.5,30.2 附近500米的建筑"
"find restaurants near 121.5, 31.2 within 1km"
"在120.15,30.25周围1公里范围内查找表:parks"
```

**生成SQL示例:**
```sql
-- 查询坐标(120.5, 30.2)周围500米内的要素
SELECT 
    *,
    ST_Distance(
        ST_Transform(geom, 4326)::geography,
        ST_GeogFromText('SRID=4326;POINT(120.5 30.2)')
    ) as distance_meters
FROM public.buildings
WHERE ST_DWithin(
    ST_Transform(geom, 4326)::geography,
    ST_GeogFromText('SRID=4326;POINT(120.5 30.2)'),
    500
)
ORDER BY distance_meters
LIMIT 100;
```

### 2. 缓冲区分析 (buffer)

为几何对象创建缓冲区。

**自然语言示例:**
```
"为表:roads创建50米缓冲区"
"create 100m buffer for table:rivers"
"生成表:railways的200米缓冲"
```

**生成SQL示例:**
```sql
-- 创建50米缓冲区
SELECT 
    *,
    ST_AsText(
        ST_Buffer(
            ST_Transform(geom, 3857),
            50
        )
    ) as buffer_geom,
    ST_Area(
        ST_Buffer(
            ST_Transform(geom, 3857),
            50
        )
    ) as buffer_area_sqm
FROM public.roads;
```

### 3. 面积计算 (area)

计算几何对象的面积。

**自然语言示例:**
```
"计算表:parks的面积"
"calculate area of table:districts"
"求表:parcels所有要素的大小"
```

**生成SQL示例:**
```sql
-- 计算几何面积
SELECT 
    *,
    ST_Area(ST_Transform(geom, 3857)) as area_sqm,
    ST_Area(ST_Transform(geom, 3857)) / 1000000.0 as area_sqkm
FROM public.parks
ORDER BY area_sqm DESC;
```

### 4. 要素计数 (count)

统计要素数量。

**自然语言示例:**
```
"统计表:buildings的数量"
"count features in table:points"
"表:restaurants有多少个"
```

**生成SQL示例:**
```sql
-- 统计要素数量
SELECT COUNT(*) as feature_count
FROM public.buildings;
```

## 使用示例

### 示例1: 附近餐厅查询

**步骤1: 生成SQL**
```python
result = await nl_to_sql(
    query="查询表:restaurants 坐标120.15,30.25 附近500米的餐厅"
)
```

**响应:**
```json
{
  "success": true,
  "generated_sql": "SELECT ...",
  "query_type": "nearby",
  "parameters": {
    "longitude": 120.15,
    "latitude": 30.25,
    "radius_meters": 500
  }
}
```

**步骤2: 检查并执行SQL**
```python
result = await execute_sql(
    sql=generated_sql,
    limit=10,
    confirmed=True
)
```

### 示例2: 道路缓冲区

**步骤1: 生成SQL**
```python
result = await nl_to_sql(
    query="为表:roads创建100米缓冲区"
)
```

**步骤2: 执行SQL**
```python
result = await execute_sql(
    sql=generated_sql,
    confirmed=True
)
```

## 查询语法规则

### 表名指定

支持以下格式：
- `表:table_name`
- `table: table_name`
- 或通过`table_name`参数单独指定

示例：
```
"查询表:buildings附近的要素"
"find features in table:parks"
```

### 坐标指定

格式：`经度,纬度` 或 `经度，纬度`

示例：
```
"120.5, 30.2"
"121.15，31.25"
```

### 距离指定

支持单位：
- 米: `米`, `m`, `meter`, `meters`
- 公里: `公里`, `千米`, `km`, `kilometer`, `kilometers`

示例：
```
"500米"
"1公里"
"1.5km"
"2000 meters"
```

## 最佳实践

### 1. 明确查询意图
使用清晰的关键词描述查询类型：
- ✅ "查询附近的建筑"
- ✅ "创建缓冲区"
- ✅ "计算面积"
- ❌ "找一下数据"（过于模糊）

### 2. 提供完整参数
确保包含所有必要信息：
- ✅ "查询表:buildings 坐标120.5,30.2 附近500米"
- ❌ "查询附近的建筑"（缺少坐标和距离）

### 3. 检查生成的SQL
- 始终查看生成的SQL语句
- 检查表名、列名是否正确
- 确认查询逻辑符合预期
- 注意LIMIT限制是否合理

### 4. 使用确认机制
- 不要跳过SQL预览步骤
- 复杂查询建议先小范围测试
- 确认无误后再执行大规模查询

## 限制与注意事项

### 功能限制

1. **仅支持SELECT查询**
   - 不支持INSERT、UPDATE、DELETE
   - 不支持CREATE、DROP等DDL操作

2. **查询类型限制**
   - 当前支持：附近查询、缓冲区、面积、计数
   - 复杂的空间关系查询需要手写SQL

3. **参数提取限制**
   - 坐标必须是数字格式
   - 距离必须包含数值和单位
   - 表名需符合命名规范

### 安全注意事项

1. **SQL注入防护**
   - 系统会检查危险关键词
   - 禁止执行修改数据的操作
   - 自动添加LIMIT限制

2. **性能考虑**
   - 大范围查询可能较慢
   - 建议使用适当的LIMIT
   - 确保表有空间索引

3. **数据安全**
   - 生成的SQL可能返回敏感数据
   - 建议检查查询范围
   - 注意结果数据的使用权限

## 错误处理

### 常见错误及解决方法

**错误1: 无法识别查询类型**
```json
{
  "success": false,
  "error": "无法识别查询类型。请使用更明确的描述..."
}
```
**解决:** 使用明确的关键词，如"附近"、"缓冲区"、"面积"等

**错误2: 未指定表名**
```json
{
  "success": false,
  "error": "未指定表名。请在查询中包含表名..."
}
```
**解决:** 在查询中添加`表:table_name`或使用`table_name`参数

**错误3: 表不存在**
```json
{
  "success": false,
  "error": "表 public.xxx 不存在或不包含几何列"
}
```
**解决:** 检查表名是否正确，确认表已创建且包含几何列

**错误4: 缺少必要参数**
```json
{
  "success": false,
  "error": "未找到坐标信息。请提供经纬度坐标..."
}
```
**解决:** 补充缺失的参数（坐标、距离等）

## 扩展与定制

### 添加新查询类型

要添加新的查询类型，需要修改以下部分：

1. **更新模式识别** (`NLQueryParser.QUERY_PATTERNS`)
2. **添加SQL生成器** (`SQLGenerator.generate_xxx_query`)
3. **更新解析逻辑** (`parse_nl_query`函数)

示例：添加距离查询
```python
# 1. 添加模式
QUERY_PATTERNS = {
    ...
    'distance': [
        r'(距离|相距)',
        r'(distance|how far)',
    ],
}

# 2. 添加生成器
@staticmethod
def generate_distance_query(geom1_wkt, geom2_wkt, srid=4326):
    return f"""
    SELECT ST_Distance(
        ST_Transform(ST_GeomFromText('{geom1_wkt}', {srid}), 3857),
        ST_Transform(ST_GeomFromText('{geom2_wkt}', {srid}), 3857)
    ) as distance_meters;
    """
```

### 自定义参数提取

可以添加新的参数提取方法：

```python
@classmethod
def extract_custom_param(cls, query: str):
    pattern = r'your_pattern_here'
    match = re.search(pattern, query)
    if match:
        return process_match(match)
    return None
```

## 未来计划

1. **更多查询类型**
   - 相交分析
   - 包含关系查询
   - 空间连接

2. **智能推荐**
   - 根据历史查询推荐
   - 自动补全参数
   - 查询优化建议

3. **多语言支持**
   - 更多语言的自然语言理解
   - 国际化错误提示

4. **可视化集成**
   - 查询结果可视化
   - 交互式参数调整

## 相关文档

- [API文档](../API.md)
- [使用指南](../USAGE.md)
- [数据导入指南](DATA_IMPORT.md)

## 技术支持

如有问题或建议，请：
1. 查看文档中的错误处理章节
2. 检查测试用例示例
3. 提交Issue或联系开发团队