"""
几何操作工具模块
提供基于 PostGIS 的几何操作功能
"""
from typing import Dict, Any, Optional
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


async def create_buffer(
    geometry_wkt: str,
    distance: float,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    创建几何缓冲区
    
    Args:
        geometry_wkt: WKT格式的几何对象
        distance: 缓冲距离（米）
        srid: 空间参考系统ID
        
    Returns:
        包含缓冲区几何的字典
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_AsText(
                    ST_Transform(
                        ST_Buffer(
                            ST_Transform(ST_GeomFromText($1, $2), 3857),
                            $3
                        ),
                        $2
                    )
                ) as buffer_geom,
                ST_Area(
                    ST_Transform(
                        ST_Buffer(
                            ST_Transform(ST_GeomFromText($1, $2), 3857),
                            $3
                        ),
                        3857
                    )
                ) as area
        """
        
        row = await conn.fetchrow(query, geometry_wkt, srid, distance)
        
        result = {
            "buffer_geometry": row["buffer_geom"],
            "area_sqm": float(row["area"])
        }
        
        logger.info(f"创建缓冲区成功，面积: {result['area_sqm']} 平方米")
        return result
        
    except Exception as e:
        logger.error(f"创建缓冲区失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def calculate_area(
    geometry_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    计算几何面积
    
    Args:
        geometry_wkt: WKT格式的几何对象
        srid: 空间参考系统ID
        
    Returns:
        包含面积信息的字典
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_Area(ST_Transform(ST_GeomFromText($1, $2), 3857)) as area_sqm,
                ST_Area(ST_Transform(ST_GeomFromText($1, $2), 3857)) / 1000000.0 as area_sqkm
        """
        
        row = await conn.fetchrow(query, geometry_wkt, srid)
        
        result = {
            "area_square_meters": float(row["area_sqm"]),
            "area_square_kilometers": float(row["area_sqkm"])
        }
        
        logger.info(f"计算面积: {result['area_square_meters']} 平方米")
        return result
        
    except Exception as e:
        logger.error(f"计算面积失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def calculate_length(
    geometry_wkt: str,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    计算几何长度
    
    Args:
        geometry_wkt: WKT格式的几何对象
        srid: 空间参考系统ID
        
    Returns:
        包含长度信息的字典
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_Length(ST_Transform(ST_GeomFromText($1, $2), 3857)) as length_m,
                ST_Length(ST_Transform(ST_GeomFromText($1, $2), 3857)) / 1000.0 as length_km
        """
        
        row = await conn.fetchrow(query, geometry_wkt, srid)
        
        result = {
            "length_meters": float(row["length_m"]),
            "length_kilometers": float(row["length_km"])
        }
        
        logger.info(f"计算长度: {result['length_meters']} 米")
        return result
        
    except Exception as e:
        logger.error(f"计算长度失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def transform_geometry(
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
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_AsText(ST_Transform(ST_GeomFromText($1, $2), $3)) as transformed_geom
        """
        
        row = await conn.fetchrow(query, geometry_wkt, from_srid, to_srid)
        
        result = {
            "transformed_geometry": row["transformed_geom"],
            "from_srid": from_srid,
            "to_srid": to_srid
        }
        
        logger.info(f"坐标系统转换成功: {from_srid} -> {to_srid}")
        return result
        
    except Exception as e:
        logger.error(f"坐标系统转换失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def simplify_geometry(
    geometry_wkt: str,
    tolerance: float,
    srid: int = 4326
) -> Dict[str, Any]:
    """
    简化几何对象
    
    Args:
        geometry_wkt: WKT格式的几何对象
        tolerance: 简化容差
        srid: 空间参考系统ID
        
    Returns:
        包含简化后几何的字典
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_AsText(ST_Simplify(ST_GeomFromText($1, $2), $3)) as simplified_geom,
                ST_NPoints(ST_GeomFromText($1, $2)) as original_points,
                ST_NPoints(ST_Simplify(ST_GeomFromText($1, $2), $3)) as simplified_points
        """
        
        row = await conn.fetchrow(query, geometry_wkt, srid, tolerance)
        
        result = {
            "simplified_geometry": row["simplified_geom"],
            "original_point_count": row["original_points"],
            "simplified_point_count": row["simplified_points"],
            "reduction_ratio": 1 - (row["simplified_points"] / row["original_points"])
        }
        
        logger.info(
            f"简化几何成功: {result['original_point_count']} -> "
            f"{result['simplified_point_count']} 点"
        )
        return result
        
    except Exception as e:
        logger.error(f"简化几何失败: {str(e)}")
        raise
    finally:
        await conn.close()