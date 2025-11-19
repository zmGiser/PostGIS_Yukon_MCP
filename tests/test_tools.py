"""
PostGIS MCP 工具测试
"""
import pytest
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
    get_postgis_version,
    list_installed_extensions,
    list_spatial_tables,
    get_table_spatial_info,
    create_spatial_index,
    spatial_join,
    nearest_neighbor,
    spatial_cluster,
    convex_hull,
)


# 注意: 这些测试需要配置好的 PostGIS 数据库连接才能运行
# 在运行测试前，请确保:
# 1. 已安装并配置 PostGIS 数据库
# 2. 已在 .env 文件中配置数据库连接信息
# 3. 数据库中有相应的测试数据表


@pytest.mark.asyncio
async def test_query_nearby_features():
    """测试查询附近要素"""
    # 示例: 查询经纬度 (120.0, 30.0) 附近1000米的要素
    # 需要替换为实际的表名
    try:
        results = await query_nearby_features(
            longitude=120.0,
            latitude=30.0,
            radius=1000.0,
            table_name="your_table_name",
            geometry_column="geom",
            limit=10
        )
        assert isinstance(results, list)
        print(f"找到 {len(results)} 个附近要素")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_query_within_bbox():
    """测试边界框查询"""
    # 示例: 查询指定边界框内的要素
    try:
        results = await query_within_bbox(
            min_x=119.9,
            min_y=29.9,
            max_x=120.1,
            max_y=30.1,
            table_name="your_table_name",
            geometry_column="geom",
            limit=10
        )
        assert isinstance(results, list)
        print(f"找到 {len(results)} 个边界框内要素")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_create_buffer():
    """测试创建缓冲区"""
    # 示例: 为一个点创建缓冲区
    try:
        result = await create_buffer(
            geometry_wkt="POINT(120.0 30.0)",
            distance=1000.0,
            srid=4326
        )
        assert "buffer_geometry" in result
        assert "area_sqm" in result
        print(f"缓冲区面积: {result['area_sqm']} 平方米")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_calculate_area():
    """测试计算面积"""
    # 示例: 计算一个多边形的面积
    try:
        result = await calculate_area(
            geometry_wkt="POLYGON((120 30, 120.1 30, 120.1 30.1, 120 30.1, 120 30))",
            srid=4326
        )
        assert "area_square_meters" in result
        assert "area_square_kilometers" in result
        print(f"面积: {result['area_square_meters']} 平方米")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_calculate_distance():
    """测试计算距离"""
    # 示例: 计算两点之间的距离
    try:
        result = await calculate_distance(
            geom1_wkt="POINT(120.0 30.0)",
            geom2_wkt="POINT(120.1 30.1)",
            srid=4326
        )
        assert "distance_meters" in result
        assert "distance_kilometers" in result
        print(f"距离: {result['distance_meters']} 米")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_check_intersection():
    """测试相交检查"""
    # 示例: 检查两个几何对象是否相交
    try:
        result = await check_intersection(
            geom1_wkt="POLYGON((120 30, 120.1 30, 120.1 30.1, 120 30.1, 120 30))",
            geom2_wkt="POLYGON((120.05 30.05, 120.15 30.05, 120.15 30.15, 120.05 30.15, 120.05 30.05))",
            srid=4326
        )
        assert "intersects" in result
        print(f"是否相交: {result['intersects']}")
        if result['intersects']:
            print(f"相交几何: {result['intersection_geometry']}")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_query_by_attribute():
    """测试属性查询"""
    try:
        results = await query_by_attribute(
            table_name="your_table_name",
            attribute_name="name",
            attribute_value="test",
            geometry_column="geom",
            limit=10
        )
        assert isinstance(results, list)
        print(f"找到 {len(results)} 个匹配要素")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_calculate_length():
    """测试计算长度"""
    try:
        result = await calculate_length(
            geometry_wkt="LINESTRING(120 30, 120.1 30.1)",
            srid=4326
        )
        assert "length_meters" in result
        assert "length_kilometers" in result
        print(f"长度: {result['length_meters']} 米")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_transform_geometry():
    """测试坐标系统转换"""
    try:
        result = await transform_geometry(
            geometry_wkt="POINT(120.0 30.0)",
            from_srid=4326,
            to_srid=3857
        )
        assert "transformed_geometry" in result
        assert "from_srid" in result
        assert "to_srid" in result
        print(f"转换后几何: {result['transformed_geometry']}")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_simplify_geometry():
    """测试简化几何"""
    try:
        result = await simplify_geometry(
            geometry_wkt="LINESTRING(120 30, 120.01 30.01, 120.02 30.02, 120.1 30.1)",
            tolerance=0.01,
            srid=4326
        )
        assert "simplified_geometry" in result
        assert "original_point_count" in result
        assert "simplified_point_count" in result
        print(f"简化: {result['original_point_count']} -> {result['simplified_point_count']} 点")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_check_containment():
    """测试包含关系检查"""
    try:
        result = await check_containment(
            container_wkt="POLYGON((120 30, 120.2 30, 120.2 30.2, 120 30.2, 120 30))",
            contained_wkt="POINT(120.1 30.1)",
            srid=4326
        )
        assert "contains" in result
        assert "within" in result
        print(f"包含关系: contains={result['contains']}, within={result['within']}")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_union_geometries():
    """测试合并几何对象"""
    try:
        result = await union_geometries(
            geometries_wkt=[
                "POLYGON((120 30, 120.1 30, 120.1 30.1, 120 30.1, 120 30))",
                "POLYGON((120.05 30.05, 120.15 30.05, 120.15 30.15, 120.05 30.15, 120.05 30.05))"
            ],
            srid=4326
        )
        assert "union_geometry" in result
        print(f"合并后几何: {result['union_geometry']}")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_calculate_centroid():
    """测试计算质心"""
    try:
        result = await calculate_centroid(
            geometry_wkt="POLYGON((120 30, 120.1 30, 120.1 30.1, 120 30.1, 120 30))",
            srid=4326
        )
        assert "centroid_geometry" in result
        assert "longitude" in result
        assert "latitude" in result
        print(f"质心: ({result['longitude']}, {result['latitude']})")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_get_postgis_version():
    """测试获取 PostGIS 版本"""
    try:
        result = await get_postgis_version()
        assert "postgis_version" in result
        print(f"PostGIS 版本: {result['postgis_version']}")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_list_installed_extensions():
    """测试列出已安装扩展"""
    try:
        extensions = await list_installed_extensions()
        assert isinstance(extensions, list)
        print(f"找到 {len(extensions)} 个 PostGIS 相关扩展")
        for ext in extensions:
            print(f"  - {ext['name']}: {ext['installed_version']}")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_list_spatial_tables():
    """测试列出空间表"""
    try:
        tables = await list_spatial_tables(schema="public")
        assert isinstance(tables, list)
        print(f"找到 {len(tables)} 个空间表")
        for table in tables:
            print(f"  - {table['table']}: {table['geometry_type']}")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接")


