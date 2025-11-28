# PostgreSQL MCP 服务器规范

## 功能需求

### 1. 数据库连接配置
- 通过环境变量 `DATABASE_URL` 设置 PostgreSQL 数据库连接字符串
- 连接字符串格式：`postgresql://user:password@host:port/database`
- 服务器启动时建立连接，并在整个生命周期中保持连接

### 2. 工具（Tools）

#### 2.1 query 工具
- **功能**：执行 SQL 查询
- **输入参数**：
  - `sql` (string, 必需)：要执行的 SQL 查询语句
- **输出**：查询结果（JSON 格式）
- **安全限制**：
  - 默认只允许 SELECT 查询（只读操作）
  - 当环境变量 `DANGEROUSLY_ALLOW_WRITE_OPS=true` 或 `DANGEROUSLY_ALLOW_WRITE_OPS=1` 时，允许执行 INSERT、UPDATE、DELETE 等写操作
  - 写操作需要明确启用，防止意外修改数据

### 3. 资源（Resources）

#### 3.1 table_schemas 资源
- **功能**：提供数据库表的结构信息
- **资源 URI 格式**：`table://<schema_name>/<table_name>`
- **返回内容**：
  - 表名
  - 列信息（列名、数据类型、是否可空、默认值）
  - 主键信息
  - 外键信息
  - 索引信息
- **特殊资源**：`table://*` 或 `table://` 返回所有表的列表

### 4. Schema 验证
- 使用 Pydantic 定义所有输入输出的数据模型
- 确保类型安全和数据验证
- 提供清晰的错误信息

### 5. 错误处理
- 数据库连接错误：提供清晰的错误信息
- SQL 执行错误：返回数据库返回的错误信息
- 参数验证错误：返回验证失败的具体原因

## 技术实现要求

1. 使用 Python MCP SDK 实现服务器
2. 通过 stdio 与 Cursor 通信
3. 支持异步操作以提高性能
4. 完善的日志记录（可选，用于调试）

## 环境变量

- `DATABASE_URL`：PostgreSQL 连接字符串（必需）
- `DANGEROUSLY_ALLOW_WRITE_OPS`：是否允许写操作（可选，默认 false）

