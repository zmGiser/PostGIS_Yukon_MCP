"""
工具模块
"""
from .spatial_query import (
    query_nearby_features,
    query_within_bbox,
    query_by_attribute
)
from .geometry import (
    create_buffer,
    calculate_area,
    calculate_length,
    transform_geometry,
    simplify_geometry
)
from .analysis import (
    calculate_distance,
    check_intersection,
    check_containment,
    union_geometries,
    calculate_centroid
)
from .admin import (
    get_postgis_version,
    list_installed_extensions,
    list_spatial_tables,
    get_table_spatial_info,
    create_spatial_index,
    analyze_table,
    vacuum_table,
    get_spatial_extent,
    check_geometry_validity
)
from .advanced import (
    spatial_join,
    nearest_neighbor,
    spatial_cluster,
    convex_hull,
    voronoi_polygons,
    line_interpolate,
    snap_to_grid,
    split_line_by_point
)
from .data_import import (
    import_shapefile,
    import_geojson,
    import_geotiff,
    import_png_as_georeferenced,
    list_supported_formats
)

__all__ = [
    # 空间查询
    "query_nearby_features",
    "query_within_bbox",
    "query_by_attribute",
    # 几何操作
    "create_buffer",
    "calculate_area",
    "calculate_length",
    "transform_geometry",
    "simplify_geometry",
    # 空间分析
    "calculate_distance",
    "check_intersection",
    "check_containment",
    "union_geometries",
    "calculate_centroid",
    # 数据库管理
    "get_postgis_version",
    "list_installed_extensions",
    "list_spatial_tables",
    "get_table_spatial_info",
    "create_spatial_index",
    "analyze_table",
    "vacuum_table",
    "get_spatial_extent",
    "check_geometry_validity",
    # 高级分析
    "spatial_join",
    "nearest_neighbor",
    "spatial_cluster",
    "convex_hull",
    "voronoi_polygons",
    "line_interpolate",
    "snap_to_grid",
    "split_line_by_point",
    # 数据导入
    "import_shapefile",
    "import_geojson",
    "import_geotiff",
    "import_png_as_georeferenced",
    "list_supported_formats",
]