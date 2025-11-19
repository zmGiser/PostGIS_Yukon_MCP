"""
PostGIS MCP 服务器主入口
使用 FastMCP 框架封装 PostGIS 工具
"""
import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from mcp.server import FastMCP
import subprocess
import time
import requests

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入数据库配置 - 使用绝对导入
from src.config.database import db_config

# 导入工具函数
from src.tools import (
    query_nearby_features,
    query_within_bbox,
    query_by_attribute,
    create_buffer,
    calculate_area,
    calculate_length,
    transform_geometry,
    simplify_geometry,
    calculate_distance,
    check_intersection,
    check_containment,
    union_geometries,
    calculate_centroid,
    spatial_join,
    nearest_neighbor,
    spatial_cluster,
    convex_hull,
    voronoi_polygons,
    line_interpolate,
    snap_to_grid,
    split_line_by_point,
    get_postgis_version,
    list_installed_extensions,
    list_spatial_tables,
    get_table_spatial_info,
    create_spatial_index,
    analyze_table,
    vacuum_table,
    get_spatial_extent,
    check_geometry_validity,
    import_shapefile,
    import_geojson,
    import_geotiff,
    import_png_as_georeferenced,
    list_supported_formats,
)
from src.tools.text_to_sql import (
    parse_nl_query,
    execute_generated_sql,
)
from src.tools.vanna_mcp_adapter import (
    get_vanna_mcp_adapter,
    VANNA_AVAILABLE,
)

# 初始化 FastMCP 服务器
mcp = FastMCP("PostGIS MCP Server")


# ============= 空间查询工具 =============

