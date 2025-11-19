"""
Vanna AI 与 PostGIS 集成 - 训练脚本
用于训练模型并将数据保存到本地 ChromaDB
"""
import os
from typing import Optional, Dict, Any

import openai
from dotenv import load_dotenv
from vanna.chromadb import ChromaDB_VectorStore
from vanna.openai import OpenAI_Chat

# 加载环境变量
load_dotenv()


class PostGISVanna(ChromaDB_VectorStore, OpenAI_Chat):
    """
    PostGIS 专用的 Vanna AI 实例
    支持配置：
    - OpenAI 官方 API
    - 兼容 OpenAI 的代理服务（如 fast.catsapi.com）
    - 其他支持 OpenAI 兼容接口的服务
    """

    def set_config(self, key, value):
        """
        兼容 0.9+ 的快捷配置入口。
        直接把键值写进 self.config 里，其它地方用的时候再读。
        """
        if not hasattr(self, "config") or self.config is None:
            self.config = {}
        self.config[key] = value

    def __init__(self, config: Optional[Dict[str, Any]] = None, model: str = "gpt-4-turbo",
        persist_directory: str = "../../yukon_db"):
        """
        初始化 PostGISVanna 实例

        Args:
            config: LLM 配置字典，支持以下参数：
                - api_key: API 密钥（优先级：参数 > 环境变量 OPENAI_API_KEY）
                - model: 模型名称（默认 gpt-4-turbo）
                - base_url: API 基础 URL（可选，用于代理或自定义服务）
            model: 默认使用的模型名称
            persist_directory: 本地存储目录
        """
        if config is None:
            config = {}

        # 初始化配置
        self.config = config.copy()
        
        # 向量库：指定本地目录，训练结果落盘
        config["path"] = persist_directory
        ChromaDB_VectorStore.__init__(self, config=config)

        # 配置 OpenAI LLM
        api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "❌ 未找到 API Key。请通过以下方式之一提供："
                "\n  1. config 参数: PostGISVanna(config={'api_key': 'sk-...'})"
                "\n  2. 环境变量: export OPENAI_API_KEY='sk-...'"
                "\n  3. .env 文件: OPENAI_API_KEY=sk-..."
            )

        # 设置模型和 API 密钥
        self.model_name = config.get('model', model)
        
        # 如果提供了 base_url，说明使用代理或自定义服务
        base_url = config.get('base_url')
        if base_url:
            print(f"✓ 使用自定义 API 端点: {base_url}")
        else:
            base_url = None
            print(f"✓ 使用 OpenAI 官方 API")
        print(f"✓ 模型: {self.model_name}")

        # 初始化 OpenAI 用于 LLM 生成
        self.client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=180,
            max_retries=3
        )
        
        OpenAI_Chat.config = config
        OpenAI_Chat.model = self.model_name
        OpenAI_Chat.temperature = config.get('temperature', 0.1)


def create_vanna_instance(config_type: str = "openai_official") -> PostGISVanna:
    """
    创建 Vanna 实例的工厂方法

    Args:
        config_type: 配置类型
            - "openai_official": OpenAI 官方 API
            - "openai_proxy": 兼容 OpenAI 的代理服务
            - "custom": 自定义配置

    Returns:
        PostGISVanna 实例
    """

    if config_type == "openai_official":
        # 官方 OpenAI API
        config = {
            'api_key': os.getenv('OPENAI_API_KEY'),
            'model': os.getenv('OPENAI_MODEL', 'gpt-4-turbo'),
        }
        print("📌 使用 OpenAI 官方 API")

    elif config_type == "openai_proxy":
        # 兼容 OpenAI 的代理服务（如 fast.catsapi.com）
        config = {
            'api_key': os.getenv('PROXY_API_KEY'),
            'model': os.getenv('PROXY_MODEL', 'gpt-3.5-turbo'),
            'base_url': os.getenv('PROXY_BASE_URL', 'https://fast.catsapi.com/v1'),
        }
        print(f"📌 使用代理服务: {config['base_url']}")

    elif config_type == "custom":
        # 自定义配置
        config = {
            'api_key': os.getenv('CUSTOM_API_KEY'),
            'model': os.getenv('CUSTOM_MODEL', 'gpt-4'),
            'base_url': os.getenv('CUSTOM_BASE_URL'),
        }
        print(f"📌 使用自定义配置")
    else:
        raise ValueError(f"❌ 未知的配置类型: {config_type}")

    return PostGISVanna(
        config=config, 
        model=config.get('model', 'gpt-4-turbo'),
        persist_directory="../../yukon_db"
    )


