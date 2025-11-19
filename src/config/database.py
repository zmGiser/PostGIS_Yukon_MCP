"""
数据库配置模块
管理 GaussDB/PostGIS 数据库连接配置
使用 psycopg2 进行连接
"""
import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """数据库配置类"""
    
    def __init__(self):
        """初始化数据库配置"""
        self.host = os.getenv("POSTGIS_HOST", "localhost")
        self.port = int(os.getenv("POSTGIS_PORT", "5432"))
        self.database = os.getenv("POSTGIS_DATABASE", "gis_database")
        self.user = os.getenv("POSTGIS_USER", "postgres")
        self.password = os.getenv("POSTGIS_PASSWORD", "")
        self.sslmode = os.getenv("POSTGIS_SSLMODE", "prefer")
        
        # 连接池
        self._connection_pool: Optional[pool.SimpleConnectionPool] = None
        self._is_connected = False
    
    def get_connection_dict(self) -> Dict[str, Any]:
        """
        获取数据库连接字典
        
        Returns:
            包含连接参数的字典
        """
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
        }
    
    def get_connection_string(self) -> str:
        """
        获取数据库连接字符串
        
        Returns:
            PostgreSQL 连接字符串
        """
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.sslmode}"
        )
    
    def get_async_connection_string(self) -> str:
        """
        获取异步数据库连接字符串
        
        Returns:
            asyncpg 连接字符串
        """
        # asyncpg 需要明确指定 sslmode 参数
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.sslmode}"
        )


    def initialize_pool(self, min_conn: int = 1, max_conn: int = 10):
        """
        初始化连接池
        
        Args:
            min_conn: 最小连接数
            max_conn: 最大连接数
        """
        try:
            if self._connection_pool is None:
                self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    min_conn,
                    max_conn,
                    **self.get_connection_dict(),
                    sslmode=self.sslmode
                )
                self._is_connected = True
                logger.info("数据库连接池初始化成功")
        except Exception as e:
            logger.error(f"初始化连接池失败: {str(e)}")
            self._is_connected = False
            raise
    
    def get_connection(self):
        """
        从连接池获取连接
        
        Returns:
            数据库连接对象
        """
        if not self._is_connected or self._connection_pool is None:
            logger.warning("连接池未初始化，正在初始化...")
            self.initialize_pool()
        
        try:
            conn = self._connection_pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"获取数据库连接失败: {str(e)}")
            raise
    
    def return_connection(self, conn):
        """
        归还连接到连接池
        
        Args:
            conn: 数据库连接对象
        """
        if self._connection_pool is not None:
            self._connection_pool.putconn(conn)
    
    def close_all_connections(self):
        """关闭所有连接"""
        if self._connection_pool is not None:
            self._connection_pool.closeall()
            self._is_connected = False
            logger.info("所有数据库连接已关闭")
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._is_connected
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            连接是否成功
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            self.return_connection(conn)
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            return False


# 全局配置实例
db_config = DatabaseConfig()