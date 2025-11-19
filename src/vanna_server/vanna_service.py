"""
Vanna AI Flask REST API 服务
提供完整的训练和查询接口,支持本地 ChromaDB 存储
"""
import openai
from flask import Flask, request, jsonify
from vanna.chromadb import ChromaDB_VectorStore
from vanna.openai import OpenAI_Chat
import os
import pandas as pd
from dotenv import load_dotenv
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import asyncpg
import asyncio

load_dotenv()

# 自定义 Vanna 类,使用本地 ChromaDB 存储
class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        
        # 配置超时和重试策略
        from httpx import Timeout
        self.client = openai.OpenAI(
            base_url=config.get('base_url'),
            api_key=config.get('api_key'),
            timeout=Timeout(
                connect=30.0,  # 连接超时30秒
                read=120.0,    # 读取超时120秒
                write=30.0,    # 写入超时30秒
                pool=30.0      # 连接池超时30秒
            ),
            max_retries=1  # 减少重试次数避免过长等待
        )
        OpenAI_Chat.config = config
        OpenAI_Chat.model = config.get('model')
        OpenAI_Chat.temperature = config.get('temperature', 0.1)


# 初始化 Flask 应用
app = Flask(__name__)

# 全局变量
vn = None
training_sessions = {}


class TrainingSession:
    """训练会话管理"""
    def __init__(self, session_id: str, training_type: str, data: Dict[str, Any]):
        self.session_id = session_id
        self.training_type = training_type
        self.data = data
        self.created_at = datetime.now()
        self.status = "pending"


def init_vanna():
    """初始化 Vanna,加载本地训练数据"""
    global vn
    
    # 检查本地数据是否存在
    persist_dir = os.path.abspath('./yukon_db')
    if not os.path.exists(persist_dir):
        os.makedirs(persist_dir, exist_ok=True)
        print(f"✓ 创建训练数据目录: {persist_dir}")
    
    # 加载本地训练数据
    vn = MyVanna(config={
        'path': persist_dir,
        'api_key': os.getenv('PROXY_API_KEY') or os.getenv('OPENAI_API_KEY'),
        'model': os.getenv('PROXY_MODEL', 'gpt-3.5-turbo'),
        'base_url': os.getenv('PROXY_BASE_URL', 'https://fast.catsapi.com/v1'),
    })
    
    # 连接到数据库
    try:
        vn.connect_to_postgres(
            host=os.getenv('POSTGIS_HOST', '172.16.12.179'),
            port=int(os.getenv('POSTGIS_PORT', 15432)),
            dbname=os.getenv('POSTGIS_DATABASE', 'yukon_mcp'),
            user=os.getenv('POSTGIS_USER', 'zhangming1'),
            password=os.getenv('POSTGIS_PASSWORD', 'Huawei@123')
        )
        return True, f"Vanna 初始化成功,训练数据目录: {persist_dir}"
    except Exception as e:
        return False, f"数据库连接失败: {str(e)}"


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'message': 'Vanna 服务运行中',
        'data_path': os.path.abspath('./yukon_db'),
        'initialized': vn is not None
    })


@app.route('/api/vanna/init', methods=['POST'])
def initialize():
    """初始化 Vanna 并加载本地训练数据"""
    success, message = init_vanna()
    return jsonify({
        'success': success,
        'message': message
    }), 200 if success else 500


