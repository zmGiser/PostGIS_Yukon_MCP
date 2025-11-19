"""
测试 asyncpg 连接
"""
import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

async def test_asyncpg_connection():
    """测试 asyncpg 连接"""
    
    # 方法1: 使用连接字符串
    print("\n=== 测试方法1: 使用连接字符串 ===")
    host = os.getenv("POSTGIS_HOST", "172.16.12.179")
    port = os.getenv("POSTGIS_PORT", "15432")
    database = os.getenv("POSTGIS_DATABASE", "yukon_mcp")
    user = os.getenv("POSTGIS_USER", "zhangming1")
    password = os.getenv("POSTGIS_PASSWORD", "")
    
    conn_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    print(f"连接字符串: {conn_string}")
    
    try:
        conn = await asyncpg.connect(conn_string)
        version = await conn.fetchval("SELECT version()")
        print(f"[OK] 连接成功")
        print(f"  数据库版本: {version}")
        await conn.close()
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        print(f"  错误类型: {type(e).__name__}")
    
    # 方法2: 使用参数
    print("\n=== 测试方法2: 使用参数 ===")
    try:
        conn = await asyncpg.connect(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password
        )
        version = await conn.fetchval("SELECT version()")
        print(f"[OK] 连接成功")
        print(f"  数据库版本: {version}")
        await conn.close()
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        print(f"  错误类型: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_asyncpg_connection())