# MCP 工具说明和安装文档

## 什么是 MCP 工具？

MCP（Model Context Protocol，模型上下文协议）是一种开放协议，用于标准化应用程序如何为大型语言模型（LLM）提供上下文和工具。通过 MCP，Cursor 能够连接到外部工具和数据源，扩展其功能。

## 常见的数据库 MCP 工具

### 1. DuckDB MCP 工具

**功能**：
- 查询本地 DuckDB 数据库
- 查询云端 MotherDuck 数据库
- 支持混合执行、云存储集成和数据共享

**特点**：
- 无需手动配置或服务器管理
- 支持数据分析工作流
- 可在 Cursor 中直接执行数据库查询

### 2. MySQL MCP 工具

**包名**: `@f4ww4z/mcp-mysql-server`

**安装方式**:
```bash
npm install -g @f4ww4z/mcp-mysql-server
```

**配置示例**:
```json
{
  "mcpServers": {
    "mysql-local": {
      "command": "npx",
      "args": [
        "@f4ww4z/mcp-mysql-server",
        "--host", "127.0.0.1",
        "--port", "3306",
        "--user", "your_username",
        "--password", "your_password"
      ]
    }
  }
}
```

**配置说明**：
- `--host`: MySQL 服务器地址（如 `127.0.0.1`）
- `--port`: MySQL 端口（默认 `3306`）
- `--user`: 数据库用户名
- `--password`: 数据库密码

### 3. PostgreSQL MCP 工具

**包名**: `@bytebase/dbhub`（支持多种数据库，包括 PostgreSQL）

**安装方式**:
```bash
npm install -g @bytebase/dbhub@0.11.2
```

**配置示例**:
```json
{
  "mcpServers": {
    "dbhub-postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@bytebase/dbhub",
        "--transport",
        "stdio",
        "--dsn",
        "postgres://your_username:your_password@your_host:5432/your_database?sslmode=disable"
      ]
    }
  }
}
```

**配置说明**：
- `--dsn`: 数据库连接字符串，格式为 `postgres://用户名:密码@主机:端口/数据库名?sslmode=disable`
- `--transport`: 传输方式，使用 `stdio` 表示标准输入输出

## 安装命令详解

### npm install 命令解析

```bash
npm install -g @bytebase/dbhub@0.11.2
```

**命令组成部分**：
- `npm install`: Node.js 包管理器安装命令
- `-g`: 全局安装标志（global），安装到系统目录而非当前项目
- `@bytebase/dbhub`: 包名
  - `@bytebase`: 组织/命名空间
  - `dbhub`: 包名
- `@0.11.2`: 指定版本号（可选，但建议指定以确保稳定性）

### 为什么需要全局安装？

1. **MCP 服务器需要全局可访问**：Cursor 通过 `npx` 调用 MCP 服务器，需要能在全局路径找到这个包
2. **配置简化**：全局安装后，配置文件中可以直接使用包名，无需指定完整路径
3. **跨项目使用**：一次安装，多个项目都可以使用

### 为什么指定版本号？

- **稳定性**：确保使用经过测试的特定版本，避免因版本更新导致配置不兼容
- **可重现性**：团队成员可以使用相同版本，保证环境一致性
- **安全性**：避免自动升级到可能有问题的版本

## 安装步骤

### 前置要求

1. **安装 Node.js**：确保系统已安装 Node.js（建议版本 >= 14）
   ```bash
   node --version
   npm --version
   ```

2. **确保网络连接**：需要能够访问 npm 仓库

### 安装流程

1. **安装 MCP 服务器包**
   ```bash
   # MySQL
   npm install -g @f4ww4z/mcp-mysql-server
   
   # PostgreSQL
   npm install -g @bytebase/dbhub@0.11.2
   ```

2. **配置 MCP 服务器**
   - 找到 Cursor 的 MCP 配置文件（通常在 `~/.cursor/mcp.json` 或类似位置）
   - 添加相应的服务器配置（参考上面的配置示例）
   - 替换配置中的数据库连接信息

3. **重启 Cursor**
   - 配置完成后，重启 Cursor 使配置生效

4. **验证安装**
   - 在 Cursor 中尝试使用数据库相关功能
   - 检查是否能正常连接和查询数据库

## 常见问题

### 1. 安装失败

**可能原因**：
- Node.js 未安装或版本过低
- 网络连接问题
- 权限不足（macOS/Linux 可能需要 `sudo`）

**解决方法**：
```bash
# 检查 Node.js 版本
node --version

# 使用 sudo（macOS/Linux）
sudo npm install -g @bytebase/dbhub@0.11.2

# 或使用 nvm 管理 Node.js 版本
```

### 2. 配置后无法连接数据库

**检查项**：
- 数据库服务是否正在运行
- 连接信息是否正确（主机、端口、用户名、密码）
- 防火墙是否允许连接
- 数据库用户是否有相应权限

### 3. 版本冲突

如果遇到版本冲突，可以：
- 使用 `npm list -g` 查看已安装的全局包
- 卸载旧版本：`npm uninstall -g 包名`
- 重新安装指定版本

## 替代方案

如果不想全局安装，也可以：

1. **本地安装**：在项目目录中安装（去掉 `-g` 参数）
2. **使用完整路径**：在配置中使用本地安装包的完整路径
3. **使用其他 MCP 服务器实现**：寻找其他支持相同数据库的 MCP 服务器

## 参考资料

- [Cursor MCP 官方文档](https://docs.cursor.com/zh/context/mcp)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- npm 包仓库：搜索 `mcp` 相关包



