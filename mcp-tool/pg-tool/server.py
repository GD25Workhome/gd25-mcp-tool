#!/usr/bin/env python3
"""
PostgreSQL MCP 服务器主文件

说明：
这是 MCP 服务器的入口点，负责：
1. 初始化 MCP 服务器
2. 注册工具（Tools）和资源（Resources）
3. 处理来自 Cursor 的请求
4. 通过 stdio 与 Cursor 通信

运行方式：
python server.py

或者在 Cursor 的 MCP 配置中直接调用此文件
"""

import os
import sys
import asyncio
import json
import logging
from typing import Any, Sequence
from dotenv import load_dotenv

# 加载环境变量（从 .env 文件）
load_dotenv()

# 配置日志记录
# 日志级别可以通过环境变量 LOG_LEVEL 设置（默认 INFO）
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stderr  # 输出到 stderr，避免干扰 MCP 通信
)

logger = logging.getLogger('postgres-mcp-server')

# MCP SDK 导入
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, Resource, TextContent, ImageContent, EmbeddedResource, Prompt
except ImportError as e:
    # 如果 MCP SDK 导入失败，提供清晰的错误信息
    logger.error(f"无法导入 MCP SDK: {e}")
    print(
        "错误：无法导入 MCP SDK。请确保已安装依赖：\n"
        "pip install -r requirements.txt",
        file=sys.stderr
    )
    sys.exit(1)

from database import DatabaseManager
from models import QueryInput, QueryResult, TableSchema


# 初始化数据库管理器
database_url = os.getenv('DATABASE_URL')
if not database_url:
    logger.error("未设置 DATABASE_URL 环境变量")
    print(
        "错误：未设置 DATABASE_URL 环境变量。\n"
        "请设置 PostgreSQL 连接字符串，例如：\n"
        "export DATABASE_URL='postgresql://user:password@localhost:5432/database'",
        file=sys.stderr
    )
    sys.exit(1)

logger.info("初始化数据库管理器")
db_manager = DatabaseManager(database_url)

