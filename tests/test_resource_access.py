"""
诊断 MCP 资源访问问题
"""
import asyncio
import json
from src.config.database import db_config
from src.tools.admin import get_spatial_extent, list_spatial_tables


async def diagnose_resource_issue():
    """诊断资源访问问题"""
    print("=" * 60)
    print("MCP 资源访问诊断")
    print("=" * 60)
    
    # 1. 测试数据库连接
    print("\n[1] 测试数据库连接")
    try:
        db_config.initialize_pool()
        if db_config.test_connection():
            print("  ✓ 数据库连接正常")
        else:
            print("  ✗ 数据库连接失败")
            return
    except Exception as e:
        print(f"  ✗ 数据库连接错误: {str(e)}")
        return
    
    # 2. 列出所有空间表
    print("\n[2] 列出所有空间表")
    try:
        tables = await list_spatial_tables("public")
        if tables:
            print(f"  ✓ 找到 {len(tables)} 个空间表:")
            for table in tables[:5]:  # 只显示前5个
                print(f"    - {table['table']}: {table['geometry_column']} ({table['geometry_type']})")
            
            # 使用第一个表进行测试
            if tables:
                test_table = tables[0]
                test_table_name = test_table['table']
                test_geom_col = test_table['geometry_column']
                
                print(f"\n[3] 测试获取表空间范围")
                print(f"  表名: {test_table_name}")
                print(f"  几何列: {test_geom_col}")
                
                try:
                    extent = await get_spatial_extent(test_table_name, test_geom_col, "public")
                    print(f"  ✓ 成功获取空间范围:")
                    print(f"    {json.dumps(extent, indent=4, ensure_ascii=False)}")
                    
                    print(f"\n[4] 资源 URI 格式")
                    print(f"  应该使用的 URI: yukon://table/public/{test_table_name}/extent")
                    
                except Exception as e:
                    print(f"  ✗ 获取空间范围失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
        else:
            print("  ! 没有找到空间表")
            print("  建议: 先导入一些空间数据")
            
    except Exception as e:
        print(f"  ✗ 列出表失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 5. 检查资源定义
    print("\n[5] 资源定义检查")
    print("  在 src/server.py 中定义的资源:")
    print("    1. yukon://database/info")
    print("    2. yukon://tables/{schema}")
    print("    3. yukon://table/{schema}/{table_name}/info")
    print("    4. yukon://table/{schema}/{table_name}/extent  ← 你的资源")
    print("    5. yukon://formats/supported")
    
    print("\n[6] 可能的问题和解决方案")
    print("=" * 60)
    print("""
问题 1: 表不存在或没有几何列
  解决: 使用 discover_spatial_tables 工具先查看可用的表

问题 2: 几何列名不是 'geom'
  当前实现: 资源函数硬编码使用 'geom' 作为几何列名
  解决: 需要修改资源函数以支持不同的几何列名

问题 3: FastMCP 版本或配置问题
  检查: pip show mcp
  更新: pip install --upgrade mcp

问题 4: 客户端调用格式不正确
  正确格式: 使用完整的 URI 路径，包括所有参数
  示例: yukon://table/public/my_table/extent

问题 5: 资源函数抛出异常
  当前行为: 异常被捕获并返回 JSON 错误
  建议: 查看服务器日志以获取详细错误信息
    """)
    
    db_config.close_all_connections()


if __name__ == "__main__":
    asyncio.run(diagnose_resource_issue())