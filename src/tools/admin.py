"""
PostGIS 扩展管理和数据库管理工具模块
提供 PostGIS 扩展管理、空间表发现和索引管理功能
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


async def get_postgis_version() -> Dict[str, Any]:
    """
    获取 PostGIS 版本信息
    
    Returns:
        包含版本信息的字典
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                PostGIS_Version() as postgis_version,
                PostGIS_Full_Version() as full_version,
                PostGIS_GEOS_Version() as geos_version,
                PostGIS_Proj_Version() as proj_version,
                PostGIS_Lib_Version() as lib_version
        """
        
        row = await conn.fetchrow(query)
        
        result = {
            "postgis_version": row["postgis_version"],
            "full_version": row["full_version"],
            "geos_version": row["geos_version"],
            "proj_version": row["proj_version"],
            "lib_version": row["lib_version"]
        }
        
        logger.info(f"PostGIS 版本: {result['postgis_version']}")
        return result
        
    except Exception as e:
        logger.error(f"获取 PostGIS 版本失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def list_installed_extensions() -> List[Dict[str, Any]]:
    """
    列出已安装的 PostGIS 相关扩展
    
    Returns:
        已安装的 PostGIS 相关扩展列表
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT
                name,
                default_version,
                installed_version,
                comment
            FROM pg_available_extensions
            WHERE installed_version IS NOT NULL
                AND (
                    name ILIKE '%postgis%'
                    OR name ILIKE '%gis%'
                    OR comment ILIKE '%GaussDB%'
                    OR installed_version ILIKE '%GaussDB%'
                )
            ORDER BY name
        """
        
        rows = await conn.fetch(query)
        
        results = []
        for row in rows:
            results.append({
                "name": row["name"],
                "default_version": row["default_version"],
                "installed_version": row["installed_version"],
                "comment": row["comment"]
            })
        
        logger.info(f"找到 {len(results)} 个 PostGIS 相关扩展")
        return results
        
    except Exception as e:
        logger.error(f"列出已安装扩展失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def list_spatial_tables(schema: str = "public") -> List[Dict[str, Any]]:
    """
    列出包含空间字段的表
    
    Args:
        schema: 数据库模式名，默认为 'public'
        
    Returns:
        包含空间字段的表列表
    """
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                f_table_schema as schema_name,
                f_table_name as table_name,
                f_geometry_column as geometry_column,
                coord_dimension as dimension,
                srid,
                type as geometry_type
            FROM geometry_columns
            WHERE f_table_schema = $1
            ORDER BY f_table_name, f_geometry_column
        """
        
        rows = await conn.fetch(query, schema)
        
        results = []
        for row in rows:
            results.append({
                "schema": row["schema_name"],
                "table": row["table_name"],
                "geometry_column": row["geometry_column"],
                "dimension": row["dimension"],
                "srid": row["srid"],
                "geometry_type": row["geometry_type"]
            })
        
        logger.info(f"在 {schema} 模式中找到 {len(results)} 个空间表")
        return results
        
    except Exception as e:
        logger.error(f"列出空间表失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def get_table_spatial_info(
    table_name: str,
    schema: str = "public"
) -> Dict[str, Any]:
    """
    获取表的详细空间信息
    
    Args:
        table_name: 表名
        schema: 模式名，默认为 'public'
        
    Returns:
        包含表空间信息的字典
    """
    conn = await get_db_connection()
    try:
        # 获取几何列信息
        geom_query = """
            SELECT 
                f_geometry_column,
                coord_dimension,
                srid,
                type as geometry_type
            FROM geometry_columns
            WHERE f_table_schema = $1 AND f_table_name = $2
        """
        
        geom_rows = await conn.fetch(geom_query, schema, table_name)
        
        # 获取表统计信息
        stats_query = f"""
            SELECT 
                COUNT(*) as row_count,
                pg_size_pretty(pg_total_relation_size($1 || '.' || $2)) as total_size
        """
        
        stats_row = await conn.fetchrow(stats_query, schema, table_name)
        
        # 获取索引信息
        index_query = """
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = $1 AND tablename = $2
        """
        
        index_rows = await conn.fetch(index_query, schema, table_name)
        
        result = {
            "schema": schema,
            "table": table_name,
            "row_count": stats_row["row_count"],
            "total_size": stats_row["total_size"],
            "geometry_columns": [dict(row) for row in geom_rows],
            "indexes": [
                {
                    "name": row["indexname"],
                    "definition": row["indexdef"]
                }
                for row in index_rows
            ]
        }
        
        logger.info(f"获取表 {schema}.{table_name} 的空间信息")
        return result
        
    except Exception as e:
        logger.error(f"获取表空间信息失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def create_spatial_index(
    table_name: str,
    geometry_column: str = "geom",
    schema: str = "public",
    index_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    为空间列创建 GIST 索引
    
    Args:
        table_name: 表名
        geometry_column: 几何列名，默认为 'geom'
        schema: 模式名，默认为 'public'
        index_name: 索引名称，如果不提供则自动生成
        
    Returns:
        包含索引创建信息的字典
    """
    conn = await get_db_connection()
    try:
        # 生成索引名称
        if index_name is None:
            index_name = f"idx_{table_name}_{geometry_column}_gist"
        
        # 检查索引是否已存在
        check_query = """
            SELECT COUNT(*) as count
            FROM pg_indexes
            WHERE schemaname = $1 AND tablename = $2 AND indexname = $3
        """
        
        check_row = await conn.fetchrow(check_query, schema, table_name, index_name)
        
        if check_row["count"] > 0:
            return {
                "success": False,
                "message": f"索引 {index_name} 已存在"
            }
        
        # 创建索引
        create_query = f"""
            CREATE INDEX {index_name}
            ON {schema}.{table_name}
            USING GIST ({geometry_column})
        """
        
        await conn.execute(create_query)
        
        logger.info(f"成功创建空间索引: {schema}.{table_name}.{index_name}")
        
        return {
            "success": True,
            "index_name": index_name,
            "table": f"{schema}.{table_name}",
            "column": geometry_column
        }
        
    except Exception as e:
        logger.error(f"创建空间索引失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def analyze_table(
    table_name: str,
    schema: str = "public"
) -> Dict[str, Any]:
    """
    分析表以更新统计信息
    
    Args:
        table_name: 表名
        schema: 模式名，默认为 'public'
        
    Returns:
        分析结果字典
    """
    conn = await get_db_connection()
    try:
        query = f"ANALYZE {schema}.{table_name}"
        
        await conn.execute(query)
        
        logger.info(f"成功分析表: {schema}.{table_name}")
        
        return {
            "success": True,
            "table": f"{schema}.{table_name}",
            "message": "表统计信息已更新"
        }
        
    except Exception as e:
        logger.error(f"分析表失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def vacuum_table(
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
        清理结果字典
    """
    conn = await get_db_connection()
    try:
        vacuum_type = "FULL" if full else ""
        query = f"VACUUM {vacuum_type} {schema}.{table_name}"
        
        await conn.execute(query)
        
        logger.info(f"成功清理表: {schema}.{table_name} (FULL={full})")
        
        return {
            "success": True,
            "table": f"{schema}.{table_name}",
            "full_vacuum": full,
            "message": "表空间已回收"
        }
        
    except Exception as e:
        logger.error(f"清理表失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def get_spatial_extent(
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
        空间范围信息字典
    """
    conn = await get_db_connection()
    try:
        query = f"""
            SELECT 
                ST_AsText(ST_Extent({geometry_column})) as extent,
                ST_XMin(ST_Extent({geometry_column})) as min_x,
                ST_YMin(ST_Extent({geometry_column})) as min_y,
                ST_XMax(ST_Extent({geometry_column})) as max_x,
                ST_YMax(ST_Extent({geometry_column})) as max_y,
                COUNT(*) as feature_count
            FROM {schema}.{table_name}
        """
        
        row = await conn.fetchrow(query)
        
        result = {
            "table": f"{schema}.{table_name}",
            "extent_wkt": row["extent"],
            "bbox": {
                "min_x": float(row["min_x"]) if row["min_x"] else None,
                "min_y": float(row["min_y"]) if row["min_y"] else None,
                "max_x": float(row["max_x"]) if row["max_x"] else None,
                "max_y": float(row["max_y"]) if row["max_y"] else None
            },
            "feature_count": row["feature_count"]
        }
        
        logger.info(f"获取表 {schema}.{table_name} 的空间范围")
        return result
        
    except Exception as e:
        logger.error(f"获取空间范围失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def check_geometry_validity(
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
    conn = await get_db_connection()
    try:
        query = f"""
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN ST_IsValid({geometry_column}) THEN 1 END) as valid_count,
                COUNT(CASE WHEN NOT ST_IsValid({geometry_column}) THEN 1 END) as invalid_count
            FROM {schema}.{table_name}
            WHERE {geometry_column} IS NOT NULL
        """
        
        row = await conn.fetchrow(query)
        
        result = {
            "table": f"{schema}.{table_name}",
            "total_geometries": row["total_count"],
            "valid_geometries": row["valid_count"],
            "invalid_geometries": row["invalid_count"],
            "validity_rate": (
                float(row["valid_count"]) / float(row["total_count"]) * 100
                if row["total_count"] > 0 else 0
            )
        }
        
        logger.info(
            f"几何有效性检查: {result['valid_geometries']}/{result['total_geometries']} 有效"
        )
        return result
        
    except Exception as e:
        logger.error(f"检查几何有效性失败: {str(e)}")
        raise
    finally:
        await conn.close()