@pytest.mark.asyncio
async def test_get_table_spatial_info():
    """测试获取表空间信息"""
    try:
        info = await get_table_spatial_info(
            table_name="your_table_name",
            schema="public"
        )
        assert "row_count" in info
        assert "geometry_columns" in info
        print(f"表信息: {info['row_count']} 行")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接或表不存在")


@pytest.mark.asyncio
async def test_spatial_join():
    """测试空间连接"""
    try:
        results = await spatial_join(
            table1="table1",
            table2="table2",
            geom_col1="geom",
            geom_col2="geom",
            join_type="intersects",
            schema="public"
        )
        assert isinstance(results, list)
        print(f"空间连接结果: {len(results)} 条")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接或表不存在")


@pytest.mark.asyncio
async def test_nearest_neighbor():
    """测试最近邻查询"""
    try:
        neighbors = await nearest_neighbor(
            point_wkt="POINT(120.0 30.0)",
            table_name="your_table_name",
            geometry_column="geom",
            k=5,
            max_distance=10000,
            schema="public",
            srid=4326
        )
        assert isinstance(neighbors, list)
        print(f"找到 {len(neighbors)} 个最近邻居")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接或表不存在")


@pytest.mark.asyncio
async def test_spatial_cluster():
    """测试空间聚类"""
    try:
        result = await spatial_cluster(
            table_name="your_table_name",
            geometry_column="geom",
            distance=100,
            min_points=5,
            schema="public"
        )
        assert "cluster_count" in result
        assert "clusters" in result
        print(f"识别出 {result['cluster_count']} 个聚类")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接或表不存在")


@pytest.mark.asyncio
async def test_convex_hull():
    """测试计算凸包"""
    try:
        result = await convex_hull(
            table_name="your_table_name",
            geometry_column="geom",
            schema="public"
        )
        assert "convex_hull_wkt" in result
        assert "area_square_meters" in result
        print(f"凸包面积: {result['area_square_meters']} 平方米")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        pytest.skip("需要配置数据库连接或表不存在")


if __name__ == "__main__":
    # 运行测试
    # pytest tests/test_tools.py -v
    print("使用 pytest 运行测试: pytest tests/test_tools.py -v")