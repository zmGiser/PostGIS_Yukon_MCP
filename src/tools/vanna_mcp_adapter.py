"""
Vanna AI MCP工具适配器
通过 REST API 调用 Vanna 服务,支持本地ChromaDB存储
"""
import os
import logging
import aiohttp
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class VannaMCPAdapter:
    """
    Vanna AI MCP适配器
    通过 REST API 调用 Vanna 服务
    """
    
    def __init__(self, base_url: str = None):
        """
        初始化适配器
        
        Args:
            base_url: Vanna 服务的基础 URL,默认为 http://localhost:5000
        """
        self.base_url = base_url or os.getenv('VANNA_SERVICE_URL', 'http://localhost:5000')
        self._is_initialized = False
        
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        发起 HTTP 请求
        
        Args:
            method: HTTP 方法 (GET, POST, DELETE 等)
            endpoint: API 端点
            json_data: JSON 请求体
            
        Returns:
            响应数据
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    timeout=aiohttp.ClientTimeout(total=360)  # 增加到6分钟
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
        except aiohttp.ClientError as e:
            logger.error(f"请求失败: {str(e)}")
            return {
                "success": False,
                "error": f"连接 Vanna 服务失败: {str(e)}. 请确保服务运行在 {self.base_url}"
            }
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def initialize(
        self,
        model_name: str = "gpt-4",
        api_key: str = None,
        api_base: str = None,
        persist_directory: str = "./yukon_db"
    ) -> Dict[str, Any]:
        """
        初始化Vanna模型
        
        Args:
            model_name: LLM模型名称
            api_key: API密钥
            api_base: API基础URL
            persist_directory: 本地存储目录
            
        Returns:
            初始化结果
        """
        try:
            result = await self._make_request(
                method='POST',
                endpoint='/api/vanna/init',
                json_data={}
            )
            
            if result.get('success'):
                self._is_initialized = True
            
            return result
            
        except Exception as e:
            logger.error(f"Vanna初始化失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _ensure_initialized(self) -> Optional[Dict[str, Any]]:
        """确保模型已初始化"""
        if not self._is_initialized:
            return {
                "success": False,
                "error": "Vanna模型未初始化,请先调用vanna_init"
            }
        return None
    
    async def train_ddl_preview(self, schema: str = "public") -> Dict[str, Any]:
        """
        预览DDL训练
        
        Args:
            schema: 数据库模式名
            
        Returns:
            训练预览结果和会话ID
        """
        error = self._ensure_initialized()
        if error:
            return error
        
        return await self._make_request(
            method='POST',
            endpoint='/api/vanna/train/ddl/preview',
            json_data={"schema": schema}
        )
    
    async def train_documentation_preview(self, documentation: str) -> Dict[str, Any]:
        """
        预览文档训练
        
        Args:
            documentation: 业务文档
            
        Returns:
            训练预览结果和会话ID
        """
        error = self._ensure_initialized()
        if error:
            return error
        
        return await self._make_request(
            method='POST',
            endpoint='/api/vanna/train/documentation/preview',
            json_data={"documentation": documentation}
        )
    
    async def train_sql_example_preview(
        self,
        question: str,
        sql: str
    ) -> Dict[str, Any]:
        """
        预览SQL示例训练
        
        Args:
            question: 自然语言问题
            sql: 对应的SQL
            
        Returns:
            训练预览结果和会话ID
        """
        error = self._ensure_initialized()
        if error:
            return error
        
        return await self._make_request(
            method='POST',
            endpoint='/api/vanna/train/sql/preview',
            json_data={
                "question": question,
                "sql": sql
            }
        )
    
    async def confirm_training(self, session_id: str) -> Dict[str, Any]:
        """
        确认并执行训练
        
        Args:
            session_id: 训练会话ID
            
        Returns:
            训练执行结果
        """
        error = self._ensure_initialized()
        if error:
            return error
        
        return await self._make_request(
            method='POST',
            endpoint='/api/vanna/train/confirm',
            json_data={"session_id": session_id}
        )
    
    async def cancel_training(self, session_id: str) -> Dict[str, Any]:
        """
        取消训练会话
        
        Args:
            session_id: 训练会话ID
            
        Returns:
            取消结果
        """
        return await self._make_request(
            method='POST',
            endpoint='/api/vanna/train/cancel',
            json_data={"session_id": session_id}
        )
    
    async def generate_sql_with_preview(
        self,
        question: str,
        allow_llm_to_see_data: bool = False
    ) -> Dict[str, Any]:
        """
        生成SQL(带预览)
        
        Args:
            question: 自然语言问题
            allow_llm_to_see_data: 是否允许LLM查看数据
            
        Returns:
            生成的SQL
        """
        error = self._ensure_initialized()
        if error:
            return error
        
        return await self._make_request(
            method='POST',
            endpoint='/api/vanna/generate_sql',
            json_data={
                "question": question,
                "allow_llm_to_see_data": allow_llm_to_see_data
            }
        )
    
    async def execute_sql(
        self,
        sql: str,
        confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        执行SQL(需要确认)
        
        Args:
            sql: SQL语句
            confirmed: 是否已确认
            
        Returns:
            执行结果
        """
        error = self._ensure_initialized()
        if error:
            return error
        
        return await self._make_request(
            method='POST',
            endpoint='/api/vanna/execute_sql',
            json_data={
                "sql": sql,
                "confirmed": confirmed
            }
        )
    
    async def get_training_data(self) -> Dict[str, Any]:
        """
        获取训练数据
        
        Returns:
            训练数据列表
        """
        error = self._ensure_initialized()
        if error:
            return error
        
        return await self._make_request(
            method='GET',
            endpoint='/api/vanna/training_data'
        )
    
    async def remove_training_data(self, id: str) -> Dict[str, Any]:
        """
        删除训练数据
        
        Args:
            id: 训练数据ID
            
        Returns:
            删除结果
        """
        error = self._ensure_initialized()
        if error:
            return error
        
        return await self._make_request(
            method='DELETE',
            endpoint=f'/api/vanna/training_data/{id}'
        )


# Vanna 可用性标志
VANNA_AVAILABLE = True

# 全局适配器实例
_vanna_mcp_adapter: Optional[VannaMCPAdapter] = None


def get_vanna_mcp_adapter() -> VannaMCPAdapter:
    """获取全局Vanna MCP适配器实例"""
    global _vanna_mcp_adapter
    if _vanna_mcp_adapter is None:
        _vanna_mcp_adapter = VannaMCPAdapter()
    return _vanna_mcp_adapter