# 创建 MCP 服务器实例
# 说明：Server 是 MCP SDK 的核心类，用于处理与 Cursor 的通信
app = Server("postgres-mcp-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    列出服务器提供的所有工具
    
    说明：
    - 工具（Tools）是 MCP 服务器暴露给 Cursor 的可执行操作
    - Cursor 可以调用这些工具来执行特定任务
    - 返回工具列表，每个工具包含名称、描述和输入参数定义
    
    返回：
    - Tool 对象列表
    """
    return [
        Tool(
            name="query",
            description=(
                "执行 SQL 查询。默认只允许 SELECT 查询（只读）。"
                "要启用写操作（INSERT/UPDATE/DELETE），请设置环境变量 "
                "DANGEROUSLY_ALLOW_WRITE_OPS=true"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "要执行的 SQL 查询语句",
                        "examples": ["SELECT * FROM users LIMIT 10"]
                    }
                },
                "required": ["sql"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """
    处理工具调用请求
    
    说明：
    - 当 Cursor 调用工具时，这个函数会被执行
    - 根据工具名称（name）执行相应的操作
    - 参数（arguments）是 Cursor 传递的输入数据
    
    参数：
    - name: 工具名称（如 "query"）
    - arguments: 工具参数（字典格式）
    
    返回：
    - 内容列表（TextContent/ImageContent/EmbeddedResource）
    """
    if name == "query":
        # 验证输入参数
        try:
            query_input = QueryInput(**arguments)
            logger.info(f"执行查询: {query_input.sql[:100]}...")  # 只记录前100个字符
        except Exception as e:
            logger.error(f"参数验证错误: {e}", exc_info=True)
            return [
                TextContent(
                    type="text",
                    text=f"参数验证错误: {str(e)}"
                )
            ]
        
        # 执行查询
        try:
            result = db_manager.execute_query(query_input.sql)
            logger.info(f"查询成功，返回 {result.row_count} 行")
            
            # 将结果转换为 JSON 字符串返回
            result_dict = {
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count
            }
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result_dict, indent=2, ensure_ascii=False)
                )
            ]
        except ValueError as e:
            # 业务逻辑错误（如写操作被禁用）
            logger.warning(f"查询被拒绝: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"查询执行错误: {str(e)}"
                )
            ]
        except Exception as e:
            # 其他错误
            logger.error(f"查询执行错误: {e}", exc_info=True)
            return [
                TextContent(
                    type="text",
                    text=f"查询执行错误: {str(e)}"
                )
            ]
    else:
        return [
            TextContent(
                type="text",
                text=f"未知工具: {name}"
            )
        ]


@app.list_resources()
async def list_resources() -> list[Resource]:
    """
    列出服务器提供的所有资源
    
    说明：
    - 资源（Resources）是 MCP 服务器提供的标准化数据或上下文
    - Cursor 可以读取资源来获取信息（如表结构）
    - 资源通过 URI 标识，格式：table://<schema>/<table>
    - 特殊 URI "table://*" 表示列出所有表
    
    返回：
    - Resource 对象列表
    """
    try:
        # 获取所有表
        logger.debug("获取表列表")
        table_list = db_manager.list_tables()
        
        resources = []
        
        # 为每个表创建一个资源
        for table in table_list.tables:
            schema_name = table['schema_name']
            table_name = table['table_name']
            uri = f"table://{schema_name}/{table_name}"
            
            resources.append(
                Resource(
                    uri=uri,
                    name=f"{schema_name}.{table_name}",
                    description=f"表 {schema_name}.{table_name} 的结构信息",
                    mimeType="application/json"
                )
            )
        
        # 添加一个特殊资源用于列出所有表
        resources.append(
            Resource(
                uri="table://*",
                name="所有表",
                description="列出数据库中的所有表",
                mimeType="application/json"
            )
        )
        
        logger.debug(f"返回 {len(resources)} 个资源")
        return resources
    except Exception as e:
        # 如果出错，至少返回列表资源
        logger.error(f"获取资源列表失败: {e}", exc_info=True)
        return [
            Resource(
                uri="table://*",
                name="所有表",
                description=f"列出数据库中的所有表（错误: {str(e)}）",
                mimeType="application/json"
            )
        ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """
    读取资源内容
    
    说明：
    - 当 Cursor 请求读取资源时，这个函数会被调用
    - 根据 URI 返回相应的内容
    - 对于表结构资源，返回 JSON 格式的表结构信息
    
    参数：
    - uri: 资源 URI（如 "table://public/users"）
    
    返回：
    - 资源内容的字符串表示（通常是 JSON）
    """
    if uri == "table://*":
        # 返回所有表的列表
        try:
            logger.debug("读取资源: table://*")
            table_list = db_manager.list_tables()
            logger.debug(f"获取到 {len(table_list.tables)} 个表")
            return json.dumps(
                {
                    "tables": table_list.tables
                },
                indent=2,
                ensure_ascii=False
            )
        except Exception as e:
            logger.error(f"获取表列表失败: {e}", exc_info=True)
            return json.dumps(
                {"error": f"获取表列表失败: {str(e)}"},
                ensure_ascii=False
            )
    
    # 解析表 URI：table://<schema>/<table>
    if uri.startswith("table://"):
        parts = uri[8:].split("/", 1)
        if len(parts) == 2:
            schema_name, table_name = parts
            logger.debug(f"读取资源: table://{schema_name}/{table_name}")
            
            try:
                # 获取表结构
                table_schema = db_manager.get_table_schema(schema_name, table_name)
                
                # 转换为字典并返回 JSON
                schema_dict = {
                    "schema_name": table_schema.schema_name,
                    "table_name": table_schema.table_name,
                    "columns": [
                        {
                            "name": col.name,
                            "data_type": col.data_type,
                            "is_nullable": col.is_nullable,
                            "default_value": col.default_value
                        }
                        for col in table_schema.columns
                    ],
                    "primary_key": table_schema.primary_key
                }
                
                logger.debug(f"成功获取表结构: {schema_name}.{table_name}")
                return json.dumps(schema_dict, indent=2, ensure_ascii=False)
            except ValueError as e:
                logger.warning(f"表不存在: {schema_name}.{table_name}")
                return json.dumps(
                    {"error": f"获取表结构失败: {str(e)}"},
                    ensure_ascii=False
                )
            except Exception as e:
                logger.error(f"获取表结构失败: {e}", exc_info=True)
                return json.dumps(
                    {"error": f"获取表结构失败: {str(e)}"},
                    ensure_ascii=False
                )
    
    logger.warning(f"未知资源 URI: {uri}")
    return json.dumps(
        {"error": f"未知资源 URI: {uri}"},
        ensure_ascii=False
    )


@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """
    列出服务器提供的所有提示
    
    说明：
    - 提示（Prompts）是预定义的模板，可以帮助 Cursor 更好地理解如何与服务器交互
    - 可以包含示例查询、最佳实践等
    """
    return [
        Prompt(
            name="query-example",
            description="SQL 查询示例：查询表的前 N 条记录",
            arguments=[
                {
                    "name": "table_name",
                    "description": "要查询的表名",
                    "required": True
                },
                {
                    "name": "limit",
                    "description": "返回的记录数（默认 10）",
                    "required": False
                }
            ]
        ),
        Prompt(
            name="schema-query",
            description="查询表结构的示例",
            arguments=[
                {
                    "name": "table_name",
                    "description": "要查询结构的表名",
                    "required": True
                }
            ]
        ),
        Prompt(
            name="join-query",
            description="多表连接查询示例",
            arguments=[
                {
                    "name": "table1",
                    "description": "第一个表名",
                    "required": True
                },
                {
                    "name": "table2",
                    "description": "第二个表名",
                    "required": True
                },
                {
                    "name": "join_condition",
                    "description": "连接条件",
                    "required": True
                }
            ]
        )
    ]


async def main():
    """
    主函数：启动 MCP 服务器
    
    说明：
    - 建立数据库连接
    - 启动 stdio 服务器，开始监听来自 Cursor 的请求
    - stdio 服务器通过标准输入/输出与 Cursor 通信
    """
    logger.info("启动 PostgreSQL MCP 服务器")
    
    # 建立数据库连接
    try:
        db_manager.connect()
        logger.info("数据库连接成功")
    except Exception as e:
        logger.critical(f"数据库连接失败: {e}", exc_info=True)
        print(f"数据库连接失败: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # 启动 stdio 服务器
    # 说明：stdio_server 是 MCP SDK 提供的函数，用于创建基于标准输入/输出的服务器
    # 它会读取标准输入中的 JSON-RPC 请求，并将响应写入标准输出
    logger.info("启动 stdio 服务器，等待 Cursor 连接...")
    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    except Exception as e:
        logger.critical(f"服务器运行错误: {e}", exc_info=True)
        raise
    finally:
        # 关闭数据库连接
        try:
            db_manager.close()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接时出错: {e}")


if __name__ == "__main__":
    # 运行主函数
    # 说明：asyncio.run() 用于运行异步主函数
    asyncio.run(main())

