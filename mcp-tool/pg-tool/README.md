# PostgreSQL MCP 服务器

这是一个为 Cursor 设计的 PostgreSQL Model Context Protocol (MCP) 服务器，允许 Cursor 直接查询 PostgreSQL 数据库并访问表结构信息。

## 功能特性

- ✅ **SQL 查询工具**：执行 SELECT 查询（默认只读）
- ✅ **写操作支持**：可通过环境变量启用 INSERT/UPDATE/DELETE
- ✅ **表结构资源**：以资源形式提供数据库表的结构信息
- ✅ **类型安全**：使用 Pydantic 进行输入输出验证

## 安装

### 1. 安装依赖

```bash
# 激活 conda 环境
conda activate py311_gb25MCP_01

# 进入项目目录
cd /path/to/gd25-mcp-tool/mcp-tool/pg-tool

# 安装依赖
pip install -r requirements.txt
```

**注意：** 如果还没有创建 conda 环境，请参考 [docs/使用说明.md](./docs/使用说明.md) 中的详细步骤。

### 2. 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
# 必需：PostgreSQL 数据库连接字符串
export DATABASE_URL="postgresql://user:password@localhost:5432/database"

# 可选：允许写操作（危险！）
export DANGEROUSLY_ALLOW_WRITE_OPS=false
```

## 使用方法

### 在 Cursor 中配置

在 Cursor 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "postgres": {
      "command": "/opt/homebrew/Caskroom/miniconda/base/envs/py311_gb25MCP_01/bin/python",
      "args": [
        "/path/to/gd25-mcp-tool/mcp-tool/pg-tool/server.py"
      ],
      "env": {
        "DATABASE_URL": "postgresql://user:password@localhost:5432/database",
        "DANGEROUSLY_ALLOW_WRITE_OPS": "false"
      }
    }
  }
}
```

**注意：** 请根据实际情况修改：
- `command`: 你的 conda 环境 Python 路径
- `args`: server.py 的实际路径
- `env.DATABASE_URL`: 你的数据库连接字符串

详细配置说明请参考 [docs/使用说明.md](./docs/使用说明.md)。

### 测试服务器

使用 MCP Inspector 测试：

```bash
python server.py
```

## 项目结构

```
pg-tool/
├── server.py                    # MCP 服务器主文件（入口点）
├── models.py                    # Pydantic 数据模型定义
├── database.py                  # 数据库连接和查询逻辑
├── requirements.txt             # Python 依赖列表
├── cursor-config.json.example   # Cursor 配置示例
├── README.md                    # 本文件
└── docs/                        # 文档目录
    ├── spec.md                  # 项目功能规范
    ├── 开发计划.md              # 详细的开发步骤和 MCP 概念说明
    ├── 使用说明.md              # 安装、配置和使用指南
    └── 代码说明.md              # 代码结构和逻辑详解
```

## 文档说明

本项目包含详细的文档，帮助理解每个步骤和概念：

1. **[docs/开发计划.md](./docs/开发计划.md)** - 详细的开发步骤和 MCP 核心概念说明
   - 项目概述和架构图
   - 每个开发步骤的详细说明
   - MCP 核心概念（工具、资源、提示）的解释
   - 为什么需要每个步骤

2. **[docs/使用说明.md](./docs/使用说明.md)** - 安装、配置和使用指南
   - 环境配置步骤
   - Cursor 配置方法
   - 功能使用说明
   - 故障排除指南

3. **[docs/代码说明.md](./docs/代码说明.md)** - 代码结构和逻辑详解
   - 每个文件的作用
   - 关键函数和类的说明
   - 数据流程图
   - 设计决策解释

4. **[docs/spec.md](./docs/spec.md)** - 项目功能规范
   - 功能需求定义
   - 技术实现要求
   - 环境变量说明

5. **[docs/测试说明.md](./docs/测试说明.md)** - 测试指南
   - 如何在 Cursor 中测试各项功能
   - 测试提示词示例
   - 测试场景和检查清单
   - 故障排除指南

6. **[docs/MCP重载机制说明.md](./docs/MCP重载机制说明.md)** - MCP 重载机制
   - 何时需要重启 Cursor
   - 何时只需要新建聊天框
   - 开发流程最佳实践
   - 常见问题解答

## 许可证

见项目根目录 LICENSE 文件

