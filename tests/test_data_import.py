"""
数据导入工具测试模块
"""
import pytest
import asyncio
from pathlib import Path
import json
import tempfile
import os

# 注意：这些测试需要实际的数据库连接和测试文件
# 在实际使用前需要准备测试数据


@pytest.mark.asyncio
async def test_list_supported_formats():
    """测试获取支持的格式列表"""
    from src.tools.data_import import list_supported_formats
    
    result = await list_supported_formats()
    
    assert "vector_formats" in result
    assert "raster_formats" in result
    assert "shapefile" in result["vector_formats"]
    assert "geojson" in result["vector_formats"]
    assert "geotiff" in result["raster_formats"]
    assert "png" in result["raster_formats"]


@pytest.mark.asyncio
async def test_import_geojson_from_string():
    """测试从GeoJSON字符串导入数据"""
    from src.tools.data_import import import_geojson
    
    # 创建简单的GeoJSON测试数据
    geojson_data = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Test Point"},
                "geometry": {
                    "type": "Point",
                    "coordinates": [116.4074, 39.9042]  # 北京坐标
                }
            }
        ]
    })
    
    # 注意：此测试需要实际的数据库连接
    # 在CI/CD环境中可能需要跳过
    try:
        result = await import_geojson(
            geojson_data=geojson_data,
            table_name="test_geojson_import",
            schema="public",
            srid=4326
        )
        
        assert result["table_name"] == "public.test_geojson_import"
        assert result["feature_count"] == 1
        assert result["srid"] == 4326
    except Exception as e:
        pytest.skip(f"需要数据库连接: {str(e)}")


@pytest.mark.asyncio
async def test_import_shapefile_file_not_found():
    """测试导入不存在的Shapefile"""
    from src.tools.data_import import import_shapefile
    
    with pytest.raises(FileNotFoundError):
        await import_shapefile(
            file_path="/nonexistent/path/to/file.shp",
            table_name="test_table"
        )


@pytest.mark.asyncio
async def test_import_geotiff_file_not_found():
    """测试导入不存在的GeoTIFF"""
    from src.tools.data_import import import_geotiff
    
    with pytest.raises(FileNotFoundError):
        await import_geotiff(
            file_path="/nonexistent/path/to/file.tif",
            table_name="test_raster"
        )


@pytest.mark.asyncio
async def test_import_png_file_not_found():
    """测试导入不存在的PNG"""
    from src.tools.data_import import import_png_as_georeferenced
    
    with pytest.raises(FileNotFoundError):
        await import_png_as_georeferenced(
            file_path="/nonexistent/path/to/file.png",
            table_name="test_png",
            bounds=[0, 0, 1, 1]
        )


# 集成测试示例（需要实际文件和数据库）
@pytest.mark.skip(reason="需要实际的测试文件和数据库连接")
@pytest.mark.asyncio
async def test_import_shapefile_integration():
    """集成测试：导入实际的Shapefile"""
    from src.tools.data_import import import_shapefile
    
    # 假设有测试数据文件
    test_shapefile = "tests/data/test_points.shp"
    
    if not os.path.exists(test_shapefile):
        pytest.skip("测试Shapefile不存在")
    
    result = await import_shapefile(
        file_path=test_shapefile,
        table_name="test_shapefile_import",
        schema="public",
        srid=4326,
        if_exists="replace"
    )
    
    assert result["table_name"] == "public.test_shapefile_import"
    assert result["feature_count"] > 0
    assert "geometry_type" in result


@pytest.mark.skip(reason="需要实际的测试文件和数据库连接")
@pytest.mark.asyncio
async def test_import_geotiff_integration():
    """集成测试：导入实际的GeoTIFF"""
    from src.tools.data_import import import_geotiff
    
    test_geotiff = "tests/data/test_raster.tif"
    
    if not os.path.exists(test_geotiff):
        pytest.skip("测试GeoTIFF不存在")
    
    result = await import_geotiff(
        file_path=test_geotiff,
        table_name="test_geotiff_import",
        schema="public"
    )
    
    assert result["table_name"] == "public.test_geotiff_import"
    assert result["width"] > 0
    assert result["height"] > 0
    assert result["bands"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])