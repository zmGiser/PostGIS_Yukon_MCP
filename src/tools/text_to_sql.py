"""
Text-to-SQL 工具模块
提供自然语言到PostGIS SQL的转换功能
"""
from typing import Dict, Any, Optional, List
import asyncpg
import logging
import json
import re

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


class NLQueryParser:
    """自然语言查询解析器"""
    
    # 查询类型模式
    QUERY_PATTERNS = {
        'nearby': [
            r'(附近|周围|周边|距离.+?以内)',
            r'(find|search).+?(near|around|within)',
        ],
        'buffer': [
            r'(缓冲区|缓冲|buffer)',
            r'create.+?buffer',
        ],
        'intersection': [
            r'(相交|交集|重叠)',
            r'(intersect|overlap)',
        ],
        'within': [
            r'(在.+?内|包含在)',
            r'(within|inside)',
        ],
        'area': [
            r'(面积|大小)',
            r'(area|size)',
        ],
        'distance': [
            r'(距离|相距)',
            r'(distance|how far)',
        ],
        'count': [
            r'(数量|个数|有多少)',
            r'(count|how many)',
        ],
    }
    
    # 表名模式
    TABLE_PATTERN = r'(表|table)\s*[:\s]*([a-zA-Z_][a-zA-Z0-9_]*)'
    
    # 数字模式 (距离、半径等)
    NUMBER_PATTERN = r'(\d+(?:\.\d+)?)\s*(米|公里|千米|m|km|kilometer|meter)'
    
    # 坐标模式
    COORD_PATTERN = r'(\d+\.?\d*)[,，]\s*(\d+\.?\d*)'
    
    @classmethod
    def detect_query_type(cls, query: str) -> Optional[str]:
        """
        检测查询类型
        
        Args:
            query: 自然语言查询
            
        Returns:
            查询类型或None
        """
        query_lower = query.lower()
        
        for query_type, patterns in cls.QUERY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return query_type
        
        return None
    
    @classmethod
    def extract_table_name(cls, query: str) -> Optional[str]:
        """提取表名"""
        match = re.search(cls.TABLE_PATTERN, query, re.IGNORECASE)
        if match:
            return match.group(2)
        return None
    
    @classmethod
    def extract_distance(cls, query: str) -> Optional[float]:
        """
        提取距离值(统一转换为米)
        
        Args:
            query: 查询文本
            
        Returns:
            距离值(米)
        """
        match = re.search(cls.NUMBER_PATTERN, query)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            
            # 转换为米
            if unit in ['公里', '千米', 'km', 'kilometer']:
                return value * 1000
            else:  # 默认米
                return value
        
        return None
    
    @classmethod
    def extract_coordinates(cls, query: str) -> Optional[tuple]:
        """
        提取坐标
        
        Returns:
            (longitude, latitude) 或 None
        """
        match = re.search(cls.COORD_PATTERN, query)
        if match:
            lon = float(match.group(1))
            lat = float(match.group(2))
            return (lon, lat)
        return None


