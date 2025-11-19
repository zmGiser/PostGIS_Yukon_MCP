"""
空间分析工具模块
提供基于 PostGIS 的空间分析功能
"""
from typing import Dict, Any, List
import asyncpg
import logging

from ..config import db_config

logger = logging.getLogger(__name__)


async def get_db_connection() -> asyncpg.Connection:
    """
    获取数据库连接
    
    Returns:
        数据库连接对象
    """
    conn = await asyncpg.connect(
        host=db_config.host,
        port=db_config.port,
        database=db_config.database,
        user=db_config.user,
        password=db_config.password
    )
    return conn


async def calculate_distance(
    geom1_wkt: str,
    geom2_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    计算两个几何对象之间的距离
    
    Args:
        geom1_wkt: 第一个几何对象的WKT格式
        geom2_wkt: 第二个几何对象的WKT格式
        srid: 空间参考系统ID
        
    Returns:
        包含距离信息的字典
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_Distance(
                    ST_Transform(ST_GeomFromText($1, $2), 3857),
                    ST_Transform(ST_GeomFromText($3, $2), 3857)
                ) as distance_m,
                ST_Distance(
                    ST_Transform(ST_GeomFromText($1, $2), 3857),
                    ST_Transform(ST_GeomFromText($3, $2), 3857)
                ) / 1000.0 as distance_km
        """
        
        row = await conn.fetchrow(query, geom1_wkt, srid, geom2_wkt)
        
        result = {
            "distance_meters": float(row["distance_m"]),
            "distance_kilometers": float(row["distance_km"])
        }
        
        logger.info(f"计算距离: {result['distance_meters']} 米")
        return result
        
    except Exception as e:
        logger.error(f"计算距离失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def check_intersection(
    geom1_wkt: str,
    geom2_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    检查两个几何对象是否相交
    
    Args:
        geom1_wkt: 第一个几何对象的WKT格式
        geom2_wkt: 第二个几何对象的WKT格式
        srid: 空间参考系统ID
        
    Returns:
        包含相交信息的字典
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_Intersects(
                    ST_GeomFromText($1, $2),
                    ST_GeomFromText($3, $2)
                ) as intersects,
                CASE 
                    WHEN ST_Intersects(ST_GeomFromText($1, $2), ST_GeomFromText($3, $2))
                    THEN ST_AsText(
                        ST_Intersection(
                            ST_GeomFromText($1, $2),
                            ST_GeomFromText($3, $2)
                        )
                    )
                    ELSE NULL
                END as intersection_geom
        """
        
        row = await conn.fetchrow(query, geom1_wkt, srid, geom2_wkt)
        
        result = {
            "intersects": row["intersects"],
            "intersection_geometry": row["intersection_geom"] if row["intersects"] else None
        }
        
        logger.info(f"相交检查: {result['intersects']}")
        return result
        
    except Exception as e:
        logger.error(f"相交检查失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def check_containment(
    container_wkt: str,
    contained_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    检查一个几何对象是否包含另一个
    
    Args:
        container_wkt: 容器几何对象的WKT格式
        contained_wkt: 被包含几何对象的WKT格式
        srid: 空间参考系统ID
        
    Returns:
        包含包含关系信息的字典
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_Contains(
                    ST_GeomFromText($1, $2),
                    ST_GeomFromText($3, $2)
                ) as contains,
                ST_Within(
                    ST_GeomFromText($3, $2),
                    ST_GeomFromText($1, $2)
                ) as within
        """
        
        row = await conn.fetchrow(query, container_wkt, srid, contained_wkt)
        
        result = {
            "contains": row["contains"],
            "within": row["within"]
        }
        
        logger.info(f"包含关系检查: contains={result['contains']}, within={result['within']}")
        return result
        
    except Exception as e:
        logger.error(f"包含关系检查失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def union_geometries(
    geometries_wkt: List[str],
    srid: int = 4326
) -> Dict[str, Any]:
    """
    合并多个几何对象
    
    Args:
        geometries_wkt: WKT格式的几何对象列表
        srid: 空间参考系统ID
        
    Returns:
        包含合并后几何的字典
    """
    conn = await get_db_connection()
    try:
        # 构建几何集合
        geom_array = ", ".join([f"ST_GeomFromText('{wkt}', {srid})" for wkt in geometries_wkt])
        
        query = f"""
            SELECT 
                ST_AsText(ST_Union(ARRAY[{geom_array}])) as union_geom,
                ST_Area(ST_Transform(ST_Union(ARRAY[{geom_array}]), 3857)) as area_sqm
        """
        
        row = await conn.fetchrow(query)
        
        result = {
            "union_geometry": row["union_geom"],
            "area_square_meters": float(row["area_sqm"]) if row["area_sqm"] else None
        }
        
        logger.info(f"合并 {len(geometries_wkt)} 个几何对象")
        return result
        
    except Exception as e:
        logger.error(f"合并几何对象失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def calculate_centroid(
    geometry_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    计算几何对象的质心
    
    Args:
        geometry_wkt: WKT格式的几何对象
        srid: 空间参考系统ID
        
    Returns:
        包含质心坐标的字典
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_AsText(ST_Centroid(ST_GeomFromText($1, $2))) as centroid_wkt,
                ST_X(ST_Centroid(ST_GeomFromText($1, $2))) as longitude,
                ST_Y(ST_Centroid(ST_GeomFromText($1, $2))) as latitude
        """
        
        row = await conn.fetchrow(query, geometry_wkt, srid)
        
        result = {
            "centroid_geometry": row["centroid_wkt"],
            "longitude": float(row["longitude"]),
            "latitude": float(row["latitude"])
        }
        
        logger.info(f"计算质心: ({result['longitude']}, {result['latitude']})")
        return result
        
    except Exception as e:
        logger.error(f"计算质心失败: {str(e)}")
        raise
    finally:
        await conn.close()