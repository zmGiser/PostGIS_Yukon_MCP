"""
测试导入 bmR.shp 文件
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.data_import import import_shapefile


async def test_import_bmR():
    """测试导入 E:/test_data/bmR.shp"""
    
    print("=" * 60)
    print("开始测试 Shapefile 导入功能")
    print("=" * 60)
    
    file_path = "E:/test_data/bmR.shp"
    table_name = "bmr_test"
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 错误: 文件不存在 - {file_path}")
        return
    
    print(f"\n文件路径: {file_path}")
    print(f"目标表名: {table_name}")
    print(f"数据库模式: public")
    print(f"坐标系统: EPSG:4326")
    
    try:
        print("\n正在导入数据...")
        result = await import_shapefile(
            file_path=file_path,
            table_name=table_name,
            schema="public",
            srid=4326,
            geometry_column="geom",
            if_exists="replace"
        )
        
        print("\n导入成功!")
        print("\n" + "=" * 60)
        print("导入结果详情")
        print("=" * 60)
        print(f"表名: {result['table_name']}")
        print(f"几何类型: {result['geometry_type']}")
        print(f"坐标系统: EPSG:{result['srid']}")
        print(f"要素数量: {result['feature_count']}")
        print(f"\n字段列表:")
        for i, col in enumerate(result['columns'], 1):
            print(f"   {i}. {col}")
        print(f"\n空间范围 (边界):")
        bounds = result['bounds']
        print(f"   最小X (西): {bounds[0]:.6f}")
        print(f"   最小Y (南): {bounds[1]:.6f}")
        print(f"   最大X (东): {bounds[2]:.6f}")
        print(f"   最大Y (北): {bounds[3]:.6f}")
        print("\n" + "=" * 60)
        
    except FileNotFoundError as e:
        print(f"\n文件错误: {e}")
    except Exception as e:
        print(f"\n导入失败: {e}")
        import traceback
        print("\n详细错误信息:")
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" PostGIS 数据导入工具测试 - bmR.shp")
    print("=" * 60 + "\n")
    
    asyncio.run(test_import_bmR())
    
    print("\n" + "=" * 60)
    print(" 测试完成")
    print("=" * 60 + "\n")