class SQLGenerator:
    """SQL生成器"""
    
    @staticmethod
    async def get_table_info(table_name: str, schema: str = "public") -> Dict[str, Any]:
        """
        获取表信息用于SQL生成
        
        Args:
            table_name: 表名
            schema: 模式名
            
        Returns:
            表信息字典
        """
        conn = await get_db_connection()
        try:
            query = """
                SELECT 
                    f_geometry_column as geom_column,
                    type as geom_type,
                    srid
                FROM geometry_columns
                WHERE f_table_schema = $1 AND f_table_name = $2
                LIMIT 1
            """
            
            row = await conn.fetchrow(query, schema, table_name)
            
            if not row:
                raise ValueError(f"表 {schema}.{table_name} 不存在或不包含几何列")
            
            # 获取列信息
            columns_query = """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = $2
                ORDER BY ordinal_position
            """
            
            columns = await conn.fetch(columns_query, schema, table_name)
            
            return {
                'geom_column': row['geom_column'],
                'geom_type': row['geom_type'],
                'srid': row['srid'],
                'columns': [
                    {'name': col['column_name'], 'type': col['data_type']}
                    for col in columns
                ]
            }
            
        finally:
            await conn.close()
    
    @staticmethod
    def generate_nearby_query(
        table_name: str,
        geom_column: str,
        longitude: float,
        latitude: float,
        radius: float,
        limit: int = 100,
        schema: str = "public"
    ) -> str:
        """
        生成附近查询SQL
        
        Args:
            table_name: 表名
            geom_column: 几何列名
            longitude: 经度
            latitude: 纬度
            radius: 半径(米)
            limit: 结果限制
            schema: 模式名
            
        Returns:
            SQL查询语句
        """
        point_wkt = f"POINT({longitude} {latitude})"
        
        sql = f"""
-- 查询坐标({longitude}, {latitude})周围{radius}米内的要素
SELECT 
    *,
    ST_Distance(
        ST_Transform({geom_column}, 4326)::geography,
        ST_GeogFromText('SRID=4326;{point_wkt}')
    ) as distance_meters
FROM {schema}.{table_name}
WHERE ST_DWithin(
    ST_Transform({geom_column}, 4326)::geography,
    ST_GeogFromText('SRID=4326;{point_wkt}'),
    {radius}
)
ORDER BY distance_meters
LIMIT {limit};
"""
        return sql.strip()
    
    @staticmethod
    def generate_buffer_query(
        table_name: str,
        geom_column: str,
        distance: float,
        where_clause: Optional[str] = None,
        schema: str = "public"
    ) -> str:
        """
        生成缓冲区查询SQL
        
        Args:
            table_name: 表名
            geom_column: 几何列名
            distance: 缓冲距离(米)
            where_clause: WHERE条件
            schema: 模式名
            
        Returns:
            SQL查询语句
        """
        where = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
-- 创建{distance}米缓冲区
SELECT 
    *,
    ST_AsText(
        ST_Buffer(
            ST_Transform({geom_column}, 3857),
            {distance}
        )
    ) as buffer_geom,
    ST_Area(
        ST_Buffer(
            ST_Transform({geom_column}, 3857),
            {distance}
        )
    ) as buffer_area_sqm
FROM {schema}.{table_name}
{where};
"""
        return sql.strip()
    
    @staticmethod
    def generate_intersection_query(
        table1: str,
        table2: str,
        geom_col1: str,
        geom_col2: str,
        schema: str = "public"
    ) -> str:
        """
        生成相交查询SQL
        
        Args:
            table1: 第一个表名
            table2: 第二个表名
            geom_col1: 第一个表的几何列
            geom_col2: 第二个表的几何列
            schema: 模式名
            
        Returns:
            SQL查询语句
        """
        sql = f"""
-- 查询两个表的相交要素
SELECT 
    a.*,
    b.*,
    ST_AsText(
        ST_Intersection(a.{geom_col1}, b.{geom_col2})
    ) as intersection_geom,
    ST_Area(
        ST_Transform(
            ST_Intersection(a.{geom_col1}, b.{geom_col2}),
            3857
        )
    ) as intersection_area_sqm
FROM {schema}.{table1} a, {schema}.{table2} b
WHERE ST_Intersects(a.{geom_col1}, b.{geom_col2});
"""
        return sql.strip()
    
    @staticmethod
    def generate_area_query(
        table_name: str,
        geom_column: str,
        where_clause: Optional[str] = None,
        schema: str = "public"
    ) -> str:
        """
        生成面积计算SQL
        
        Args:
            table_name: 表名
            geom_column: 几何列名
            where_clause: WHERE条件
            schema: 模式名
            
        Returns:
            SQL查询语句
        """
        where = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
-- 计算几何面积
SELECT 
    *,
    ST_Area(ST_Transform({geom_column}, 3857)) as area_sqm,
    ST_Area(ST_Transform({geom_column}, 3857)) / 1000000.0 as area_sqkm
FROM {schema}.{table_name}
{where}
ORDER BY area_sqm DESC;
"""
        return sql.strip()
    
    @staticmethod
    def generate_count_query(
        table_name: str,
        where_clause: Optional[str] = None,
        schema: str = "public"
    ) -> str:
        """
        生成计数查询SQL
        
        Args:
            table_name: 表名
            where_clause: WHERE条件
            schema: 模式名
            
        Returns:
            SQL查询语句
        """
        where = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
