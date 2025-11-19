"""
测试 MCP 资源
"""
import asyncio
import json
from src.tools.admin import get_spatial_extent


async def test_get_spatial_extent():
    """测试获取空间范围功能"""
    print("\n=== 测试 get_spatial_extent 函数 ===")
    
    # 测试参数
    table_name = "your_table_name"  # 替换为实际表名
    geometry_column = "geom"
    schema = "public"
    
    try:
        result = await get_spatial_extent(table_name, geometry_column, schema)
        print(f"[OK] 成功获取空间范围")
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"[FAIL] 获取失败: {str(e)}")


async def test_resource_format():
    """测试资源 URI 格式"""
    print("\n=== 测试资源 URI 格式 ===")
    
    # 测试不同的 URI 格式
    test_cases = [
        ("yukon://database/info", "数据库信息"),
        ("yukon://tables/public", "公共模式表列表"),
        ("yukon://table/public/test_table/info", "表信息"),
        ("yukon://table/public/test_table/extent", "表空间范围"),
        ("yukon://formats/supported", "支持格式"),
    ]
    
    print("定义的资源 URI:")
    for uri, desc in test_cases:
        print(f"  - {uri}: {desc}")
    
    print("\n注意: FastMCP 资源路径格式要求:")
    print("  1. 路径参数必须用大括号包围: {param}")
    print("  2. 参数名必须与函数参数名完全匹配")
    print("  3. 路径不能包含特殊字符")


if __name__ == "__main__":
    print("=" * 60)
    print("MCP 资源测试")
    print("=" * 60)
    
    asyncio.run(test_resource_format())
    
    print("\n" + "=" * 60)
    print("如果资源无法访问，可能的原因:")
    print("=" * 60)
    print("""
1. FastMCP 版本问题
   - 检查 mcp 包版本: pip show mcp
   - 更新到最新版本: pip install --upgrade mcp

2. 资源路径格式问题
   - 确保路径参数格式正确
   - 检查是否有拼写错误

3. 服务器未正确启动
   - 检查服务器日志
   - 确认资源已注册

4. 客户端调用格式问题
   - 确认客户端使用正确的 URI 格式
   - 检查参数是否正确传递

调试步骤:
1. 运行服务器并查看启动日志
2. 检查是否有资源注册的日志信息
3. 使用 MCP Inspector 工具查看可用资源列表
4. 尝试使用简单的资源 URI (如 yukon://database/info)
    """)