def train_postgis_model():
    """
    训练 PostGIS 模型的主函数
    将训练数据保存到本地 ChromaDB
    """
    print("\n" + "=" * 60)
    print("🚀 开始训练 Vanna AI 模型")
    print("=" * 60)
    
    # 初始化Vanna AI
    config_type = os.getenv('VANNA_CONFIG_TYPE', 'openai_proxy')
    vn = create_vanna_instance(config_type)
    vn.set_config("include_columns", False)
    vn.set_config("include_examples", False)
    vn.set_config("max_tokens", 3500)
    
    # 连接到数据库
    try:
        vn.connect_to_postgres(
            host=os.getenv('POSTGIS_HOST', '172.16.12.179'),
            port=int(os.getenv('POSTGIS_PORT', 15432)),
            dbname=os.getenv('POSTGIS_DATABASE', 'yukon_mcp'),
            user=os.getenv('POSTGIS_USER', 'zhangming1'),
            password=os.getenv('POSTGIS_PASSWORD', 'Huawei@123')
        )
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"⚠️  数据库连接失败: {str(e)}")
        print("   将继续进行模型训练（不使用实时数据库）")
    
    # 2. 训练模型 - DDL 阶段
    print("\n" + "=" * 60)
    print("🔧 训练模型 - DDL 阶段")
    print("=" * 60)
    
    vn.train(ddl="""
                 CREATE TABLE cities
                 (
                     id         SERIAL PRIMARY KEY,
                     name       VARCHAR(255),
                     population INTEGER,
                     geom       GEOMETRY(Point, 4326)
                 );
                 """)
    print("✓ 已注册 cities 表")
    
    vn.train(ddl="""
                 CREATE TABLE buildings
                 (
                     id     SERIAL PRIMARY KEY,
                     name   VARCHAR(255),
                     geom   GEOMETRY(Polygon, 4326),
                     height FLOAT
                 );
                 """)
    print("✓ 已注册 buildings 表")
    
    vn.train(ddl="""
                 CREATE TABLE roads
                 (
                     id    SERIAL PRIMARY KEY,
                     name  VARCHAR(255),
                     geom  GEOMETRY(LineString, 4326),
                     width FLOAT
                 );
                 """)
    print("✓ 已注册 roads 表")
    
    # 2.2. 训练模型 - 文档阶段
    print("\n" + "=" * 60)
    print("📚 训练模型 - 文档阶段")
    print("=" * 60)
    
    postgis_docs = [
        ("ST_DWithin", "ST_DWithin(geometry1, geometry2, distance) - 检查两个几何体是否在指定距离内"),
        ("ST_Buffer", "ST_Buffer(geometry, distance) - 创建围绕几何体的缓冲区"),
        ("ST_Area", "ST_Area(geometry) - 计算几何体的面积（平方度或平方米）"),
        ("ST_Centroid", "ST_Centroid(geometry) - 计算几何体的几何中心"),
        ("ST_Distance", "ST_Distance(geometry1, geometry2) - 计算两个几何体之间的最短距离"),
        ("ST_Intersection", "ST_Intersection(geometry1, geometry2) - 返回两个几何体的交集"),
        ("ST_Union", "ST_Union(geometry1, geometry2) - 返回两个几何体的并集"),
        ("ST_Contains", "ST_Contains(geometry1, geometry2) - 检查几何体1是否包含几何体2"),
        ("ST_Intersects", "ST_Intersects(geometry1, geometry2) - 检查两个几何体是否相交"),
        ("ST_AsText", "ST_AsText(geometry) - 将几何体转换为 WKT（文本）格式"),
        ("ST_AsGeoJSON", "ST_AsGeoJSON(geometry) - 将几何体转换为 GeoJSON 格式"),
        ("ST_GeomFromText", "ST_GeomFromText(wkt_string, srid) - 从 WKT 字符串创建几何体"),
        ("ST_MakePoint", "ST_MakePoint(x, y) - 从 X 和 Y 坐标创建点几何体"),
        ("ST_Length", "ST_Length(geometry) - 计算线几何体的长度"),
        ("ST_Perimeter", "ST_Perimeter(geometry) - 计算多边形的周长"),
    ]
    
    for func_name, doc in postgis_docs:
        vn.train(documentation=doc)
        print(f"✓ {func_name} 文档已添加")
    
    # 2.3. 训练模型 - SQL 示例阶段
    print("\n" + "=" * 60)
    print("💡 训练模型 - SQL 示例阶段")
    print("=" * 60)
    
    sql_examples = [
        {
            "question": "计算特定坐标多边形的面积",
            "sql": """SELECT ST_Area(geom) As area
                      FROM (SELECT 'Polygon((0 0, 100 0, 100 100, 0 100, 0 0))'::geometry as geom) as subquery;"""
        },
        {
            "question": "查找多边形的中心点",
            "sql": """SELECT ST_AsText(ST_Centroid(geom)) As centroid
                      FROM (SELECT 'Polygon((0 0, 100 0, 100 100, 0 100, 0 0))'::geometry as geom) as subquery;"""
        },
        {
            "question": "创建1000米缓冲区",
            "sql": """SELECT ST_AsText(ST_Buffer(geom::geography, 1000)::geometry) as buffer
                      FROM (SELECT 'Point(120.5 30.2)'::geometry as geom) as subquery;"""
        },
        {
            "question": "查询距离特定点500米范围内的城市",
            "sql": """SELECT c.name, ST_Distance(c.geom::geography, p.geom::geography) as distance_m
                      FROM cities c,
                           (SELECT 'Point(120.5 30.2)'::geometry as geom) p
                      WHERE ST_DWithin(c.geom::geography, p.geom::geography, 500)
                      ORDER BY distance_m;"""
        },
        {
            "question": "查找与特定道路相交的建筑物",
            "sql": """SELECT DISTINCT b.name
                      FROM buildings b,
                           roads r
                      WHERE ST_Intersects(b.geom, r.geom);"""
        },
        {
            "question": "查询包含特定点的建筑物",
            "sql": """SELECT name
                      FROM buildings
                      WHERE ST_Contains(geom, 'Point(120.5 30.2)'::geometry);"""
        },
        {
            "question": "计算建筑物之间的距离",
            "sql": """SELECT b1.name, b2.name, ST_Distance(b1.geom::geography, b2.geom::geography) as distance_m
                      FROM buildings b1,
                           buildings b2
                      WHERE b1.id < b2.id
                      ORDER BY distance_m;"""
        },
        {
            "question": "查找距离城市中心5公里范围内的建筑物",
            "sql": """SELECT b.name, ST_Distance(b.geom::geography, c.geom::geography) as distance_m
                      FROM buildings b,
                           cities c
                      WHERE c.name = '北京'
                        AND ST_DWithin(b.geom::geography, c.geom::geography, 5000)
                      ORDER BY distance_m;"""
        },
        {
            "question": "计算城市边界内的建筑物总面积",
            "sql": """SELECT SUM(ST_Area(b.geom)) as total_area
                      FROM buildings b,
                           cities c
                      WHERE c.name = '北京'
                        AND ST_Contains(c.geom::geography, b.geom::geography);"""
        },
        {
            "question": "查询所有道路的总长度",
            "sql": """SELECT SUM(ST_Length(geom::geography)) as total_length_m
                      FROM roads;"""
        },
    ]
    
    for example in sql_examples:
        vn.train(question=example["question"], sql=example["sql"])
        print(f"✓ 示例已添加: {example['question']}")
    
    print("\n" + "=" * 60)
    print("✅ 训练完成！数据已保存到本地 ChromaDB")
    print(f"   存储路径: {os.path.abspath('../../yukon_db')}")
    print("=" * 60)
    
    return vn


if __name__ == "__main__":
    try:
        vn = train_postgis_model()
        
        # 可选：测试模型
        print("\n" + "=" * 60)
        print("🤖 测试模型 - 自然语言查询")
        print("=" * 60)
        
        test_queries = [
            "查询距离坐标120.5,30.2 500米范围内的城市",
            "哪些建筑物与特定道路相交",
            "计算北京市的建筑物总面积",
        ]
        
        for query in test_queries:
            print(f"\n📝 查询: {query}")
            try:
                generated_sql = vn.generate_sql(query)
                print(f"📊 生成的 SQL:")
                print(f"   {generated_sql}")
            except Exception as e:
                print(f"❌ 错误: {str(e)}")
        
        print("\n" + "=" * 60)
        print("✅ 演示完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 训练失败: {str(e)}")
        exit(1)