@app.route('/api/vanna/train/ddl/preview', methods=['POST'])
def train_ddl_preview():
    """预览 DDL 训练"""
    global vn
    
    if vn is None:
        return jsonify({
            'success': False,
            'error': '请先调用 /api/vanna/init 接口初始化 Vanna'
        }), 400
    
    data = request.get_json()
    schema = data.get('schema', 'public')
    
    try:
        # 获取数据库配置
        db_config = {
            'host': os.getenv('POSTGIS_HOST', '172.16.12.179'),
            'port': int(os.getenv('POSTGIS_PORT', 15432)),
            'database': os.getenv('POSTGIS_DATABASE', 'yukon_mcp'),
            'user': os.getenv('POSTGIS_USER', 'zhangming1'),
            'password': os.getenv('POSTGIS_PASSWORD', 'Huawei@123')
        }
        
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def get_ddl_info():
            conn = await asyncpg.connect(**db_config)
            
            # 获取所有空间表
            query = """
                SELECT 
                    f_table_name,
                    f_geometry_column,
                    type,
                    srid
                FROM geometry_columns
                WHERE f_table_schema = $1
            """
            
            tables = await conn.fetch(query, schema)
            
            if not tables:
                await conn.close()
                return None, f"在模式 '{schema}' 中未找到空间表"
            
            # 构建DDL信息
            ddl_list = []
            for table in tables:
                table_name = table['f_table_name']
                
                # 获取表的CREATE语句(简化版)
                ddl_query = f"""
                    SELECT 
                        'CREATE TABLE {schema}.' || $2 || ' (' ||
                        string_agg(
                            column_name || ' ' || data_type,
                            ', '
                        ) || ');' as ddl
                    FROM information_schema.columns
                    WHERE table_schema = $1 AND table_name = $2
                    GROUP BY table_schema, table_name
                """
                
                ddl_result = await conn.fetchrow(ddl_query, schema, table_name)
                
                if ddl_result:
                    # 添加PostGIS特定信息
                    postgis_info = f"""
-- PostGIS空间表: {schema}.{table_name}
-- 几何列: {table['f_geometry_column']}
-- 几何类型: {table['type']}
-- SRID: {table['srid']}
"""
                    full_ddl = postgis_info + "\n" + ddl_result['ddl']
                    ddl_list.append({
                        "table": f"{schema}.{table_name}",
                        "ddl": full_ddl
                    })
            
            await conn.close()
            return ddl_list, None
        
        ddl_list, error = loop.run_until_complete(get_ddl_info())
        loop.close()
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 400
        
        # 创建训练会话
        session_id = f"training_{uuid.uuid4().hex[:8]}"
        session = TrainingSession(
            session_id=session_id,
            training_type="ddl",
            data={"schema": schema, "ddl_list": ddl_list}
        )
        training_sessions[session_id] = session
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "training_type": "ddl",
            "schema": schema,
            "table_count": len(ddl_list),
            "preview": ddl_list,
            "message": f"将训练 {len(ddl_list)} 个表的DDL,请使用 /api/vanna/train/confirm 确认"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/vanna/train/documentation/preview', methods=['POST'])
def train_documentation_preview():
    """预览文档训练"""
    global vn
    
    if vn is None:
        return jsonify({
            'success': False,
            'error': '请先调用 /api/vanna/init 接口初始化 Vanna'
        }), 400
    
    data = request.get_json()
    documentation = data.get('documentation')
    
    if not documentation:
        return jsonify({
            'success': False,
            'error': '请提供 documentation 参数'
        }), 400
    
    try:
        # 创建训练会话
        session_id = f"training_{uuid.uuid4().hex[:8]}"
        session = TrainingSession(
            session_id=session_id,
            training_type="documentation",
            data={"documentation": documentation}
        )
        training_sessions[session_id] = session
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "training_type": "documentation",
            "preview": {
                "documentation": documentation,
                "length": len(documentation)
            },
            "message": "请检查文档内容,使用 /api/vanna/train/confirm 确认"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/vanna/train/sql/preview', methods=['POST'])
