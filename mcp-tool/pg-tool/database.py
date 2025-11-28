"""
数据库连接和查询逻辑
负责与 PostgreSQL 数据库的实际交互
"""

import os
import re
import logging
import hashlib
import time
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from models import QueryResult, TableSchema, ColumnInfo, TableList

# 创建数据库模块的日志记录器
logger = logging.getLogger('postgres-mcp-server.database')

# 缓存配置
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))  # 默认缓存 5 分钟
MAX_CACHE_SIZE = int(os.getenv('MAX_CACHE_SIZE', '128'))  # 默认最多缓存 128 个查询结果


class DatabaseManager:
    """
    数据库管理器类
    
    说明：
    这个类封装了所有数据库操作，包括：
    - 建立和关闭数据库连接
    - 执行 SQL 查询
    - 获取表结构信息
    - 验证 SQL 语句的安全性（只读/写操作检查）
    """
    
    def __init__(self, database_url: str):
        """
        初始化数据库管理器
        
        参数：
        - database_url: PostgreSQL 连接字符串
          格式：postgresql://user:password@host:port/database
        """
        self.database_url = database_url
        self.connection: Optional[psycopg2.extensions.connection] = None
        self._allow_write_ops = os.getenv(
            'DANGEROUSLY_ALLOW_WRITE_OPS', 'false'
        ).lower() in ('true', '1', 'yes')
        
        # 查询结果缓存（仅用于 SELECT 查询）
        # 格式: {sql_hash: (result, timestamp)}
        self._query_cache: Dict[str, Tuple[QueryResult, float]] = {}
        self._cache_enabled = os.getenv('ENABLE_QUERY_CACHE', 'true').lower() in ('true', '1', 'yes')
        
        # 表结构缓存（格式: {schema.table: (schema_obj, timestamp)}）
        self._schema_cache: Dict[str, Tuple[TableSchema, float]] = {}
    
    def connect(self) -> None:
        """
        建立数据库连接
        
        说明：
        - 使用 psycopg2 连接到 PostgreSQL 数据库
        - 连接会在整个服务器生命周期中保持打开
        """
        try:
            logger.info("正在连接数据库...")
            self.connection = psycopg2.connect(self.database_url)
            # 设置自动提交模式，这样每个查询都会立即执行
            self.connection.autocommit = True
            logger.info("数据库连接成功")
        except psycopg2.Error as e:
            logger.error(f"数据库连接失败: {e}", exc_info=True)
            raise ConnectionError(f"无法连接到数据库: {str(e)}")
    
    def close(self) -> None:
        """
        关闭数据库连接
        
        说明：
        - 在服务器关闭时调用，释放数据库资源
        """
        if self.connection:
            logger.debug("关闭数据库连接")
            self.connection.close()
            self.connection = None
    
    def _is_write_operation(self, sql: str) -> bool:
        """
        检查 SQL 语句是否为写操作
        
        参数：
        - sql: SQL 查询语句
        
        返回：
        - True 如果是写操作（INSERT/UPDATE/DELETE/DROP/CREATE/ALTER等）
        - False 如果是只读操作（SELECT/SHOW/DESCRIBE等）
        
        说明：
        - 通过检查 SQL 语句的第一个关键字来判断
        - 写操作需要明确启用才能执行
        """
        # 移除注释和多余空白
        sql_clean = re.sub(r'--.*?\n', '', sql, flags=re.MULTILINE)
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)
        sql_clean = sql_clean.strip()
        
        if not sql_clean:
            return False
        
        # 获取第一个关键字
        first_word = sql_clean.split()[0].upper()
        
        # 写操作关键字列表
        write_keywords = {
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
            'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE', 'COMMIT',
            'ROLLBACK', 'SAVEPOINT'
        }
        
        return first_word in write_keywords
    
    def _get_cache_key(self, sql: str) -> str:
        """生成 SQL 查询的缓存键"""
        # 规范化 SQL（移除多余空白）
        sql_normalized = ' '.join(sql.split())
        return hashlib.md5(sql_normalized.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[QueryResult]:
        """从缓存获取查询结果"""
        if not self._cache_enabled:
            return None
        
        if cache_key not in self._query_cache:
            return None
        
        result, timestamp = self._query_cache[cache_key]
        # 检查缓存是否过期
        if time.time() - timestamp > CACHE_TTL:
            logger.debug(f"缓存已过期: {cache_key[:8]}...")
            del self._query_cache[cache_key]
            return None
        
        logger.debug(f"使用缓存结果: {cache_key[:8]}...")
        return result
    
    def _set_cached_result(self, cache_key: str, result: QueryResult) -> None:
        """将查询结果存入缓存"""
        if not self._cache_enabled:
            return
        
        # 如果缓存已满，删除最旧的条目
        if len(self._query_cache) >= MAX_CACHE_SIZE:
            # 删除最旧的缓存条目
            oldest_key = min(self._query_cache.keys(), 
                           key=lambda k: self._query_cache[k][1])
            del self._query_cache[oldest_key]
            logger.debug(f"缓存已满，删除最旧条目: {oldest_key[:8]}...")
        
        self._query_cache[cache_key] = (result, time.time())
        logger.debug(f"结果已缓存: {cache_key[:8]}...")
    
    def clear_cache(self) -> None:
        """清空所有缓存（查询缓存和表结构缓存）"""
        self._query_cache.clear()
        self._schema_cache.clear()
        logger.info("所有缓存已清空")
    
    def execute_query(self, sql: str, use_cache: bool = True) -> QueryResult:
        """
        执行 SQL 查询并返回结果
        
        参数：
        - sql: SQL 查询语句
        - use_cache: 是否使用缓存（仅对 SELECT 查询有效）
        
        返回：
        - QueryResult 对象，包含查询结果
        
        说明：
        - 默认只允许 SELECT 查询（只读）
        - 如果启用了写操作，可以执行 INSERT/UPDATE/DELETE 等
        - 使用 RealDictCursor 返回字典格式的结果，便于转换为 JSON
        - SELECT 查询结果会被缓存以提高性能
        """
        if not self.connection:
            raise RuntimeError("数据库连接未建立")
        
        # 检查是否为写操作
        is_write = self._is_write_operation(sql)
        if is_write:
            if not self._allow_write_ops:
                logger.warning("写操作被拒绝（未启用写操作权限）")
                raise ValueError(
                    "写操作被禁用。要启用写操作，请设置环境变量 "
                    "DANGEROUSLY_ALLOW_WRITE_OPS=true"
                )
            logger.warning("执行写操作（INSERT/UPDATE/DELETE等）")
            # 写操作会清空缓存，因为可能影响查询结果
            if self._cache_enabled:
                self.clear_cache()
        
        # 对于 SELECT 查询，尝试从缓存获取
        if not is_write and use_cache:
            cache_key = self._get_cache_key(sql)
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result
        
        try:
            # 使用 RealDictCursor 返回字典格式的结果
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql)
                
                # 获取列名
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # 获取所有行
                rows = [dict(row) for row in cursor.fetchall()]
                
                logger.debug(f"查询返回 {len(rows)} 行，{len(columns)} 列")
                result = QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows)
                )
                
                # 缓存 SELECT 查询结果
                if not is_write and use_cache:
                    cache_key = self._get_cache_key(sql)
                    self._set_cached_result(cache_key, result)
                
                return result
        except psycopg2.Error as e:
            logger.error(f"SQL 执行错误: {e}", exc_info=True)
            raise RuntimeError(f"SQL 执行错误: {str(e)}")
    
    def get_table_schema(self, schema_name: str, table_name: str, use_cache: bool = True) -> TableSchema:
        """
        获取指定表的结构信息
        
        参数：
        - schema_name: 数据库模式名（通常是 'public'）
        - table_name: 表名
        - use_cache: 是否使用缓存
        
        返回：
        - TableSchema 对象，包含表的完整结构信息
        
        说明：
        - 查询 PostgreSQL 的系统表（information_schema）获取表结构
        - 包括列名、数据类型、是否可空、默认值等信息
        - 还会查询主键信息
        - 表结构会被缓存以提高性能
        """
        if not self.connection:
            raise RuntimeError("数据库连接未建立")
        
        # 检查缓存
        cache_key = f"{schema_name}.{table_name}"
        if use_cache and self._cache_enabled:
            if cache_key in self._schema_cache:
                schema_obj, timestamp = self._schema_cache[cache_key]
                if time.time() - timestamp <= CACHE_TTL:
                    logger.debug(f"使用缓存的表结构: {cache_key}")
                    return schema_obj
                else:
                    # 缓存过期，删除
                    del self._schema_cache[cache_key]
        
        try:
            logger.debug(f"获取表结构: {schema_name}.{table_name}")
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # 查询列信息
                column_query = """
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """
                cursor.execute(column_query, (schema_name, table_name))
                column_rows = cursor.fetchall()
                
                if not column_rows:
                    logger.warning(f"表不存在: {schema_name}.{table_name}")
                    raise ValueError(f"表 {schema_name}.{table_name} 不存在")
                
                # 构建列信息列表
                columns = []
                for row in column_rows:
                    columns.append(ColumnInfo(
                        name=row['column_name'],
                        data_type=row['data_type'],
                        is_nullable=row['is_nullable'] == 'YES',
                        default_value=row['column_default']
                    ))
                
                # 查询主键信息
                pk_query = """
                    SELECT column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                        AND tc.table_schema = %s
                        AND tc.table_name = %s
                    ORDER BY kcu.ordinal_position
                """
                cursor.execute(pk_query, (schema_name, table_name))
                pk_rows = cursor.fetchall()
                primary_key = [row['column_name'] for row in pk_rows]
                
                logger.debug(f"成功获取表结构: {schema_name}.{table_name} ({len(columns)} 列)")
                schema_obj = TableSchema(
                    schema_name=schema_name,
                    table_name=table_name,
                    columns=columns,
                    primary_key=primary_key
                )
                
                # 缓存表结构
                if use_cache and self._cache_enabled:
                    self._schema_cache[cache_key] = (schema_obj, time.time())
                
                return schema_obj
        except psycopg2.Error as e:
            logger.error(f"获取表结构错误: {e}", exc_info=True)
            raise RuntimeError(f"获取表结构错误: {str(e)}")
    
    def list_tables(self) -> TableList:
        """
        列出数据库中的所有表
        
        返回：
        - TableList 对象，包含所有表的列表
        
        说明：
        - 查询 information_schema 获取所有用户表
        - 排除系统表（information_schema 和 pg_catalog 模式）
        """
        if not self.connection:
            raise RuntimeError("数据库连接未建立")
        
        try:
            logger.debug("列出所有表")
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # 查询所有用户表
                query = """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                        AND table_type = 'BASE TABLE'
                    ORDER BY table_schema, table_name
                """
                cursor.execute(query)
                rows = cursor.fetchall()
                
                tables = [
                    {
                        'schema_name': row['table_schema'],
                        'table_name': row['table_name']
                    }
                    for row in rows
                ]
                
                logger.debug(f"找到 {len(tables)} 个表")
                return TableList(tables=tables)
        except psycopg2.Error as e:
            logger.error(f"列出表错误: {e}", exc_info=True)
            raise RuntimeError(f"列出表错误: {str(e)}")

