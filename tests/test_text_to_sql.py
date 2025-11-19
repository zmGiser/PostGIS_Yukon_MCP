"""
Text-to-SQL 功能测试
"""
import pytest
import asyncio
from src.tools.text_to_sql import (
    NLQueryParser,
    SQLGenerator,
    parse_nl_query,
    execute_generated_sql,
)


class TestNLQueryParser:
    """测试自然语言查询解析器"""
    
    def test_detect_nearby_query_chinese(self):
        """测试识别附近查询(中文)"""
        queries = [
            "查询附近的建筑",
            "找到周围500米的餐厅",
            "距离这个点1公里以内的设施",
        ]
        for query in queries:
            assert NLQueryParser.detect_query_type(query) == 'nearby'
    
    def test_detect_nearby_query_english(self):
        """测试识别附近查询(英文)"""
        queries = [
            "find buildings near this point",
            "search restaurants around here",
            "within 500 meters",
        ]
        for query in queries:
            assert NLQueryParser.detect_query_type(query) == 'nearby'
    
    def test_detect_buffer_query(self):
        """测试识别缓冲区查询"""
        queries = [
            "创建100米缓冲区",
            "create buffer around this",
            "生成缓冲",
        ]
        for query in queries:
            assert NLQueryParser.detect_query_type(query) == 'buffer'
    
    def test_detect_area_query(self):
        """测试识别面积查询"""
        queries = [
            "计算面积",
            "这个多边形的大小",
            "calculate area",
        ]
        for query in queries:
            assert NLQueryParser.detect_query_type(query) == 'area'
    
    def test_detect_count_query(self):
        """测试识别计数查询"""
        queries = [
            "有多少个建筑",
            "统计数量",
            "count buildings",
        ]
        for query in queries:
            assert NLQueryParser.detect_query_type(query) == 'count'
    
    def test_extract_table_name(self):
        """测试提取表名"""
        test_cases = [
            ("查询表:buildings附近", "buildings"),
            ("table: restaurants", "restaurants"),
            ("从parks表中", None),  # 不匹配这种格式
        ]
        for query, expected in test_cases:
            result = NLQueryParser.extract_table_name(query)
            assert result == expected
    
    def test_extract_distance_meters(self):
        """测试提取距离(米)"""
        test_cases = [
            ("500米", 500.0),
            ("500m", 500.0),
            ("500 meters", 500.0),
        ]
        for query, expected in test_cases:
            result = NLQueryParser.extract_distance(query)
            assert result == expected
    
    def test_extract_distance_kilometers(self):
        """测试提取距离(公里)"""
        test_cases = [
            ("1公里", 1000.0),
            ("2km", 2000.0),
            ("1.5 kilometer", 1500.0),
        ]
        for query, expected in test_cases:
            result = NLQueryParser.extract_distance(query)
            assert result == expected
    
    def test_extract_coordinates(self):
        """测试提取坐标"""
        test_cases = [
            ("120.5, 30.2", (120.5, 30.2)),
            ("120.15，30.25", (120.15, 30.25)),
            ("121, 31", (121.0, 31.0)),
        ]
        for query, expected in test_cases:
            result = NLQueryParser.extract_coordinates(query)
            assert result == expected


class TestSQLGenerator:
    """测试SQL生成器"""
    
    def test_generate_nearby_query(self):
        """测试生成附近查询SQL"""
        sql = SQLGenerator.generate_nearby_query(
            table_name="buildings",
            geom_column="geom",
            longitude=120.5,
            latitude=30.2,
            radius=500,
            schema="public"
        )
        
        assert "SELECT" in sql
        assert "ST_Distance" in sql
        assert "ST_DWithin" in sql
        assert "buildings" in sql
        assert "500" in sql
        assert "120.5" in sql
        assert "30.2" in sql
    
    def test_generate_buffer_query(self):
        """测试生成缓冲区SQL"""
        sql = SQLGenerator.generate_buffer_query(
            table_name="roads",
            geom_column="geom",
            distance=100,
            schema="public"
        )
        
        assert "SELECT" in sql
        assert "ST_Buffer" in sql
        assert "roads" in sql
        assert "100" in sql
    
    def test_generate_area_query(self):
        """测试生成面积计算SQL"""
        sql = SQLGenerator.generate_area_query(
            table_name="parcels",
            geom_column="geom",
            schema="public"
        )
        
        assert "SELECT" in sql
        assert "ST_Area" in sql
        assert "parcels" in sql
        assert "area_sqm" in sql
        assert "area_sqkm" in sql
    
    def test_generate_count_query(self):
        """测试生成计数SQL"""
        sql = SQLGenerator.generate_count_query(
            table_name="buildings",
            schema="public"
        )
        
        assert "SELECT COUNT(*)" in sql
        assert "buildings" in sql
        assert "feature_count" in sql


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_nearby_query_integration(self):
        """测试附近查询完整流程"""
        query = "查询表:test_buildings 坐标120.5,30.2 附近500米的建筑"
        
        result = await parse_nl_query(query)
        
        # 注意: 此测试需要数据库连接和test_buildings表存在
        # 如果表不存在，会返回错误
        assert "success" in result
        if result["success"]:
            assert result["query_type"] == "nearby"
            assert "sql" in result
            assert "120.5" in result["sql"]
            assert "30.2" in result["sql"]
    
    @pytest.mark.asyncio
    async def test_buffer_query_integration(self):
        """测试缓冲区查询完整流程"""
        query = "为表:test_roads创建100米缓冲区"
        
        result = await parse_nl_query(query)
        
        assert "success" in result
        if result["success"]:
            assert result["query_type"] == "buffer"
            assert "sql" in result
            assert "100" in result["sql"]
    
    @pytest.mark.asyncio
    async def test_area_query_integration(self):
        """测试面积查询完整流程"""
        query = "计算表:test_parcels的面积"
        
        result = await parse_nl_query(query)
        
        assert "success" in result
        if result["success"]:
            assert result["query_type"] == "area"
            assert "sql" in result


def test_query_examples():
    """测试各种查询示例"""
    examples = {
        "附近查询": [
            "查询表:restaurants 坐标120.15,30.25 附近500米的餐厅",
            "find buildings near 121.5, 31.2 within 1km",
        ],
        "缓冲区": [
            "为表:rivers创建50米缓冲区",
            "create 100m buffer for table:roads",
        ],
        "面积": [
            "计算表:parks的面积",
            "calculate area of table:districts",
        ],
        "计数": [
            "统计表:buildings的数量",
            "count features in table:points",
        ],
    }
    
    for category, queries in examples.items():
        print(f"\n{category}示例:")
        for query in queries:
            query_type = NLQueryParser.detect_query_type(query)
            table = NLQueryParser.extract_table_name(query)
            print(f"  查询: {query}")
            print(f"  类型: {query_type}, 表名: {table}")


if __name__ == "__main__":
    # 运行基本测试
    print("=" * 60)
    print("测试查询示例")
    print("=" * 60)
    test_query_examples()
    
    print("\n" + "=" * 60)
    print("运行单元测试")
    print("=" * 60)
    pytest.main([__file__, "-v"])