@mcp.tool()
async def query_nearby(
    longitude: float,
    latitude: float,
    radius: float,
    table_name: str,
    geometry_column: str = "geom",
    limit: int = 100
) -> Dict[str, Any]:
    """
    查询指定坐标附近的地理要素
    
    Args:
        longitude: 经度
        latitude: 纬度
        radius: 搜索半径（米）
        table_name: 表名
        geometry_column: 几何列名，默认为 'geom'
        limit: 返回结果数量限制，默认100
        
    Returns:
        查询结果字典，包含要素列表和距离信息
    """
    try:
        results = await query_nearby_features(
            longitude, latitude, radius, table_name, geometry_column, limit
        )
        return {
            "success": True,
            "count": len(results),
            "features": results
        }
    except Exception as e:
        logger.error(f"查询附近要素失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def query_bbox(
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    table_name: str,
    geometry_column: str = "geom",
    limit: int = 100
) -> Dict[str, Any]:
    """
    查询边界框内的地理要素
    
    Args:
        min_x: 最小经度
        min_y: 最小纬度
        max_x: 最大经度
        max_y: 最大纬度
        table_name: 表名
        geometry_column: 几何列名，默认为 'geom'
        limit: 返回结果数量限制，默认100
        
    Returns:
        查询结果字典，包含边界框内的要素列表
    """
    try:
        results = await query_within_bbox(
            min_x, min_y, max_x, max_y, table_name, geometry_column, limit
        )
        return {
            "success": True,
            "count": len(results),
            "features": results
        }
    except Exception as e:
        logger.error(f"查询边界框内要素失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def query_attribute(
    table_name: str,
    attribute_name: str,
    attribute_value: Any,
    geometry_column: str = "geom",
    limit: int = 100
) -> Dict[str, Any]:
    """
    根据属性查询地理要素
    
    Args:
        table_name: 表名
        attribute_name: 属性名
        attribute_value: 属性值
        geometry_column: 几何列名，默认为 'geom'
        limit: 返回结果数量限制，默认100
        
    Returns:
        查询结果字典，包含匹配的要素列表
    """
    try:
        results = await query_by_attribute(
            table_name, attribute_name, attribute_value, geometry_column, limit
        )
        return {
            "success": True,
            "count": len(results),
            "features": results
        }
    except Exception as e:
        logger.error(f"根据属性查询要素失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============= 几何操作工具 =============

@mcp.tool()
async def buffer_geometry(
    geometry_wkt: str,
    distance: float,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    创建几何缓冲区
    
    Args:
        geometry_wkt: WKT格式的几何对象
        distance: 缓冲距离（米）
        srid: 空间参考系统ID，默认4326（WGS84）
        
    Returns:
        包含缓冲区几何和面积信息的字典
    """
    try:
        result = await create_buffer(geometry_wkt, distance, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"创建缓冲区失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def get_area(
    geometry_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    计算几何面积
    
    Args:
        geometry_wkt: WKT格式的几何对象
        srid: 空间参考系统ID，默认4326（WGS84）
        
    Returns:
        包含面积信息的字典（平方米和平方公里）
    """
    try:
        result = await calculate_area(geometry_wkt, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"计算面积失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def get_length(
    geometry_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    计算几何长度
    
    Args:
        geometry_wkt: WKT格式的几何对象
        srid: 空间参考系统ID，默认4326（WGS84）
        
    Returns:
        包含长度信息的字典（米和公里）
    """
    try:
        result = await calculate_length(geometry_wkt, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"计算长度失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def transform_coords(
    geometry_wkt: str,
    from_srid: int,
    to_srid: int
) -> Dict[str, Any]:
    """
    转换几何坐标系统
    
    Args:
        geometry_wkt: WKT格式的几何对象
        from_srid: 源空间参考系统ID
        to_srid: 目标空间参考系统ID
        
    Returns:
        包含转换后几何的字典
    """
    try:
        result = await transform_geometry(geometry_wkt, from_srid, to_srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"坐标系统转换失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def simplify_geom(
    geometry_wkt: str,
    tolerance: float,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    简化几何对象
    
    Args:
        geometry_wkt: WKT格式的几何对象
        tolerance: 简化容差
        srid: 空间参考系统ID，默认4326（WGS84）
        
    Returns:
        包含简化后几何和统计信息的字典
    """
    try:
        result = await simplify_geometry(geometry_wkt, tolerance, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"简化几何失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============= 空间分析工具 =============

@mcp.tool()
async def measure_distance(
    geom1_wkt: str,
    geom2_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    计算两个几何对象之间的距离
    
    Args:
        geom1_wkt: 第一个几何对象的WKT格式
        geom2_wkt: 第二个几何对象的WKT格式
        srid: 空间参考系统ID，默认4326（WGS84）
        
    Returns:
        包含距离信息的字典（米和公里）
    """
    try:
        result = await calculate_distance(geom1_wkt, geom2_wkt, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"计算距离失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def test_intersection(
    geom1_wkt: str,
    geom2_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    检查两个几何对象是否相交
    
    Args:
        geom1_wkt: 第一个几何对象的WKT格式
        geom2_wkt: 第二个几何对象的WKT格式
        srid: 空间参考系统ID，默认4326（WGS84）
        
    Returns:
        包含相交信息和相交几何的字典
    """
    try:
        result = await check_intersection(geom1_wkt, geom2_wkt, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"相交检查失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def test_containment(
    container_wkt: str,
    contained_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    检查一个几何对象是否包含另一个
    
    Args:
        container_wkt: 容器几何对象的WKT格式
        contained_wkt: 被包含几何对象的WKT格式
        srid: 空间参考系统ID，默认4326（WGS84）
        
    Returns:
        包含包含关系信息的字典
    """
    try:
        result = await check_containment(container_wkt, contained_wkt, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"包含关系检查失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def union_geoms(
    geometries_wkt: List[str],
    srid: int = 4326
) -> Dict[str, Any]:
    """
    合并多个几何对象
    
    Args:
        geometries_wkt: WKT格式的几何对象列表
        srid: 空间参考系统ID，默认4326（WGS84）
        
    Returns:
        包含合并后几何和面积信息的字典
    """
    try:
        result = await union_geometries(geometries_wkt, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"合并几何对象失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def get_centroid(
    geometry_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    计算几何对象的质心
    
    Args:
        geometry_wkt: WKT格式的几何对象
        srid: 空间参考系统ID，默认4326（WGS84）
        
    Returns:
        包含质心坐标的字典
    """
    try:
        result = await calculate_centroid(geometry_wkt, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"计算质心失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============= 数据库管理工具 =============

@mcp.tool()
async def postgis_version() -> Dict[str, Any]:
    """
    获取 PostGIS 版本信息
    
    Returns:
        包含 PostGIS 各组件版本信息的字典
    """
    try:
        result = await get_postgis_version()
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"获取 PostGIS 版本失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def list_extensions() -> Dict[str, Any]:
    """
    列出数据库中已安装的所有扩展
    
    Returns:
        已安装扩展列表
    """
    try:
        extensions = await list_installed_extensions()
        return {
            "success": True,
            "count": len(extensions),
            "extensions": extensions
        }
    except Exception as e:
        logger.error(f"列出扩展失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def discover_spatial_tables(schema: str = "public") -> Dict[str, Any]:
    """
    发现包含空间字段的表
    
    Args:
        schema: 数据库模式名，默认为 'public'
        
    Returns:
        包含空间字段的表列表
    """
    try:
        tables = await list_spatial_tables(schema)
        return {
            "success": True,
            "schema": schema,
            "count": len(tables),
            "tables": tables
        }
    except Exception as e:
        logger.error(f"发现空间表失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def table_info(
    table_name: str,
    schema: str = "public"
) -> Dict[str, Any]:
    """
    获取表的详细空间信息
    
    Args:
        table_name: 表名
        schema: 模式名，默认为 'public'
        
    Returns:
        表的详细空间信息，包括几何列、索引和统计信息
    """
    try:
        info = await get_table_spatial_info(table_name, schema)
        return {
            "success": True,
            **info
        }
    except Exception as e:
        logger.error(f"获取表信息失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def create_index(
    table_name: str,
    geometry_column: str = "geom",
    schema: str = "public",
    index_name: str = None
) -> Dict[str, Any]:
    """
    为空间列创建 GIST 索引
    
    Args:
        table_name: 表名
        geometry_column: 几何列名，默认为 'geom'
        schema: 模式名，默认为 'public'
        index_name: 索引名称，如果不提供则自动生成
        
    Returns:
        索引创建结果
    """
    try:
        result = await create_spatial_index(
            table_name, geometry_column, schema, index_name
        )
        return result
    except Exception as e:
        logger.error(f"创建索引失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def analyze(
    table_name: str,
    schema: str = "public"
) -> Dict[str, Any]:
    """
    分析表以更新统计信息
    
    Args:
        table_name: 表名
        schema: 模式名，默认为 'public'
        
    Returns:
        分析结果
    """
    try:
        result = await analyze_table(table_name, schema)
        return result
    except Exception as e:
        logger.error(f"分析表失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def vacuum(
    table_name: str,
    schema: str = "public",
    full: bool = False
) -> Dict[str, Any]:
    """
    清理表以回收空间
    
    Args:
        table_name: 表名
        schema: 模式名，默认为 'public'
        full: 是否执行完全清理
        
    Returns:
        清理结果
    """
    try:
        result = await vacuum_table(table_name, schema, full)
        return result
    except Exception as e:
        logger.error(f"清理表失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def spatial_extent(
    table_name: str,
    geometry_column: str = "geom",
    schema: str = "public"
) -> Dict[str, Any]:
    """
    获取表的空间范围
    
    Args:
        table_name: 表名
        geometry_column: 几何列名
        schema: 模式名
        
    Returns:
        表的空间范围信息
    """
    try:
        result = await get_spatial_extent(table_name, geometry_column, schema)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"获取空间范围失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def validate_geometries(
    table_name: str,
    geometry_column: str = "geom",
    schema: str = "public"
) -> Dict[str, Any]:
    """
    检查表中几何对象的有效性
    
    Args:
        table_name: 表名
        geometry_column: 几何列名
        schema: 模式名
        
    Returns:
        几何有效性检查结果
    """
    try:
        result = await check_geometry_validity(table_name, geometry_column, schema)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"检查几何有效性失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============= 高级空间分析工具 =============

@mcp.tool()
async def join_spatial(
    table1: str,
    table2: str,
    geom_col1: str = "geom",
    geom_col2: str = "geom",
    join_type: str = "intersects",
    schema: str = "public"
) -> Dict[str, Any]:
    """
    执行空间连接操作
    
    Args:
        table1: 第一个表名
        table2: 第二个表名
        geom_col1: 第一个表的几何列名
        geom_col2: 第二个表的几何列名
        join_type: 连接类型 (intersects, contains, within, touches, overlaps)
        schema: 模式名
        
    Returns:
        空间连接结果
    """
    try:
        results = await spatial_join(
            table1, table2, geom_col1, geom_col2, join_type, schema
        )
        return {
            "success": True,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"空间连接失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def find_nearest(
    point_wkt: str,
    table_name: str,
    geometry_column: str = "geom",
    k: int = 5,
    max_distance: float = None,
    schema: str = "public",
    srid: int = 4326
) -> Dict[str, Any]:
    """
    查找最近的K个邻居
    
    Args:
        point_wkt: 查询点的WKT格式
        table_name: 表名
        geometry_column: 几何列名
        k: 返回的邻居数量
        max_distance: 最大搜索距离（米）
        schema: 模式名
        srid: 空间参考系统ID
        
    Returns:
        最近邻居列表
    """
    try:
        neighbors = await nearest_neighbor(
            point_wkt, table_name, geometry_column, k, max_distance, schema, srid
        )
        return {
            "success": True,
            "count": len(neighbors),
            "neighbors": neighbors
        }
    except Exception as e:
        logger.error(f"最近邻查询失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def cluster_spatial(
    table_name: str,
    geometry_column: str = "geom",
    distance: float = 100,
    min_points: int = 5,
    schema: str = "public"
) -> Dict[str, Any]:
    """
    使用 DBSCAN 进行空间聚类
    
    Args:
        table_name: 表名
        geometry_column: 几何列名
        distance: 聚类距离阈值（米）
        min_points: 最小点数
        schema: 模式名
        
    Returns:
        聚类结果
    """
    try:
        result = await spatial_cluster(
            table_name, geometry_column, distance, min_points, schema
        )
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"空间聚类失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def compute_convex_hull(
    table_name: str,
    geometry_column: str = "geom",
    schema: str = "public"
) -> Dict[str, Any]:
    """
    计算表中所有几何对象的凸包
    
    Args:
        table_name: 表名
        geometry_column: 几何列名
        schema: 模式名
        
    Returns:
        凸包信息
    """
    try:
        result = await convex_hull(table_name, geometry_column, schema)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"计算凸包失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def generate_voronoi(
    table_name: str,
    geometry_column: str = "geom",
    schema: str = "public"
) -> Dict[str, Any]:
    """
    生成 Voronoi 多边形
    
    Args:
        table_name: 表名
        geometry_column: 几何列名
        schema: 模式名
        
    Returns:
        Voronoi 多边形列表
    """
    try:
        polygons = await voronoi_polygons(table_name, geometry_column, schema)
        return {
            "success": True,
            "count": len(polygons),
            "polygons": polygons
        }
    except Exception as e:
        logger.error(f"生成 Voronoi 多边形失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def interpolate_line(
    line_wkt: str,
    fraction: float,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    沿线段插值点
    
    Args:
        line_wkt: 线段的WKT格式
        fraction: 插值比例 (0-1)
        srid: 空间参考系统ID
        
    Returns:
        插值点信息
    """
    try:
        result = await line_interpolate(line_wkt, fraction, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"线段插值失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def snap_geometry(
    geometry_wkt: str,
    grid_size: float,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    将几何对象捕捉到网格
    
    Args:
        geometry_wkt: WKT格式的几何对象
        grid_size: 网格大小
        srid: 空间参考系统ID
        
    Returns:
        捕捉后的几何对象
    """
    try:
        result = await snap_to_grid(geometry_wkt, grid_size, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"捕捉到网格失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def split_line(
    line_wkt: str,
    point_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    使用点分割线段
    
    Args:
        line_wkt: 线段的WKT格式
        point_wkt: 分割点的WKT格式
        srid: 空间参考系统ID
        
    Returns:
        分割后的线段信息
    """
    try:
        result = await split_line_by_point(line_wkt, point_wkt, srid)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"线段分割失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============= 数据导入工具 =============

@mcp.tool()
async def import_shp(
    file_path: str,
    table_name: str,
    schema: str = "public",
    srid: int = 4326,
    geometry_column: str = "geom",
    if_exists: str = "replace"
) -> Dict[str, Any]:
    """
    导入 Shapefile 到 PostGIS
    
    Args:
        file_path: Shapefile 文件路径(.shp)
        table_name: 目标表名
        schema: 数据库模式名，默认为 'public'
        srid: 空间参考系统ID，默认4326（WGS84）
        geometry_column: 几何列名，默认为 'geom'
        if_exists: 如果表存在的处理方式 ('replace', 'append', 'fail')，默认'replace'
        
    Returns:
        导入结果信息，包括表名、几何类型、要素数量等
    """
    try:
        result = await import_shapefile(
            file_path, table_name, schema, srid, geometry_column, if_exists
        )
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"导入 Shapefile 失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def import_geojson_file(
    file_path: str = None,
    geojson_data: str = None,
    table_name: str = "imported_geojson",
    schema: str = "public",
    srid: int = 4326,
    geometry_column: str = "geom",
    if_exists: str = "replace"
) -> Dict[str, Any]:
    """
    导入 GeoJSON 到 PostGIS
    
    Args:
        file_path: GeoJSON 文件路径（与geojson_data二选一）
        geojson_data: GeoJSON 字符串数据（与file_path二选一）
        table_name: 目标表名，默认为 'imported_geojson'
        schema: 数据库模式名，默认为 'public'
        srid: 空间参考系统ID，默认4326（WGS84）
        geometry_column: 几何列名，默认为 'geom'
        if_exists: 如果表存在的处理方式 ('replace', 'append', 'fail')，默认'replace'
        
    Returns:
        导入结果信息，包括表名、几何类型、要素数量等
    """
    try:
        result = await import_geojson(
            file_path, geojson_data, table_name, schema, srid, geometry_column, if_exists
        )
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"导入 GeoJSON 失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def import_tif(
    file_path: str,
    table_name: str,
    schema: str = "public",
    srid: int = None,
    tile_size: int = 256,
    overview_levels: List[int] = [2, 4, 8, 16]
) -> Dict[str, Any]:
    """
    导入 GeoTIFF 栅格数据到 PostGIS
    
    Args:
        file_path: GeoTIFF 文件路径(.tif或.tiff)
        table_name: 目标表名
        schema: 数据库模式名，默认为 'public'
        srid: 目标空间参考系统ID，如果为None则使用文件原始SRID
        tile_size: 瓦片大小，默认256
        overview_levels: 概览层级，默认[2, 4, 8, 16]
        
    Returns:
        导入结果信息，包括表名、尺寸、波段数等
    """
    try:
        result = await import_geotiff(
            file_path, table_name, schema, srid, tile_size, overview_levels
        )
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"导入 GeoTIFF 失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def import_png(
    file_path: str,
    table_name: str,
    bounds: List[float],
    schema: str = "public",
    srid: int = 4326
) -> Dict[str, Any]:
    """
    导入 PNG 图像作为地理配准栅格
    
    Args:
        file_path: PNG 文件路径
        table_name: 目标表名
        bounds: 地理边界 [minx, miny, maxx, maxy]
        schema: 数据库模式名，默认为 'public'
        srid: 空间参考系统ID，默认4326（WGS84）
        
    Returns:
        导入结果信息，包括表名、尺寸、地理范围等
    """
    try:
        result = await import_png_as_georeferenced(
            file_path, table_name, bounds, schema, srid
        )
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"导入 PNG 失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def get_supported_formats() -> Dict[str, Any]:
    """
    列出所有支持的数据导入格式
    
    Returns:
        支持的矢量和栅格格式列表
    """
    try:
        result = await list_supported_formats()
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"获取支持格式失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# ============= Text-to-SQL 工具 =============

@mcp.tool()
async def nl_to_sql(
    query: str,
    table_name: str = None,
    schema: str = "public"
) -> Dict[str, Any]:
    """
    将自然语言查询转换为PostGIS SQL语句
    
    此工具会解析您的自然语言描述并生成相应的SQL查询语句。
    生成的SQL将返回给您预览，您需要确认后才能执行。
    
    Args:
        query: 自然语言查询描述
               例如: "查询120.5, 30.2附近500米内的建筑"
                    "计算buildings表中所有要素的面积"
                    "创建100米的缓冲区"
        table_name: 目标表名(如果查询中未指定)
        schema: 数据库模式名，默认为 'public'
        
    Returns:
        包含生成的SQL和参数信息的字典，需要用户确认后使用execute_sql工具执行
        
    示例:
        1. 附近查询:
           query: "查询表:buildings 坐标120.15,30.25 附近500米的建筑"
           
        2. 面积计算:
           query: "计算表:parks的面积"
           
        3. 缓冲区:
           query: "为表:roads创建50米缓冲区"
    """
    try:
        result = await parse_nl_query(query, table_name, schema)
        
        if not result.get("success"):
            return result
        
        return {
            "success": True,
            "message": "SQL生成成功。请检查以下SQL语句，确认无误后使用execute_sql工具执行。",
            "query_type": result.get("query_type"),
            "table_name": result.get("table_name"),
            "schema": result.get("schema"),
            "generated_sql": result.get("sql"),
            "parameters": result.get("parameters"),
            "original_query": result.get("original_query"),
            "warning": "⚠️ 请仔细检查SQL语句后再执行，特别注意WHERE条件和LIMIT限制"
        }
        
    except Exception as e:
        logger.error(f"NL to SQL转换失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def execute_sql(
    sql: str,
    limit: int = 100,
    confirmed: bool = False
) -> Dict[str, Any]:
    """
    执行SQL查询语句
    
    ⚠️ 重要安全提示:
    - 此工具执行用户提供的SQL语句
    - 仅执行SELECT查询，不支持INSERT/UPDATE/DELETE等修改操作
    - 建议先使用nl_to_sql生成SQL并预览
    - 执行前请确认SQL语句的正确性和安全性
    
    Args:
        sql: 要执行的SQL语句(仅支持SELECT查询)
        limit: 结果数量限制，默认100
        confirmed: 确认标志，必须设置为true才能执行
        
    Returns:
        查询结果
        
    示例:
        execute_sql(
            sql="SELECT * FROM buildings WHERE area > 1000 LIMIT 10",
            limit=10,
            confirmed=True
        )
    """
    if not confirmed:
        return {
            "success": False,
            "error": "请设置confirmed=True以确认执行SQL语句"
        }
    
    # 安全检查: 只允许SELECT语句
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith('SELECT') and not sql_upper.startswith('--'):
        return {
            "success": False,
            "error": "安全限制: 只允许执行SELECT查询语句"
        }
    
    # 检查是否包含危险操作
    dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE']
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return {
                "success": False,
                "error": f"安全限制: SQL中不允许包含 {keyword} 操作"
            }
    
    try:
        result = await execute_generated_sql(sql, limit)
        return result
        
    except Exception as e:
        logger.error(f"执行SQL失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============= Vanna AI 工具 (高级Text-to-SQL) =============

@mcp.tool()
async def vanna_init(
    model_name: str = "gpt-4",
    api_key: str = None,
    api_base: str = None,
    embedding_model: str = "text-embedding-3-small"
) -> Dict[str, Any]:
    """
    初始化本地Vanna模型(使用您自己的LLM)
    
    使用ChromaDB本地存储训练数据,使用您自己的LLM API生成SQL。
    完全不依赖Vanna云服务,训练数据保存在本地。
    
    Args:
        model_name: LLM模型名称(如gpt-4, claude-3-opus等)
        api_key: 您的LLM API密钥(或设置OPENAI_API_KEY环境变量)
        api_base: API基础URL(可选,用于自定义端点如Azure OpenAI)
        embedding_model: 嵌入模型名称
        
    Returns:
        初始化结果
        
    示例:
        # 使用OpenAI
        vanna_init(model_name="gpt-4", api_key="sk-...")
        
        # 使用自定义端点
        vanna_init(
            model_name="gpt-4",
            api_key="your-key",
            api_base="https://your-endpoint.openai.azure.com/v1"
        )
        
    注意:
        - 需要安装: pip install chromadb openai
        - 训练数据保存在本地./chroma_db目录
        - 支持OpenAI兼容的API端点
    """
    try:
        adapter = get_vanna_mcp_adapter()
        result = await adapter.initialize(model_name, api_key, api_base)
        return result
        
    except Exception as e:
        logger.error(f"Vanna初始化失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def vanna_train_ddl(schema: str = "public") -> Dict[str, Any]:
    """
    预览数据库DDL训练 - 需要用户确认后才执行
    
    此工具会显示将要训练的数据库结构信息，
    需要使用vanna_confirm_training确认后才会实际训练。
    
    Args:
        schema: 数据库模式名，默认"public"
        
    Returns:
        训练预览结果和会话ID
        
    示例:
        1. vanna_train_ddl(schema="public")
        2. 检查返回的信息
        3. vanna_confirm_training(session_id="training_xxx")
    """
    if not VANNA_AVAILABLE:
        return {
            "success": False,
            "error": "Vanna AI未安装"
        }
    
    try:
        adapter = get_vanna_mcp_adapter()
        result = await adapter.train_ddl_preview(schema)
        return result
        
    except Exception as e:
        logger.error(f"DDL训练预览失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def vanna_train_documentation(documentation: str) -> Dict[str, Any]:
    """
    预览文档训练 - 需要用户确认后才执行
    
    提供业务术语、字段含义等文档，帮助Vanna更好地理解你的数据。
    需要使用vanna_confirm_training确认后才会实际训练。
    
    Args:
        documentation: 业务文档或数据说明
                      例如: "customer_type字段表示客户类型，1代表个人，2代表企业"
        
    Returns:
        训练预览结果和会话ID
        
    示例:
        1. vanna_train_documentation(documentation="buildings表存储建筑物信息")
        2. 检查返回的信息
        3. vanna_confirm_training(session_id="training_xxx")
    """
    if not VANNA_AVAILABLE:
        return {
            "success": False,
            "error": "Vanna AI未安装"
        }
    
    try:
        adapter = get_vanna_mcp_adapter()
        result = await adapter.train_documentation_preview(documentation)
        return result
        
    except Exception as e:
        logger.error(f"文档训练预览失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def vanna_train_sql_example(
    question: str,
    sql: str
) -> Dict[str, Any]:
    """
    预览SQL示例训练 - 需要用户确认后才执行
    
    提供问题和对应的SQL查询示例，Vanna会学习这种模式。
    需要使用vanna_confirm_training确认后才会实际训练。
    
    Args:
        question: 自然语言问题
        sql: 对应的SQL查询
        
    Returns:
        训练预览结果和会话ID
        
    示例:
        1. vanna_train_sql_example(question="查询所有高度超过100米的建筑",
                                    sql="SELECT * FROM buildings WHERE height > 100")
        2. 检查SQL正确性
        3. vanna_confirm_training(session_id="training_xxx")
    """
    if not VANNA_AVAILABLE:
        return {
            "success": False,
            "error": "Vanna AI未安装"
        }
    
    try:
        adapter = get_vanna_mcp_adapter()
        result = await adapter.train_sql_example_preview(question, sql)
        return result
        
    except Exception as e:
        logger.error(f"SQL示例训练预览失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def vanna_generate_sql(
    question: str,
    allow_llm_to_see_data: bool = False
) -> Dict[str, Any]:
    """
    使用Vanna AI生成SQL查询(带预览)
    
    基于训练的模型，将自然语言问题转换为SQL查询。
    生成的SQL会返回给你预览，需要使用execute_sql工具并设置confirmed=True来执行。
    
    Args:
        question: 自然语言问题
        allow_llm_to_see_data: 是否允许查看数据样本以提高准确性
        
    Returns:
        生成的SQL和会话ID
        
    示例:
        1. vanna_generate_sql(question="统计每个城市的建筑数量")
        2. 检查返回的SQL
        3. execute_sql(sql="...", confirmed=True)
        
    注意:
        - allow_llm_to_see_data=True会提高准确性但可能涉及隐私
    """
    if not VANNA_AVAILABLE:
        return {
            "success": False,
            "error": "Vanna AI未安装"
        }
    
    try:
        adapter = get_vanna_mcp_adapter()
        result = await adapter.generate_sql_with_preview(question, allow_llm_to_see_data)
        return result
        
    except Exception as e:
        logger.error(f"Vanna SQL生成失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def vanna_ask(
    question: str,
    auto_train: bool = True,
    visualize: bool = False
) -> Dict[str, Any]:
    """
    完整的Vanna AI问答流程
    
    一站式操作：生成SQL -> 执行查询 -> 返回结果 -> (可选)生成图表
    
    Args:
        question: 自然语言问题
        auto_train: 成功的查询是否自动加入训练数据
        visualize: 是否生成数据可视化图表
        
    Returns:
        包含SQL、数据结果和图表(如果启用)的完整响应
        
    示例:
        vanna_ask(
            question="最近一个月销售额最高的5个产品",
            auto_train=True,
            visualize=True
        )
        
    注意:
        - 此工具会直接执行SQL，请确保模型已充分训练
        - auto_train=True会持续改进模型
        - visualize=True会生成Plotly图表
    """
    if not VANNA_AVAILABLE:
        return {
            "success": False,
            "error": "Vanna AI未安装"
        }
    
    try:
        adapter = get_vanna_mcp_adapter()
        # 只生成SQL，不执行（避免超时）
        sql_result = await adapter.generate_sql_with_preview(question, allow_llm_to_see_data=True)
        
        if not sql_result.get('success'):
            return sql_result
        
        sql = sql_result.get('generated_sql')
        
        return {
            "success": True,
            "question": question,
            "generated_sql": sql,
            "message": "SQL已生成。请使用execute_sql工具执行此SQL，记得设置confirmed=True",
            "warning": "⚠️ 为避免超时，vanna_ask现在只生成SQL不执行。请检查SQL后使用execute_sql工具执行。"
        }
        
    except Exception as e:
        logger.error(f"Vanna问答失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def vanna_get_training_data() -> Dict[str, Any]:
    """
    获取Vanna模型的训练数据
    
    查看当前模型已学习的所有训练数据，包括DDL、文档和SQL示例。
    
    Returns:
        训练数据列表和数量
        
    示例:
        vanna_get_training_data()
    """
    if not VANNA_AVAILABLE:
        return {
            "success": False,
            "error": "Vanna AI未安装"
        }
    
    try:
        adapter = get_vanna_mcp_adapter()
        result = await adapter.get_training_data()
        return result
        
    except Exception as e:
        logger.error(f"获取训练数据失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def vanna_remove_training_data(id: str) -> Dict[str, Any]:
    """
    删除指定的训练数据
    
    如果某个训练数据不准确或不再需要，可以删除它。
    
    Args:
        id: 训练数据ID(从vanna_get_training_data获取)
        
    Returns:
        删除结果
        
    示例:
        vanna_remove_training_data(id="training_123")
    """
    if not VANNA_AVAILABLE:
        return {
            "success": False,
            "error": "Vanna AI未安装"
        }
    
    try:
        adapter = get_vanna_mcp_adapter()
        result = await adapter.remove_training_data(id)
        return result
        
    except Exception as e:
        logger.error(f"删除训练数据失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def vanna_confirm_training(session_id: str) -> Dict[str, Any]:
    """
    确认并执行训练
    
    用于确认之前创建的训练会话，实际执行训练操作。
    
    Args:
        session_id: 训练会话ID(从训练预览工具返回)
        
    Returns:
        训练执行结果
        
    示例:
        vanna_confirm_training(session_id="training_1")
    """
    if not VANNA_AVAILABLE:
        return {
            "success": False,
            "error": "Vanna AI未安装"
        }
    
    try:
        adapter = get_vanna_mcp_adapter()
        result = await adapter.confirm_training(session_id)
        return result
        
    except Exception as e:
        logger.error(f"确认训练失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def vanna_cancel_training(session_id: str) -> Dict[str, Any]:
    """
    取消训练会话
    
    取消之前创建的训练会话，不执行训练。
    
    Args:
        session_id: 训练会话ID
        
    Returns:
        取消结果
        
    示例:
        vanna_cancel_training(session_id="training_1")
    """
    if not VANNA_AVAILABLE:
        return {
            "success": False,
            "error": "Vanna AI未安装"
        }
    
    try:
        adapter = get_vanna_mcp_adapter()
        result = await adapter.cancel_training(session_id)
        return result
        
    except Exception as e:
        logger.error(f"取消训练失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============= 资源(Resources) =============

@mcp.resource("yukon://database/info")
async def get_database_info() -> str:
    """
    获取数据库基本信息资源
    
    Returns:
        数据库信息的 JSON 字符串
    """
    try:
        import json
        result = await get_postgis_version()
        extensions = await list_installed_extensions()
        
        info = {
            "database": db_config.database,
            "host": db_config.host,
            "port": db_config.port,
            "postgis_version": result,
            "extensions": extensions
        }
        return json.dumps(info, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取数据库信息失败: {str(e)}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.resource("yukon://database/{schema}")
async def get_database_schema(schema: str) -> str:
    """
    获取指定模式下的空间表列表
    
    Args:
        schema: 数据库模式名
        
    Returns:
        表列表的 JSON 字符串
    """
    try:
        import json
        tables = await list_spatial_tables(schema)
        return json.dumps({
            "schema": schema,
            "tables": tables
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取表列表失败: {str(e)}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.resource("yukon://database/{schema}/{table_name}/info")
async def get_table_info_resource(schema: str, table_name: str) -> str:
    """
    获取表的详细信息
    
    Args:
        schema: 数据库模式名
        table_name: 表名
        
    Returns:
        表信息的 JSON 字符串
    """
    try:
        import json
        info = await get_table_spatial_info(table_name, schema)
        return json.dumps(info, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取表信息失败: {str(e)}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.resource("yukon://database/{schema}/{table_name}/extent")
async def get_table_extent_resource(schema: str, table_name: str) -> str:
    """
    获取表的空间范围
     
    Args:
        schema: 数据库模式名
        table_name: 表名 
         
    Returns:
        空间范围的 JSON 字符串
    """
    try: 
        import json
        # 默认使用 geom 作为几何列名
        extent = await get_spatial_extent(table_name, "geom", schema)
        return json.dumps(extent, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取空间范围失败: {str(e)}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.resource("yukon://formats/supported")
async def get_supported_formats_resource() -> str:
    """
    获取支持的数据格式列表
    
    Returns:
        支持格式的 JSON 字符串
    """
    try:
        import json
        formats = await list_supported_formats()
        return json.dumps(formats, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取支持格式失败: {str(e)}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============= 提示(Prompts) =============

@mcp.prompt(
    name="analyze_spatial_data",
    title="分析空间数据",
    description="分析指定表的空间数据，生成统计报告"
)
async def analyze_spatial_data_prompt(schema: str = "public", table_name: str = "") -> list:
    """
    生成空间数据分析提示
    
    Args:
        schema: 数据库模式名
        table_name: 表名
        
    Returns:
        消息列表
    """
    try:
        if not table_name:
            tables = await list_spatial_tables(schema)
            table_list = "\n".join([f"- {t['table_name']}" for t in tables])
            return [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"数据库模式 '{schema}' 中有以下空间表:\n{table_list}\n\n请选择一个表进行分析。"
                    }
                }
            ]
        
        info = await get_table_spatial_info(table_name, schema)
        extent = await get_spatial_extent(table_name, info.get('geometry_columns', [{}])[0].get('column_name', 'geom'), schema)
        
        analysis_text = f"""请分析以下空间数据表的信息:

表名: {schema}.{table_name}
几何类型: {info.get('geometry_columns', [{}])[0].get('type', 'Unknown')}
坐标系统: EPSG:{info.get('geometry_columns', [{}])[0].get('srid', 'Unknown')}
要素数量: {info.get('row_count', 0)}

空间范围:
- 最小X: {extent.get('bounds', [0,0,0,0])[0]}
- 最小Y: {extent.get('bounds', [0,0,0,0])[1]}
- 最大X: {extent.get('bounds', [0,0,0,0])[2]}
- 最大Y: {extent.get('bounds', [0,0,0,0])[3]}

索引信息:
{chr(10).join([f"- {idx['name']}: {idx['type']}" for idx in info.get('indexes', [])])}

请基于这些信息:
1. 评估数据的空间分布特征
2. 建议可能的空间分析方法
3. 指出数据质量问题(如果有)
4. 推荐优化建议
"""
        
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": analysis_text
                }
            }
        ]
    except Exception as e:
        logger.error(f"生成分析提示失败: {str(e)}")
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"生成分析提示时出错: {str(e)}"
                }
            }
        ]


@mcp.prompt(
    name="import_data_guide",
    title="数据导入指南",
    description="提供数据导入的交互式指导"
)
async def import_data_guide_prompt(file_type: str = "") -> list:
    """
    生成数据导入指南提示
    
    Args:
        file_type: 文件类型 (shapefile, geojson, geotiff, png)
        
    Returns:
        消息列表
    """
    formats = await list_supported_formats()
    
    if not file_type:
        format_text = "支持的矢量格式:\n"
        for fmt_name, fmt_info in formats.get('vector_formats', {}).items():
            format_text += f"- {fmt_info['description']} ({fmt_info['extension']})\n"
        
        format_text += "\n支持的栅格格式:\n"
        for fmt_name, fmt_info in formats.get('raster_formats', {}).items():
            format_text += f"- {fmt_info['description']} ({fmt_info['extension']})\n"
        
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"""PostGIS 数据导入指南

{format_text}

请告诉我您要导入哪种格式的数据，我会为您提供详细的导入步骤。"""
                }
            }
        ]
    
    guides = {
        "shapefile": """Shapefile 导入步骤:

1. 准备文件: 确保 .shp, .shx, .dbf, .prj 等文件都在同一目录
2. 使用工具: import_shp
3. 必需参数:
   - file_path: .shp 文件的完整路径
   - table_name: 目标表名
4. 可选参数:
   - schema: 数据库模式 (默认: public)
   - srid: 坐标系统 (默认: 4326)
   - if_exists: 表存在时的处理 (replace/append/fail)

示例:
```python
result = await import_shp(
    file_path="/path/to/data.shp",
    table_name="my_table",
    srid=4326
)
```""",
        "geojson": """GeoJSON 导入步骤:

1. 准备文件或数据字符串
2. 使用工具: import_geojson_file
3. 必需参数 (二选一):
   - file_path: GeoJSON 文件路径
   - geojson_data: GeoJSON 字符串
4. 其他参数:
   - table_name: 目标表名
   - schema: 数据库模式
   - srid: 坐标系统

示例:
```python
result = await import_geojson_file(
    file_path="/path/to/data.geojson",
    table_name="my_geojson_table"
)
```""",
        "geotiff": """GeoTIFF 导入步骤:

1. 准备 GeoTIFF 文件 (带地理参考信息)
2. 使用工具: import_tif
3. 必需参数:
   - file_path: GeoTIFF 文件路径
   - table_name: 目标表名
4. 可选参数:
   - srid: 目标坐标系统 (默认使用文件原始坐标系)
   - tile_size: 瓦片大小 (默认: 256)

示例:
```python
result = await import_tif(
    file_path="/path/to/raster.tif",
    table_name="my_raster"
)
```""",
        "png": """PNG 导入步骤:

1. 准备 PNG 图像和地理边界信息
2. 使用工具: import_png
3. 必需参数:
   - file_path: PNG 文件路径
   - table_name: 目标表名
   - bounds: [minx, miny, maxx, maxy] 地理边界
4. 可选参数:
   - srid: 坐标系统 (默认: 4326)

示例:
```python
result = await import_png(
    file_path="/path/to/image.png",
    table_name="my_image",
    bounds=[120.0, 30.0, 121.0, 31.0]
)
```"""
    }
    
    guide_text = guides.get(file_type.lower(), f"不支持的文件类型: {file_type}")
    
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": guide_text
            }
        }
    ]


@mcp.prompt(
    name="spatial_query_builder",
    title="空间查询构建器",
    description="帮助构建复杂的空间查询"
)
async def spatial_query_builder_prompt(query_type: str = "") -> list:
    """
    生成空间查询构建提示
    
    Args:
        query_type: 查询类型 (nearby, bbox, intersection, buffer)
        
    Returns:
        消息列表
    """
    query_guides = {
        "nearby": """附近查询 (Nearby Query)

查找指定位置附近的要素。

工具: query_nearby

参数:
- longitude: 经度
- latitude: 纬度
- radius: 搜索半径(米)
- table_name: 表名
- geometry_column: 几何列名 (默认: geom)
- limit: 结果数量限制 (默认: 100)

示例场景:
- 查找我附近500米内的餐厅
- 找出距离某个点1公里内的所有设施

示例:
```python
results = await query_nearby(
    longitude=120.15,
    latitude=30.25,
    radius=500,
    table_name="restaurants"
)
```""",
        "bbox": """边界框查询 (Bounding Box Query)

查找在指定矩形区域内的所有要素。

工具: query_bbox

参数:
- min_x, min_y: 左下角坐标
- max_x, max_y: 右上角坐标
- table_name: 表名
- geometry_column: 几何列名
- limit: 结果数量限制

示例场景:
- 获取地图当前可视区域内的所有数据
- 批量导出某个区域的数据

示例:
```python
results = await query_bbox(
    min_x=120.0,
    min_y=30.0,
    max_x=121.0,
    max_y=31.0,
    table_name="buildings"
)
```""",
        "intersection": """相交分析 (Intersection Analysis)

检查两个几何对象是否相交，并获取相交部分。

工具: test_intersection

参数:
- geom1_wkt: 第一个几何对象 (WKT格式)
- geom2_wkt: 第二个几何对象 (WKT格式)
- srid: 坐标系统

示例场景:
- 检查建筑物是否在洪水淹没区内
- 分析道路与规划区域的交叉情况

示例:
```python
result = await test_intersection(
    geom1_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
    geom2_wkt="POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))",
    srid=4326
)
```""",
        "buffer": """缓冲区分析 (Buffer Analysis)

为几何对象创建指定距离的缓冲区。

工具: buffer_geometry

参数:
- geometry_wkt: 几何对象 (WKT格式)
- distance: 缓冲距离(米)
- srid: 坐标系统

示例场景:
- 创建河流两侧的保护区
- 分析道路周边影响范围

示例:
```python
result = await buffer_geometry(
    geometry_wkt="POINT(120.15 30.25)",
    distance=100,
    srid=4326
)
```"""
    }
    
    if not query_type:
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"""空间查询类型:

1. nearby - 附近查询
2. bbox - 边界框查询
3. intersection - 相交分析
4. buffer - 缓冲区分析

请告诉我您想了解哪种查询类型，我会提供详细的使用指南。"""
                }
            }
        ]
    
    guide = query_guides.get(query_type.lower(), f"不支持的查询类型: {query_type}")
    
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": guide
            }
        }
    ]


# Vanna服务进程
vanna_service_process: Optional[subprocess.Popen] = None


def check_vanna_service_health(base_url: str = "http://localhost:5000", timeout: int = 5) -> bool:
    """
    检查Vanna服务健康状态
    
    Args:
        base_url: Vanna服务基础URL
        timeout: 超时时间(秒)
        
    Returns:
        服务是否健康
    """
    try:
        response = requests.get(f"{base_url}/health", timeout=timeout)
        return response.status_code == 200 and response.json().get('status') == 'ok'
    except Exception as e:
        logger.debug(f"Vanna服务健康检查失败: {str(e)}")
        return False


def start_vanna_service() -> bool:
    """
    启动Vanna服务
    
    Returns:
        是否成功启动
    """
    global vanna_service_process
    
    # 检查是否启用Vanna服务
    enable_vanna = os.getenv('ENABLE_VANNA_SERVICE', 'false').lower() == 'true'
    if not enable_vanna:
        logger.info("Vanna服务未启用(设置 ENABLE_VANNA_SERVICE=true 启用)")
        return True
    
    # 检查服务是否已运行
    if check_vanna_service_health():
        logger.info("检测到Vanna服务已运行")
        return True
    
    # 获取Vanna服务脚本路径
    vanna_service_path = Path(__file__).parent / "vanna_server" / "vanna_service.py"
    
    if not vanna_service_path.exists():
        logger.warning(f"Vanna服务脚本不存在: {vanna_service_path}")
        return False
    
    try:
        logger.info("正在启动Vanna服务...")
        
        # 启动Vanna服务作为子进程
        vanna_service_process = subprocess.Popen(
            [sys.executable, str(vanna_service_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # 等待服务启动
        max_wait = 30
        wait_interval = 1
        for i in range(max_wait):
            if check_vanna_service_health():
                logger.info(f"✓ Vanna服务启动成功 (耗时 {i+1}秒)")
                return True
            time.sleep(wait_interval)
        
        logger.error(f"Vanna服务启动超时({max_wait}秒)")
        return False
        
    except Exception as e:
        logger.error(f"启动Vanna服务失败: {str(e)}")
        return False


def stop_vanna_service():
    """停止Vanna服务"""
    global vanna_service_process
    
    if vanna_service_process:
        logger.info("正在停止Vanna服务...")
        try:
            vanna_service_process.terminate()
            vanna_service_process.wait(timeout=5)
            logger.info("✓ Vanna服务已停止")
        except subprocess.TimeoutExpired:
            logger.warning("Vanna服务终止超时，强制结束")
            vanna_service_process.kill()
        except Exception as e:
            logger.error(f"停止Vanna服务失败: {str(e)}")


def main():
    """启动 MCP 服务器"""
    import sys
    
    # 对于MCP客户端(如Cherry Studio)，不要输出日志到stdout
    # 因为stdout用于MCP协议通信
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # 禁用控制台日志输出，只记录到文件
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                logging.root.removeHandler(handler)
    
    logger.info("启动 PostGIS MCP 服务器...")
    
    # 启动Vanna服务(如果启用)
    try:
        if not start_vanna_service():
            logger.warning("Vanna服务启动失败，但MCP服务器将继续启动")
    except Exception as e:
        logger.error(f"启动Vanna服务时发生错误: {str(e)}")
    
    # 初始化数据库连接池
    try:
        logger.info("正在初始化数据库连接...")
        db_config.initialize_pool()
        
        # 测试数据库连接
        if db_config.test_connection():
            logger.info("数据库连接成功!")
        else:
            logger.warning("数据库连接测试失败，但服务器将继续启动")
    except Exception as e:
        logger.error(f"初始化数据库连接失败: {str(e)}")
        logger.warning("服务器将在没有数据库连接的情况下启动")
    
    # 启动 MCP 服务器 - 使用stdio传输
    try:
        mcp.run(transport='stdio')
    finally:
        # 停止Vanna服务
        stop_vanna_service()
        
        # 关闭所有数据库连接
        logger.info("正在关闭数据库连接...")
        db_config.close_all_connections()


if __name__ == "__main__":
    main()