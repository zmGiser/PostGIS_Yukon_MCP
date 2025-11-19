"""
空间查询工具模块
提供基于 PostGIS 的空间查询功能
"""
from typing import Dict, List, Any, Optional
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


async def query_nearby_features(
    longitude: float,
    latitude: float,
    radius: float,
    table_name: str,
    geometry_column: str = "geom",
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    查询指定坐标附近的地理要素
    
    Args:
        longitude: 经度
        latitude: 纬度
        radius: 搜索半径（米）
        table_name: 表名
        geometry_column: 几何列名
        limit: 返回结果数量限制
        
    Returns:
        查询结果列表
    """
    conn = await get_db_connection()
    try:
        # 创建点几何
        point_wkt = f"POINT({longitude} {latitude})"
        
        # 构建查询SQL
        query = f"""
            SELECT 
                *,
                ST_Distance(
                    ST_Transform({geometry_column}, 4326)::geography,
                    ST_GeogFromText('SRID=4326;{point_wkt}')
                ) as distance
            FROM {table_name}
            WHERE ST_DWithin(
                ST_Transform({geometry_column}, 4326)::geography,
                ST_GeogFromText('SRID=4326;{point_wkt}'),
                $1
            )
            ORDER BY distance
            LIMIT $2
        """
        
        rows = await conn.fetch(query, radius, limit)
        
        # 转换为字典列表
        results = []
        for row in rows:
            result = dict(row)
            # 处理几何字段
            if geometry_column in result:
                result[geometry_column] = str(result[geometry_column])
            results.append(result)
        
        logger.info(f"查询到 {len(results)} 个附近要素")
        return results
        
    except Exception as e:
        logger.error(f"查询附近要素失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def query_within_bbox(
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    table_name: str,
    geometry_column: str = "geom",
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    查询边界框内的地理要素
    
    Args:
        min_x: 最小经度
        min_y: 最小纬度
        max_x: 最大经度
        max_y: 最大纬度
        table_name: 表名
        geometry_column: 几何列名
        limit: 返回结果数量限制
        
    Returns:
        查询结果列表
    """
    conn = await get_db_connection()
    try:
        # 构建边界框
        bbox = f"POLYGON(({min_x} {min_y}, {max_x} {min_y}, {max_x} {max_y}, {min_x} {max_y}, {min_x} {min_y}))"
        
        query = f"""
            SELECT *
            FROM {table_name}
            WHERE ST_Intersects(
                ST_Transform({geometry_column}, 4326),
                ST_GeomFromText('SRID=4326;{bbox}')
            )
            LIMIT $1
        """
        
        rows = await conn.fetch(query, limit)
        
        results = []
        for row in rows:
            result = dict(row)
            if geometry_column in result:
                result[geometry_column] = str(result[geometry_column])
            results.append(result)
        
        logger.info(f"查询到 {len(results)} 个边界框内要素")
        return results
        
    except Exception as e:
        logger.error(f"查询边界框内要素失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def query_by_attribute(
    table_name: str,
    attribute_name: str,
    attribute_value: Any,
    geometry_column: str = "geom",
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    根据属性查询地理要素
    
    Args:
        table_name: 表名
        attribute_name: 属性名
        attribute_value: 属性值
        geometry_column: 几何列名
        limit: 返回结果数量限制
        
    Returns:
        查询结果列表
    """
    conn = await get_db_connection()
    try:
        query = f"""
            SELECT *
            FROM {table_name}
            WHERE {attribute_name} = $1
            LIMIT $2
        """
        
        rows = await conn.fetch(query, attribute_value, limit)
        
        results = []
        for row in rows:
            result = dict(row)
            if geometry_column in result:
                result[geometry_column] = str(result[geometry_column])
            results.append(result)
        
        logger.info(f"根据属性查询到 {len(results)} 个要素")
        return results
        
    except Exception as e:
        logger.error(f"根据属性查询要素失败: {str(e)}")
        raise
    finally:
        await conn.close()