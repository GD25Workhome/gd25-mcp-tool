"""
Pydantic 数据模型定义
用于验证输入输出数据的格式和类型
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class QueryInput(BaseModel):
    """
    SQL 查询工具的输入模型
    
    说明：
    - sql: 要执行的 SQL 查询语句
    - 这个模型确保输入参数符合预期格式
    """
    sql: str = Field(
        ...,
        description="要执行的 SQL 查询语句",
        examples=["SELECT * FROM users LIMIT 10"]
    )


class QueryResult(BaseModel):
    """
    SQL 查询结果的输出模型
    
    说明：
    - columns: 查询结果的列名列表
    - rows: 查询结果的行数据（每行是一个字典）
    - row_count: 返回的行数
    """
    columns: List[str] = Field(..., description="查询结果的列名列表")
    rows: List[Dict[str, Any]] = Field(..., description="查询结果的行数据")
    row_count: int = Field(..., description="返回的行数")


class ColumnInfo(BaseModel):
    """
    数据库列信息模型
    
    说明：
    - name: 列名
    - data_type: 数据类型（如 varchar, integer 等）
    - is_nullable: 是否允许为空
    - default_value: 默认值（如果有）
    """
    name: str = Field(..., description="列名")
    data_type: str = Field(..., description="PostgreSQL 数据类型")
    is_nullable: bool = Field(..., description="是否允许为空")
    default_value: Optional[str] = Field(None, description="默认值")


class TableSchema(BaseModel):
    """
    数据库表结构信息模型
    
    说明：
    - schema_name: 模式名（通常是 'public'）
    - table_name: 表名
    - columns: 列信息列表
    - primary_key: 主键列名列表
    """
    schema_name: str = Field(..., description="数据库模式名")
    table_name: str = Field(..., description="表名")
    columns: List[ColumnInfo] = Field(..., description="列信息列表")
    primary_key: List[str] = Field(default_factory=list, description="主键列名列表")


class TableList(BaseModel):
    """
    数据库表列表模型
    
    说明：
    - tables: 表信息列表，每个表包含模式名和表名
    """
    tables: List[Dict[str, str]] = Field(
        ...,
        description="表列表，每个表包含 schema_name 和 table_name"
    )

