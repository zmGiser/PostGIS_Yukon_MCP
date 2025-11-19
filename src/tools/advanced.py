"""
高级空间分析工具模块
提供高级的 PostGIS 空间分析功能
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


async def spatial_join(
    table1: str,
    table2: str,
    geom_col1: str = "geom",
    geom_col2: str = "geom",
    join_type: str = "intersects",
    schema: str = "public"
) -> List[Dict[str, Any]]:
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
        空间连接结果列表
    """
    conn = await get_db_connection()
    try:
        # 根据连接类型构建查询
        spatial_predicates = {
            "intersects": "ST_Intersects",
            "contains": "ST_Contains",
            "within": "ST_Within",
            "touches": "ST_Touches",
            "overlaps": "ST_Overlaps"
        }
        
        predicate = spatial_predicates.get(join_type.lower(), "ST_Intersects")
        
        query = f"""
            SELECT 
                t1.*,
                t2.*
            FROM {schema}.{table1} t1
            JOIN {schema}.{table2} t2
            ON {predicate}(t1.{geom_col1}, t2.{geom_col2})
            LIMIT 100
        """
        
        rows = await conn.fetch(query)
        
        results = []
        for row in rows:
            result = dict(row)
            # 转换几何字段为字符串
            if geom_col1 in result:
                result[geom_col1] = str(result[geom_col1])
            if geom_col2 in result:
                result[geom_col2] = str(result[geom_col2])
            results.append(result)
        
        logger.info(f"空间连接完成: {len(results)} 条结果")
        return results
        
    except Exception as e:
        logger.error(f"空间连接失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def nearest_neighbor(
    point_wkt: str,
    table_name: str,
    geometry_column: str = "geom",
    k: int = 5,
    max_distance: Optional[float] = None,
    schema: str = "public",
    srid: int = 4326
) -> List[Dict[str, Any]]:
    """
    查找最近的K个邻居
    
    Args:
        point_wkt: 查询点的WKT格式
        table_name: 表名
        geometry_column: 几何列名
        k: 返回的邻居数量
        max_distance: 最大搜索距离（米），None表示无限制
        schema: 模式名
        srid: 空间参考系统ID
        
    Returns:
        最近邻居列表
    """
    conn = await get_db_connection()
    try:
        distance_filter = ""
        if max_distance is not None:
            distance_filter = f"""
                AND ST_DWithin(
                    ST_Transform({geometry_column}, 4326)::geography,
                    ST_GeogFromText('SRID=4326;{point_wkt}'),
                    {max_distance}
                )
            """
        
        query = f"""
            SELECT 
                *,
                ST_Distance(
                    ST_Transform({geometry_column}, 4326)::geography,
                    ST_GeogFromText('SRID=4326;{point_wkt}')
                ) as distance
            FROM {schema}.{table_name}
            WHERE {geometry_column} IS NOT NULL
            {distance_filter}
            ORDER BY {geometry_column} <-> ST_GeomFromText('{point_wkt}', {srid})
            LIMIT {k}
        """
        
        rows = await conn.fetch(query)
        
        results = []
        for row in rows:
            result = dict(row)
            if geometry_column in result:
                result[geometry_column] = str(result[geometry_column])
            results.append(result)
        
        logger.info(f"找到 {len(results)} 个最近邻居")
        return results
        
    except Exception as e:
        logger.error(f"最近邻查询失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def spatial_cluster(
    table_name: str,
    geometry_column: str = "geom",
    distance: float = 100,
    min_points: int = 5,
    schema: str = "public"
) -> Dict[str, Any]:
    """
    使用 ST_ClusterDBSCAN 进行空间聚类
    
    Args:
        table_name: 表名
        geometry_column: 几何列名
        distance: 聚类距离阈值（米）
        min_points: 最小点数
        schema: 模式名
        
    Returns:
        聚类结果字典
    """
    conn = await get_db_connection()
    try:
        query = f"""
            WITH clustered AS (
                SELECT 
                    *,
                    ST_ClusterDBSCAN(
                        ST_Transform({geometry_column}, 3857),
                        eps := {distance},
                        minpoints := {min_points}
                    ) OVER () AS cluster_id
                FROM {schema}.{table_name}
                WHERE {geometry_column} IS NOT NULL
            )
            SELECT 
                cluster_id,
                COUNT(*) as point_count,
                ST_AsText(ST_Centroid(ST_Collect({geometry_column}))) as cluster_centroid
            FROM clustered
            WHERE cluster_id IS NOT NULL
            GROUP BY cluster_id
            ORDER BY cluster_id
        """
        
        rows = await conn.fetch(query)
        
        clusters = []
        for row in rows:
            clusters.append({
                "cluster_id": row["cluster_id"],
                "point_count": row["point_count"],
                "centroid": row["cluster_centroid"]
            })
        
        logger.info(f"识别出 {len(clusters)} 个聚类")
        
        return {
            "cluster_count": len(clusters),
            "clusters": clusters
        }
        
    except Exception as e:
        logger.error(f"空间聚类失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def convex_hull(
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
        凸包信息字典
    """
    conn = await get_db_connection()
    try:
        query = f"""
            SELECT 
                ST_AsText(ST_ConvexHull(ST_Collect({geometry_column}))) as convex_hull,
                ST_Area(ST_Transform(ST_ConvexHull(ST_Collect({geometry_column})), 3857)) as area_sqm,
                COUNT(*) as feature_count
            FROM {schema}.{table_name}
            WHERE {geometry_column} IS NOT NULL
        """
        
        row = await conn.fetchrow(query)
        
        result = {
            "convex_hull_wkt": row["convex_hull"],
            "area_square_meters": float(row["area_sqm"]),
            "feature_count": row["feature_count"]
        }
        
        logger.info(f"计算凸包: 包含 {result['feature_count']} 个要素")
        return result
        
    except Exception as e:
        logger.error(f"计算凸包失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def voronoi_polygons(
    table_name: str,
    geometry_column: str = "geom",
    schema: str = "public"
) -> List[Dict[str, Any]]:
    """
    生成 Voronoi 多边形
    
    Args:
        table_name: 表名
        geometry_column: 几何列名
        schema: 模式名
        
    Returns:
        Voronoi 多边形列表
    """
    conn = await get_db_connection()
    try:
        query = f"""
            SELECT 
                (ST_Dump(ST_VoronoiPolygons(ST_Collect({geometry_column})))).geom as voronoi_polygon
            FROM {schema}.{table_name}
            WHERE {geometry_column} IS NOT NULL
        """
        
        rows = await conn.fetch(query)
        
        results = []
        for i, row in enumerate(rows):
            results.append({
                "polygon_id": i,
                "geometry": str(row["voronoi_polygon"])
            })
        
        logger.info(f"生成 {len(results)} 个 Voronoi 多边形")
        return results
        
    except Exception as e:
        logger.error(f"生成 Voronoi 多边形失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def line_interpolate(
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
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_AsText(ST_LineInterpolatePoint(ST_GeomFromText($1, $2), $3)) as point_wkt,
                ST_X(ST_LineInterpolatePoint(ST_GeomFromText($1, $2), $3)) as longitude,
                ST_Y(ST_LineInterpolatePoint(ST_GeomFromText($1, $2), $3)) as latitude
        """
        
        row = await conn.fetchrow(query, line_wkt, srid, fraction)
        
        result = {
            "point_wkt": row["point_wkt"],
            "longitude": float(row["longitude"]),
            "latitude": float(row["latitude"]),
            "fraction": fraction
        }
        
        logger.info(f"线段插值点: ({result['longitude']}, {result['latitude']})")
        return result
        
    except Exception as e:
        logger.error(f"线段插值失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def snap_to_grid(
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
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_AsText(ST_SnapToGrid(ST_GeomFromText($1, $2), $3)) as snapped_geom,
                ST_NPoints(ST_GeomFromText($1, $2)) as original_points,
                ST_NPoints(ST_SnapToGrid(ST_GeomFromText($1, $2), $3)) as snapped_points
        """
        
        row = await conn.fetchrow(query, geometry_wkt, srid, grid_size)
        
        result = {
            "snapped_geometry": row["snapped_geom"],
            "original_point_count": row["original_points"],
            "snapped_point_count": row["snapped_points"],
            "grid_size": grid_size
        }
        
        logger.info(f"捕捉到网格: {result['original_point_count']} -> {result['snapped_point_count']} 点")
        return result
        
    except Exception as e:
        logger.error(f"捕捉到网格失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def split_line_by_point(
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
    conn = await get_db_connection()
    try:
        query = """
            SELECT 
                ST_AsText(ST_Split(
                    ST_GeomFromText($1, $2),
                    ST_GeomFromText($3, $2)
                )) as split_result
        """
        
        row = await conn.fetchrow(query, line_wkt, srid, point_wkt)
        
        result = {
            "split_geometry": row["split_result"]
        }
        
        logger.info("线段分割完成")
        return result
        
    except Exception as e:
        logger.error(f"线段分割失败: {str(e)}")
        raise
    finally:
        await conn.close()