def train_sql_preview():
    """预览SQL示例训练"""
    global vn
    
    if vn is None:
        return jsonify({
            'success': False,
            'error': '请先调用 /api/vanna/init 接口初始化 Vanna'
        }), 400
    
    data = request.get_json()
    question = data.get('question')
    sql = data.get('sql')
    
    if not question or not sql:
        return jsonify({
            'success': False,
            'error': '请提供 question 和 sql 参数'
        }), 400
    
    try:
        # 创建训练会话
        session_id = f"training_{uuid.uuid4().hex[:8]}"
        session = TrainingSession(
            session_id=session_id,
            training_type="sql_example",
            data={"question": question, "sql": sql}
        )
        training_sessions[session_id] = session
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "training_type": "sql_example",
            "preview": {
                "question": question,
                "sql": sql
            },
            "message": "请检查SQL示例,使用 /api/vanna/train/confirm 确认"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/vanna/train/confirm', methods=['POST'])
def confirm_training():
    """确认并执行训练"""
    global vn
    
    if vn is None:
        return jsonify({
            'success': False,
            'error': '请先调用 /api/vanna/init 接口初始化 Vanna'
        }), 400
    
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({
            'success': False,
            'error': '请提供 session_id 参数'
        }), 400
    
    try:
        # 获取训练会话
        session = training_sessions.get(session_id)
        if not session:
            return jsonify({
                "success": False,
                "error": f"训练会话 {session_id} 不存在"
            }), 400
        
        if session.status == "completed":
            return jsonify({
                "success": False,
                "error": "训练会话已完成"
            }), 400
        
        # 执行训练
        if session.training_type == "ddl":
            ddl_list = session.data["ddl_list"]
            for item in ddl_list:
                vn.train(ddl=item['ddl'])
            
            session.status = "completed"
            return jsonify({
                "success": True,
                "session_id": session_id,
                "training_type": "ddl",
                "trained_count": len(ddl_list),
                "message": f"成功训练 {len(ddl_list)} 个表的DDL"
            })
            
        elif session.training_type == "documentation":
            doc = session.data["documentation"]
            try:
                vn.train(documentation=doc)
                
                session.status = "completed"
                return jsonify({
                    "success": True,
                    "session_id": session_id,
                    "training_type": "documentation",
                    "message": "文档训练成功"
                })
            except Exception as train_error:
                return jsonify({
                    "success": False,
                    "error": f"训练失败: {str(train_error)}",
                    "session_id": session_id
                }), 500
            
        elif session.training_type == "sql_example":
            question = session.data["question"]
            sql = session.data["sql"]
            vn.train(question=question, sql=sql)
            
            session.status = "completed"
            return jsonify({
                "success": True,
                "session_id": session_id,
                "training_type": "sql_example",
                "message": "SQL示例训练成功"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"未知的训练类型: {session.training_type}"
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/vanna/train/cancel', methods=['POST'])
def cancel_training():
    """取消训练会话"""
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({
            'success': False,
            'error': '请提供 session_id 参数'
        }), 400
    
    try:
        if session_id in training_sessions:
            del training_sessions[session_id]
            return jsonify({
                "success": True,
                "session_id": session_id,
                "message": "训练会话已取消"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"训练会话 {session_id} 不存在"
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/vanna/generate_sql', methods=['POST'])
def generate_sql_api():
    """生成 SQL(带预览)"""
    global vn
    
    if vn is None:
        return jsonify({
            'success': False,
            'error': '请先调用 /api/vanna/init 接口初始化 Vanna'
        }), 400
    
    data = request.get_json()
    question = data.get('question')
    allow_llm_to_see_data = data.get('allow_llm_to_see_data', False)
    
    if not question:
        return jsonify({
            'success': False,
            'error': '请提供 question 参数'
        }), 400
    
    try:
        sql = vn.generate_sql(
            question=question,
            allow_llm_to_see_data=allow_llm_to_see_data
        )
        
        return jsonify({
            'success': True,
            'question': question,
            'generated_sql': sql,
            'warning': '⚠️ 请检查SQL后使用 /api/vanna/execute_sql 执行(需设置confirmed=True)'
        })
    except TimeoutError as e:
        return jsonify({
            'success': False,
            'error': f'API请求超时: {str(e)}',
            'suggestion': '请检查网络连接或API配置'
        }), 504
    except Exception as e:
        error_msg = str(e)
        if 'ssl' in error_msg.lower() or 'timeout' in error_msg.lower():
            return jsonify({
                'success': False,
                'error': f'网络连接问题: {error_msg}',
                'suggestion': '请检查网络连接、代理设置或API密钥'
            }), 504
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/api/vanna/execute_sql', methods=['POST'])
def execute_sql_api():
    """执行SQL(需要确认)"""
    global vn
    
    if vn is None:
        return jsonify({
            'success': False,
            'error': '请先调用 /api/vanna/init 接口初始化 Vanna'
        }), 400
    
    data = request.get_json()
    sql = data.get('sql')
    confirmed = data.get('confirmed', False)
    
    if not sql:
        return jsonify({
            'success': False,
            'error': '请提供 sql 参数'
        }), 400
    
    if not confirmed:
        return jsonify({
            'success': False,
            'error': '执行SQL需要确认,请设置 confirmed=True'
        }), 400
    
    try:
        # 执行 SQL
        df = vn.run_sql(sql)
        
        # 将 DataFrame 转换为字典列表
        result_data = df.to_dict('records') if not df.empty else []
        
        return jsonify({
            'success': True,
            'sql': sql,
            'data': result_data,
            'row_count': len(result_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'执行SQL时出错: {str(e)}'
        }), 500


@app.route('/api/vanna/training_data', methods=['GET'])
def get_training_data():
    """获取训练数据"""
    global vn
    
    if vn is None:
        return jsonify({
            'success': False,
            'error': '请先调用 /api/vanna/init 接口初始化 Vanna'
        }), 400
    
    try:
        training_data = vn.get_training_data()
        
        # 处理DataFrame或None的情况
        if training_data is None:
            data_list = []
        elif hasattr(training_data, 'to_dict'):
            # DataFrame
            data_list = training_data.to_dict('records')
        elif isinstance(training_data, list):
            data_list = training_data
        else:
            data_list = []
        
        return jsonify({
            'success': True,
            'count': len(data_list),
            'training_data': data_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/vanna/training_data/<data_id>', methods=['DELETE'])
def remove_training_data(data_id):
    """删除训练数据"""
    global vn
    
    if vn is None:
        return jsonify({
            'success': False,
            'error': '请先调用 /api/vanna/init 接口初始化 Vanna'
        }), 400
    
    try:
        vn.remove_training_data(id=data_id)
        
        return jsonify({
            'success': True,
            'message': f'训练数据 {data_id} 已删除'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Vanna 服务启动中...")
    print("=" * 60)
    
    # 自动初始化
    success, message = init_vanna()
    print(f"\n初始化结果: {message}\n")
    
    if success:
        print("服务已启动,可用接口:")
        print("  - GET  /health                              - 健康检查")
        print("  - POST /api/vanna/init                      - 初始化Vanna")
        print("  - POST /api/vanna/train/ddl/preview         - 预览DDL训练")
        print("  - POST /api/vanna/train/documentation/preview - 预览文档训练")
        print("  - POST /api/vanna/train/sql/preview         - 预览SQL示例训练")
        print("  - POST /api/vanna/train/confirm             - 确认并执行训练")
        print("  - POST /api/vanna/train/cancel              - 取消训练会话")
        print("  - POST /api/vanna/generate_sql              - 生成SQL")
        print("  - POST /api/vanna/execute_sql               - 执行SQL")
        print("  - GET  /api/vanna/training_data             - 获取训练数据")
        print("  - DELETE /api/vanna/training_data/<id>      - 删除训练数据")
        print("\n示例请求:")
        print('  curl -X POST http://localhost:5000/api/vanna/generate_sql \\')
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'{"question": "查询所有城市"}\'')
    else:
        print("警告: 初始化失败")
    
    print("\n" + "=" * 60)
    
    # 启动服务
    app.run(host='0.0.0.0', port=5000, debug=False)