-- 统计要素数量
SELECT COUNT(*) as feature_count
FROM {schema}.{table_name}
{where};
"""
        return sql.strip()


async def parse_nl_query(
    query: str,
    table_name: Optional[str] = None,
    schema: str = "public"
) -> Dict[str, Any]:
    """
    解析自然语言查询并生成SQL
    
    Args:
        query: 自然语言查询
        table_name: 表名(如果未在查询中指定)
        schema: 模式名
        
    Returns:
        包含SQL和元数据的字典
    """
    try:
        # 检测查询类型
        query_type = NLQueryParser.detect_query_type(query)
        if not query_type:
            return {
                "success": False,
                "error": "无法识别查询类型。请使用更明确的描述，如'查询附近'、'计算面积'等"
            }
        
        # 提取表名
        extracted_table = NLQueryParser.extract_table_name(query)
        final_table = extracted_table or table_name
        
        if not final_table:
            return {
                "success": False,
                "error": "未指定表名。请在查询中包含表名，例如'表:buildings'，或单独提供table_name参数"
            }
        
        # 获取表信息
        try:
            table_info = await SQLGenerator.get_table_info(final_table, schema)
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
        
        geom_column = table_info['geom_column']
        
        # 根据查询类型生成SQL
        sql = None
        params = {}
        
        if query_type == 'nearby':
            coords = NLQueryParser.extract_coordinates(query)
            distance = NLQueryParser.extract_distance(query)
            
            if not coords:
                return {
                    "success": False,
                    "error": "未找到坐标信息。请提供经纬度坐标，例如'120.5, 30.2'"
                }
            
            if not distance:
                return {
                    "success": False,
                    "error": "未找到距离信息。请指定距离，例如'500米'或'1公里'"
                }
            
            sql = SQLGenerator.generate_nearby_query(
                final_table, geom_column, coords[0], coords[1], distance, schema=schema
            )
            params = {
                'longitude': coords[0],
                'latitude': coords[1],
                'radius_meters': distance
            }
            
        elif query_type == 'buffer':
            distance = NLQueryParser.extract_distance(query)
            
            if not distance:
                return {
                    "success": False,
                    "error": "未找到缓冲距离。请指定距离，例如'100米'"
                }
            
            sql = SQLGenerator.generate_buffer_query(
                final_table, geom_column, distance, schema=schema
            )
            params = {'buffer_distance_meters': distance}
            
        elif query_type == 'area':
            sql = SQLGenerator.generate_area_query(
                final_table, geom_column, schema=schema
            )
            
        elif query_type == 'count':
            sql = SQLGenerator.generate_count_query(
                final_table, schema=schema
            )
        
        else:
            return {
                "success": False,
                "error": f"查询类型 '{query_type}' 尚未实现完整支持"
            }
        
        if not sql:
            return {
                "success": False,
                "error": "无法生成SQL语句"
            }
        
        return {
            "success": True,
            "query_type": query_type,
            "table_name": final_table,
            "schema": schema,
            "table_info": table_info,
            "sql": sql,
            "parameters": params,
            "original_query": query
        }
        
    except Exception as e:
        logger.error(f"解析自然语言查询失败: {str(e)}")
        return {
            "success": False,
            "error": f"解析失败: {str(e)}"
        }


async def execute_generated_sql(
    sql: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    执行生成的SQL语句
    
    Args:
        sql: SQL语句
        limit: 结果数量限制
        
    Returns:
        执行结果
    """
    conn = await get_db_connection()
    try:
        # 如果需要限制结果数量，修改SQL
        if limit and 'LIMIT' not in sql.upper():
            sql = sql.rstrip(';') + f'\nLIMIT {limit};'
        
        # 执行查询
        rows = await conn.fetch(sql)
        
        # 转换结果
        results = []
        for row in rows:
            result = dict(row)
            # 转换几何对象为字符串
            for key, value in result.items():
                if value is not None and hasattr(value, '__class__'):
                    if 'geometry' in value.__class__.__name__.lower():
                        result[key] = str(value)
            results.append(result)
        
        return {
            "success": True,
            "row_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"执行SQL失败: {str(e)}")
        return {
            "success": False,
            "error": f"执行失败: {str(e)}"
        }
    finally:
        await conn.close()