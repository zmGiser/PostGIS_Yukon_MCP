# 数据导入功能文档

本文档介绍 PostGIS MCP 服务器的数据导入功能，支持多种矢量和栅格格式的导入。

## 目录

- [支持的格式](#支持的格式)
- [矢量格式导入](#矢量格式导入)
  - [Shapefile 导入](#shapefile-导入)
  - [GeoJSON 导入](#geojson-导入)
- [栅格格式导入](#栅格格式导入)
  - [GeoTIFF 导入](#geotiff-导入)
  - [PNG 导入](#png-导入)
- [使用示例](#使用示例)
- [注意事项](#注意事项)

## 支持的格式

### 矢量格式

- **Shapefile (.shp)**: ESRI Shapefile 格式，包含几何和属性数据
- **GeoJSON (.geojson, .json)**: 轻量级地理数据交换格式

### 栅格格式

- **GeoTIFF (.tif, .tiff)**: 带地理参考信息的 TIFF 图像
- **PNG (.png)**: 需要提供地理配准信息的 PNG 图像

## 矢量格式导入

### Shapefile 导入

Shapefile 是最常用的矢量数据格式之一。

#### 函数签名

```python
async def import_shp(
    file_path: str,
    table_name: str,
    schema: str = "public",
    srid: int = 4326,
    geometry_column: str = "geom",
    if_exists: str = "replace"
) -> Dict[str, Any]
```

#### 参数说明

- `file_path` (必需): Shapefile 文件路径 (.shp)
- `table_name` (必需): 目标数据库表名
- `schema`: 数据库模式名，默认 "public"
- `srid`: 空间参考系统 ID，默认 4326 (WGS84)
- `geometry_column`: 几何列名，默认 "geom"
- `if_exists`: 表存在时的处理方式
  - `"replace"`: 替换现有表（默认）
  - `"append"`: 追加数据
  - `"fail"`: 抛出错误

#### 返回值

```json
{
  "success": true,
  "table_name": "public.my_table",
  "geometry_type": "Point",
  "srid": 4326,
  "feature_count": 1000,
  "columns": ["id", "name", "value", "geom"],
  "bounds": [116.0, 39.0, 117.0, 40.0]
}
```

#### 使用示例

```python
result = await import_shp(
    file_path="/path/to/data/cities.shp",
    table_name="cities",
    schema="public",
    srid=4326
)
```

### GeoJSON 导入

GeoJSON 支持从文件或字符串导入。

#### 函数签名

```python
async def import_geojson_file(
    file_path: str = None,
    geojson_data: str = None,
    table_name: str = "imported_geojson",
    schema: str = "public",
    srid: int = 4326,
    geometry_column: str = "geom",
    if_exists: str = "replace"
) -> Dict[str, Any]
```

#### 参数说明

- `file_path`: GeoJSON 文件路径（与 `geojson_data` 二选一）
- `geojson_data`: GeoJSON 字符串数据（与 `file_path` 二选一）
- `table_name`: 目标表名，默认 "imported_geojson"
- `schema`: 数据库模式名，默认 "public"
- `srid`: 空间参考系统 ID，默认 4326
- `geometry_column`: 几何列名，默认 "geom"
- `if_exists`: 表存在时的处理方式

#### 使用示例

从文件导入：

```python
result = await import_geojson_file(
    file_path="/path/to/data/features.geojson",
    table_name="features",
    schema="public"
)
```

从字符串导入：

```python
geojson_str = '''
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {"name": "Beijing"},
      "geometry": {
        "type": "Point",
        "coordinates": [116.4074, 39.9042]
      }
    }
  ]
}
'''

result = await import_geojson_file(
    geojson_data=geojson_str,
    table_name="poi",
    schema="public"
)
```

## 栅格格式导入

### GeoTIFF 导入

导入带地理参考的 TIFF 栅格数据。

#### 函数签名

```python
async def import_tif(
    file_path: str,
    table_name: str,
    schema: str = "public",
    srid: int = None,
    tile_size: int = 256,
    overview_levels: List[int] = [2, 4, 8, 16]
) -> Dict[str, Any]
```

#### 参数说明

- `file_path` (必需): GeoTIFF 文件路径
- `table_name` (必需): 目标表名
- `schema`: 数据库模式名，默认 "public"
- `srid`: 目标空间参考系统 ID（None 表示使用文件原始 SRID）
- `tile_size`: 瓦片大小，默认 256
- `overview_levels`: 概览层级，默认 [2, 4, 8, 16]

#### 返回值

```json
{
  "success": true,
  "table_name": "public.dem",
  "srid": 4326,
  "width": 1024,
  "height": 1024,
  "bands": 1,
  "dtype": "float32",
  "bounds": [116.0, 39.0, 117.0, 40.0],
  "pixel_size": [0.001, 0.001]
}
```

#### 使用示例

```python
result = await import_tif(
    file_path="/path/to/dem.tif",
    table_name="elevation",
    schema="public"
)
```

### PNG 导入

导入 PNG 图像作为地理配准栅格。需要手动提供地理边界。

#### 函数签名

```python
async def import_png(
    file_path: str,
    table_name: str,
    bounds: List[float],
    schema: str = "public",
    srid: int = 4326
) -> Dict[str, Any]
```

#### 参数说明

- `file_path` (必需): PNG 文件路径
- `table_name` (必需): 目标表名
- `bounds` (必需): 地理边界 [minx, miny, maxx, maxy]
- `schema`: 数据库模式名，默认 "public"
- `srid`: 空间参考系统 ID，默认 4326

#### 使用示例

```python
result = await import_png(
    file_path="/path/to/map.png",
    table_name="map_image",
    bounds=[116.0, 39.0, 117.0, 40.0],  # [minx, miny, maxx, maxy]
    schema="public",
    srid=4326
)
```

## 获取支持的格式

查询服务器支持的所有导入格式。

#### 函数签名

```python
async def get_supported_formats() -> Dict[str, Any]
```

#### 返回值

```json
{
  "success": true,
  "vector_formats": {
    "shapefile": {
      "extension": ".shp",
      "description": "ESRI Shapefile",
      "function": "import_shapefile"
    },
    "geojson": {
      "extension": ".geojson, .json",
      "description": "GeoJSON",
      "function": "import_geojson"
    }
  },
  "raster_formats": {
    "geotiff": {
      "extension": ".tif, .tiff",
      "description": "GeoTIFF",
      "function": "import_geotiff"
    },
    "png": {
      "extension": ".png",
      "description": "PNG (需要地理配准信息)",
      "function": "import_png_as_georeferenced"
    }
  }
}
```

## 使用示例

### 完整工作流程示例

```python
import asyncio
from src.tools.data_import import (
    import_shapefile,
    import_geojson,
    import_geotiff,
    list_supported_formats
)

async def main():
    # 1. 查看支持的格式
    formats = await list_supported_formats()
    print("支持的格式:", formats)
    
    # 2. 导入 Shapefile
    shp_result = await import_shapefile(
        file_path="data/cities.shp",
        table_name="cities",
        schema="public",
        srid=4326,
        if_exists="replace"
    )
    print(f"导入了 {shp_result['feature_count']} 个城市要素")
    
    # 3. 导入 GeoJSON
    geojson_result = await import_geojson(
        file_path="data/roads.geojson",
        table_name="roads",
        schema="public"
    )
    print(f"导入了 {geojson_result['feature_count']} 条道路")
    
    # 4. 导入 GeoTIFF
    tif_result = await import_geotiff(
        file_path="data/elevation.tif",
        table_name="dem",
        schema="public"
    )
    print(f"导入栅格: {tif_result['width']}x{tif_result['height']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 注意事项

### 坐标系统

- 默认使用 EPSG:4326 (WGS84) 坐标系统
- 导入时会自动进行坐标转换
- 建议在导入前确认数据的原始坐标系统

### 表管理

- 使用 `if_exists="replace"` 会删除现有表
- 使用 `if_exists="append"` 追加数据，但要确保表结构匹配
- 导入后会自动创建空间索引以提升查询性能

### 数据验证

- 导入前会检查文件是否存在
- 导入过程中会验证几何对象的有效性
- 建议在导入大型数据集前先测试小样本

### 性能优化

- 大型 Shapefile 可能需要较长时间导入
- GeoTIFF 导入时会考虑瓦片大小和概览层级
- 建议分批导入超大数据集

### 依赖库

确保已安装以下依赖：

```bash
pip install geopandas fiona shapely rasterio pillow numpy pyproj
```

或使用项目的 requirements.txt:

```bash
pip install -r requirements.txt
```

## 错误处理

所有导入函数都会返回包含 `success` 字段的字典：

```python
# 成功
{
  "success": true,
  "table_name": "...",
  ...
}

# 失败
{
  "success": false,
  "error": "错误信息"
}
```

建议在代码中检查 `success` 字段：

```python
result = await import_shapefile(...)
if result["success"]:
    print(f"成功导入 {result['feature_count']} 个要素")
else:
    print(f"导入失败: {result['error']}")
```

## 技术支持

如有问题或建议，请提交 Issue 或查看项目文档。