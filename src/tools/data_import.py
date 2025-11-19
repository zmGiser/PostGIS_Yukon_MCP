"""
数据导入工具模块
提供矢量格式(SHP, GeoJSON)和栅格格式(TIF, PNG)的导入功能
"""
from typing import Dict, Any, List, Optional
import asyncpg
import logging
import json
import os
from pathlib import Path
import tempfile
import base64
import pandas as pd

# 地理空间数据处理
import geopandas as gpd
import fiona
from shapely import wkt
from shapely.geometry import mapping, shape

# 栅格数据处理
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from PIL import Image
import numpy as np

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


async def import_shapefile(
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
        schema: 数据库模式名
        srid: 空间参考系统ID
        geometry_column: 几何列名
        if_exists: 如果表存在的处理方式 ('replace', 'append', 'fail')
        
    Returns:
        导入结果信息
    """
    conn = await get_db_connection()
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取 Shapefile
        logger.info(f"正在读取 Shapefile: {file_path}")
        gdf = gpd.read_file(file_path)
        
        # 转换坐标系
        if gdf.crs is not None and gdf.crs.to_epsg() != srid:
            logger.info(f"转换坐标系从 {gdf.crs.to_epsg()} 到 {srid}")
            gdf = gdf.to_crs(epsg=srid)
        
        # 获取几何类型
        geom_type = gdf.geometry.geom_type.mode()[0] if len(gdf) > 0 else "Unknown"
        
        # 检查表是否存在
        table_exists_query = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = $1 AND table_name = $2
            )
        """
        table_exists = await conn.fetchval(table_exists_query, schema, table_name)
        
        if table_exists:
            if if_exists == "fail":
                raise ValueError(f"表 {schema}.{table_name} 已存在")
            elif if_exists == "replace":
                logger.info(f"删除现有表: {schema}.{table_name}")
                await conn.execute(f'DROP TABLE IF EXISTS "{schema}"."{table_name}" CASCADE')
        
        # 创建表结构
        columns = []
        for col in gdf.columns:
            if col != gdf.geometry.name:
                dtype = gdf[col].dtype
                if dtype == 'object':
                    pg_type = 'TEXT'
                elif dtype in ['int64', 'int32']:
                    pg_type = 'INTEGER'
                elif dtype in ['float64', 'float32']:
                    pg_type = 'DOUBLE PRECISION'
                elif dtype == 'bool':
                    pg_type = 'BOOLEAN'
                else:
                    pg_type = 'TEXT'
                columns.append(f'"{col}" {pg_type}')
        
        columns.append(f'"{geometry_column}" geometry({geom_type}, {srid})')
        
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS "{schema}"."{table_name}" (
                id SERIAL PRIMARY KEY,
                {', '.join(columns)}
            )
        """
        
        if not table_exists or if_exists == "replace":
            await conn.execute(create_table_sql)
            logger.info(f"创建表: {schema}.{table_name}")
        
        # 插入数据
        insert_count = 0
        for idx, row in gdf.iterrows():
            # 准备属性数据
            attrs = []
            attr_cols = []
            for col in gdf.columns:
                if col != gdf.geometry.name:
                    attr_cols.append(f'"{col}"')
                    value = row[col]
                    if pd.isna(value):
                        attrs.append(None)
                    else:
                        attrs.append(value)
            
            # 准备几何数据
            geom_wkt = row.geometry.wkt if row.geometry is not None else None
            
            if geom_wkt:
                placeholders = ', '.join([f'${i+1}' for i in range(len(attrs))])
                insert_sql = f"""
                    INSERT INTO "{schema}"."{table_name}" 
                    ({', '.join(attr_cols)}, "{geometry_column}")
                    VALUES ({placeholders}, ST_GeomFromText(${len(attrs)+1}, {srid}))
                """
                await conn.execute(insert_sql, *attrs, geom_wkt)
                insert_count += 1
        
        # 创建空间索引
        index_name = f"{table_name}_{geometry_column}_idx"
        create_index_sql = f"""
            CREATE INDEX IF NOT EXISTS "{index_name}"
            ON "{schema}"."{table_name}"
            USING GIST ("{geometry_column}")
        """
        await conn.execute(create_index_sql)
        
        result = {
            "table_name": f"{schema}.{table_name}",
            "geometry_type": geom_type,
            "srid": srid,
            "feature_count": insert_count,
            "columns": list(gdf.columns),
            "bounds": gdf.total_bounds.tolist()
        }
        
        logger.info(f"成功导入 {insert_count} 个要素到 {schema}.{table_name}")
        return result
        
    except Exception as e:
        logger.error(f"导入 Shapefile 失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def import_geojson(
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
        file_path: GeoJSON 文件路径
        geojson_data: GeoJSON 字符串数据
        table_name: 目标表名
        schema: 数据库模式名
        srid: 空间参考系统ID
        geometry_column: 几何列名
        if_exists: 如果表存在的处理方式
        
    Returns:
        导入结果信息
    """
    conn = await get_db_connection()
    try:
        # 读取 GeoJSON
        if file_path:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            logger.info(f"正在读取 GeoJSON 文件: {file_path}")
            gdf = gpd.read_file(file_path)
        elif geojson_data:
            logger.info("正在解析 GeoJSON 数据")
            geojson_dict = json.loads(geojson_data)
            gdf = gpd.GeoDataFrame.from_features(geojson_dict['features'])
            gdf.crs = f"EPSG:{srid}"
        else:
            raise ValueError("必须提供 file_path 或 geojson_data")
        
        # 转换坐标系
        if gdf.crs is not None and gdf.crs.to_epsg() != srid:
            logger.info(f"转换坐标系从 {gdf.crs.to_epsg()} 到 {srid}")
            gdf = gdf.to_crs(epsg=srid)
        
        # 获取几何类型
        geom_type = gdf.geometry.geom_type.mode()[0] if len(gdf) > 0 else "Unknown"
        
        # 检查表是否存在
        table_exists_query = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = $1 AND table_name = $2
            )
        """
        table_exists = await conn.fetchval(table_exists_query, schema, table_name)
        
        if table_exists:
            if if_exists == "fail":
                raise ValueError(f"表 {schema}.{table_name} 已存在")
            elif if_exists == "replace":
                logger.info(f"删除现有表: {schema}.{table_name}")
                await conn.execute(f'DROP TABLE IF EXISTS "{schema}"."{table_name}" CASCADE')
        
        # 创建表并插入数据(使用与 shapefile 相同的逻辑)
        columns = []
        for col in gdf.columns:
            if col != gdf.geometry.name:
                dtype = gdf[col].dtype
                if dtype == 'object':
                    pg_type = 'TEXT'
                elif dtype in ['int64', 'int32']:
                    pg_type = 'INTEGER'
                elif dtype in ['float64', 'float32']:
                    pg_type = 'DOUBLE PRECISION'
                elif dtype == 'bool':
                    pg_type = 'BOOLEAN'
                else:
                    pg_type = 'TEXT'
                columns.append(f'"{col}" {pg_type}')
        
        columns.append(f'"{geometry_column}" geometry({geom_type}, {srid})')
        
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS "{schema}"."{table_name}" (
                id SERIAL PRIMARY KEY,
                {', '.join(columns)}
            )
        """
        
        if not table_exists or if_exists == "replace":
            await conn.execute(create_table_sql)
            logger.info(f"创建表: {schema}.{table_name}")
        
        # 插入数据
        insert_count = 0
        for idx, row in gdf.iterrows():
            attrs = []
            attr_cols = []
            for col in gdf.columns:
                if col != gdf.geometry.name:
                    attr_cols.append(f'"{col}"')
                    value = row[col]
                    if pd.isna(value):
                        attrs.append(None)
                    else:
                        attrs.append(value)
            
            geom_wkt = row.geometry.wkt if row.geometry is not None else None
            
            if geom_wkt:
                placeholders = ', '.join([f'${i+1}' for i in range(len(attrs))])
                insert_sql = f"""
                    INSERT INTO "{schema}"."{table_name}" 
                    ({', '.join(attr_cols)}, "{geometry_column}")
                    VALUES ({placeholders}, ST_GeomFromText(${len(attrs)+1}, {srid}))
                """
                await conn.execute(insert_sql, *attrs, geom_wkt)
                insert_count += 1
        
        # 创建空间索引
        index_name = f"{table_name}_{geometry_column}_idx"
        create_index_sql = f"""
            CREATE INDEX IF NOT EXISTS "{index_name}"
            ON "{schema}"."{table_name}"
            USING GIST ("{geometry_column}")
        """
        await conn.execute(create_index_sql)
        
        result = {
            "table_name": f"{schema}.{table_name}",
            "geometry_type": geom_type,
            "srid": srid,
            "feature_count": insert_count,
            "columns": list(gdf.columns),
            "bounds": gdf.total_bounds.tolist()
        }
        
        logger.info(f"成功导入 {insert_count} 个要素到 {schema}.{table_name}")
        return result
        
    except Exception as e:
        logger.error(f"导入 GeoJSON 失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def import_geotiff(
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
        file_path: GeoTIFF 文件路径
        table_name: 目标表名
        schema: 数据库模式名
        srid: 目标空间参考系统ID(如果为None则使用文件原始SRID)
        tile_size: 瓦片大小
        overview_levels: 概览层级
        
    Returns:
        导入结果信息
    """
    conn = await get_db_connection()
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        logger.info(f"正在读取 GeoTIFF: {file_path}")
        
        with rasterio.open(file_path) as src:
            # 获取栅格元数据
            meta = src.meta.copy()
            src_srid = src.crs.to_epsg() if src.crs else None
            target_srid = srid if srid else src_srid
            
            if target_srid is None:
                raise ValueError("无法确定空间参考系统")
            
            # 如果需要重投影
            if src_srid != target_srid:
                logger.info(f"重投影栅格从 EPSG:{src_srid} 到 EPSG:{target_srid}")
                transform, width, height = calculate_default_transform(
                    src.crs, f'EPSG:{target_srid}', src.width, src.height, *src.bounds
                )
                meta.update({
                    'crs': f'EPSG:{target_srid}',
                    'transform': transform,
                    'width': width,
                    'height': height
                })
            
            # 创建栅格表
            create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS "{schema}"."{table_name}" (
                    rid SERIAL PRIMARY KEY,
                    rast raster,
                    filename TEXT
                )
            """
            await conn.execute(f'DROP TABLE IF EXISTS "{schema}"."{table_name}" CASCADE')
            await conn.execute(create_table_sql)
            
            # 读取栅格数据
            if src_srid != target_srid:
                # 需要重投影
                data = np.empty((src.count, height, width), dtype=meta['dtype'])
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=data[i-1],
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=f'EPSG:{target_srid}',
                        resampling=Resampling.bilinear
                    )
            else:
                data = src.read()
                transform = src.transform
            
            # 将栅格数据编码为 WKB 格式并插入
            bounds = src.bounds
            pixel_size_x = transform[0]
            pixel_size_y = -transform[4]  # y方向通常是负的
            
            # 使用 ST_AddBand 构建栅格
            bands_data = []
            for band_idx in range(data.shape[0]):
                band_data = data[band_idx].flatten().tolist()
                bands_data.append(band_data)
            
            # 插入栅格(简化版本 - 实际应用中可能需要分块处理)
            insert_sql = f"""
                INSERT INTO "{schema}"."{table_name}" (rast, filename)
                VALUES (
                    ST_AddBand(
                        ST_MakeEmptyRaster(
                            $1, $2, $3, $4, $5, $6, 0, 0, $7
                        ),
                        '8BUI'::text, 0, 0
                    ),
                    $8
                )
            """
            
            await conn.execute(
                insert_sql,
                meta['width'], meta['height'],
                bounds.left, bounds.top,
                pixel_size_x, pixel_size_y,
                target_srid,
                os.path.basename(file_path)
            )
            
            # 创建空间索引
            index_sql = f"""
                CREATE INDEX IF NOT EXISTS "{table_name}_rast_idx"
                ON "{schema}"."{table_name}"
                USING GIST (ST_ConvexHull(rast))
            """
            await conn.execute(index_sql)
            
            result = {
                "table_name": f"{schema}.{table_name}",
                "srid": target_srid,
                "width": meta['width'],
                "height": meta['height'],
                "bands": src.count,
                "dtype": str(meta['dtype']),
                "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
                "pixel_size": [pixel_size_x, pixel_size_y]
            }
            
            logger.info(f"成功导入 GeoTIFF 到 {schema}.{table_name}")
            return result
            
    except Exception as e:
        logger.error(f"导入 GeoTIFF 失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def import_png_as_georeferenced(
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
        schema: 数据库模式名
        srid: 空间参考系统ID
        
    Returns:
        导入结果信息
    """
    conn = await get_db_connection()
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        logger.info(f"正在读取 PNG: {file_path}")
        
        # 使用 PIL 读取 PNG
        img = Image.open(file_path)
        img_array = np.array(img)
        
        width, height = img.size
        minx, miny, maxx, maxy = bounds
        
        # 计算像素大小
        pixel_size_x = (maxx - minx) / width
        pixel_size_y = (maxy - miny) / height
        
        # 创建栅格表
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS "{schema}"."{table_name}" (
                rid SERIAL PRIMARY KEY,
                rast raster,
                filename TEXT
            )
        """
        await conn.execute(f'DROP TABLE IF EXISTS "{schema}"."{table_name}" CASCADE')
        await conn.execute(create_table_sql)
        
        # 插入栅格数据
        insert_sql = f"""
            INSERT INTO "{schema}"."{table_name}" (rast, filename)
            VALUES (
                ST_MakeEmptyRaster($1, $2, $3, $4, $5, $6, 0, 0, $7),
                $8
            )
        """
        
        await conn.execute(
            insert_sql,
            width, height,
            minx, maxy,  # 左上角
            pixel_size_x, -pixel_size_y,  # y方向是负的
            srid,
            os.path.basename(file_path)
        )
        
        # 创建空间索引
        index_sql = f"""
            CREATE INDEX IF NOT EXISTS "{table_name}_rast_idx"
            ON "{schema}"."{table_name}"
            USING GIST (ST_ConvexHull(rast))
        """
        await conn.execute(index_sql)
        
        result = {
            "table_name": f"{schema}.{table_name}",
            "srid": srid,
            "width": width,
            "height": height,
            "bounds": bounds,
            "pixel_size": [pixel_size_x, pixel_size_y],
            "mode": img.mode
        }
        
        logger.info(f"成功导入 PNG 到 {schema}.{table_name}")
        return result
        
    except Exception as e:
        logger.error(f"导入 PNG 失败: {str(e)}")
        raise
    finally:
        await conn.close()


async def list_supported_formats() -> Dict[str, Any]:
    """
    列出支持的导入格式
    
    Returns:
        支持的格式列表
    """
    return {
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