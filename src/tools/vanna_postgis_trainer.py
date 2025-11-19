"""
Vanna PostGIS训练器
提供用户确认机制的训练工具,通过 REST API 调用 Vanna 服务
"""
import logging
from typing import Dict, Any
from .vanna_mcp_adapter import get_vanna_mcp_adapter

logger = logging.getLogger(__name__)


async def vanna_initialize(
    model_name: str = "gpt-4",
    api_key: str = None,
    api_base: str = None,
    embedding_model: str = "text-embedding-3-small"
) -> Dict[str, Any]:
    """
    初始化本地Vanna模型
    
    使用您自己的LLM API(如OpenAI、Claude等),不依赖Vanna云服务。
    训练数据将完全保存在本地ChromaDB中。
    
    Args:
        model_name: LLM模型名称(如gpt-4, claude-3-opus等)
        api_key: 您的LLM API密钥(或设置OPENAI_API_KEY环境变量)
        api_base: API基础URL(可选,用于自定义端点)
        embedding_model: 嵌入模型名称
        
    Returns:
        初始化结果
        
    示例:
        # 使用OpenAI
        vanna_initialize(model_name="gpt-4", api_key="sk-...")
        
        # 使用自定义端点(如Azure OpenAI)
        vanna_initialize(
            model_name="gpt-4",
            api_key="your-key",
            api_base="https://your-endpoint.openai.azure.com/v1"
        )
    """
    adapter = get_vanna_mcp_adapter()
    return await adapter.initialize(
        model_name=model_name,
        api_key=api_key,
        api_base=api_base
    )


async def vanna_train_ddl_preview(schema: str = "public") -> Dict[str, Any]:
    """
    预览DDL训练 - 不实际训练,只显示将要训练的内容
    
    Args:
        schema: 数据库模式
        
    Returns:
        预览结果和会话ID
    """
    try:
        adapter = get_vanna_mcp_adapter()
        return await adapter.train_ddl_preview(schema)
        
    except Exception as e:
        logger.error(f"DDL训练预览失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def vanna_train_documentation_preview(
    documentation: str
) -> Dict[str, Any]:
    """
    预览文档训练
    
    Args:
        documentation: 文档内容
        
    Returns:
        预览结果和会话ID
    """
    try:
        adapter = get_vanna_mcp_adapter()
        return await adapter.train_documentation_preview(documentation)
        
    except Exception as e:
        logger.error(f"文档训练预览失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def vanna_train_sql_example_preview(
    question: str,
    sql: str
) -> Dict[str, Any]:
    """
    预览SQL示例训练
    
    Args:
        question: 自然语言问题
        sql: SQL语句
        
    Returns:
        预览结果和会话ID
    """
    try:
        adapter = get_vanna_mcp_adapter()
        return await adapter.train_sql_example_preview(question, sql)
        
    except Exception as e:
        logger.error(f"SQL示例训练预览失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def vanna_confirm_training(session_id: str) -> Dict[str, Any]:
    """
    确认并执行训练
    
    Args:
        session_id: 训练会话ID
        
    Returns:
        训练结果
    """
    try:
        adapter = get_vanna_mcp_adapter()
        return await adapter.confirm_training(session_id)
        
    except Exception as e:
        logger.error(f"训练执行失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def vanna_cancel_training(session_id: str) -> Dict[str, Any]:
    """
    取消训练会话
    
    Args:
        session_id: 训练会话ID
        
    Returns:
        取消结果
    """
    try:
        adapter = get_vanna_mcp_adapter()
        return await adapter.cancel_training(session_id)
        
    except Exception as e:
        logger.error(f"取消训练失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def vanna_generate_sql_with_preview(
    question: str,
    allow_llm_to_see_data: bool = False
) -> Dict[str, Any]:
    """
    生成SQL(带预览,不直接执行)
    
    Args:
        question: 自然语言问题
        allow_llm_to_see_data: 是否允许查看数据
        
    Returns:
        生成的SQL和会话ID
    """
    try:
        adapter = get_vanna_mcp_adapter()
        result = await adapter.generate_sql_with_preview(question, allow_llm_to_see_data)
        
        if result.get("success"):
            result["next_step"] = f"execute_sql(sql=\"{result.get('generated_sql')}\", confirmed=True)"
        
        return result
        
    except Exception as e:
        logger.error(f"SQL生成失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }