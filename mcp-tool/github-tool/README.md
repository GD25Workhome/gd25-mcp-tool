# GitHub MCP 服务器

这是一个为 Cursor 设计的 GitHub Model Context Protocol (MCP) 服务器，允许 Cursor 直接与 GitHub 交互，搜索代码、获取仓库信息、管理 Issue 和 Pull Request。

## 功能特性

- ✅ **代码搜索**：在 GitHub 上搜索代码，支持 GitHub 搜索语法
- ✅ **仓库信息**：获取仓库的详细信息（描述、语言、Star 数等）
- ✅ **文件内容**：获取仓库中指定文件的内容
- ✅ **Issue 管理**：列出和创建 Issue
- ✅ **Pull Request**：列出仓库的 Pull Request
- ✅ **类型安全**：使用 Pydantic 进行输入输出验证

## 安装

### 1. 安装依赖

```bash
# 激活 conda 环境
conda activate py311_gb25MCP_01

# 进入项目目录
cd /path/to/gd25-mcp-tool/mcp-tool/github-tool

# 安装依赖
pip install -r requirements.txt
```

**注意**：如果还没有创建 conda 环境，请参考 [docs/使用说明.md](./docs/使用说明.md) 中的详细步骤。

### 2. 获取 GitHub Token

1. 登录 GitHub，进入 **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. 点击 **Generate new token (classic)**
3. 选择权限：`public_repo`（必需），`repo`（如果需要访问私有仓库）
4. 生成并复制 Token

### 3. 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
# 必需：GitHub 个人访问令牌
export GITHUB_TOKEN="your_github_token_here"

# 可选：日志级别
export LOG_LEVEL="INFO"
```

## 使用方法

### 在 Cursor 中配置

在 Cursor 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "github": {
      "command": "/opt/homebrew/Caskroom/miniconda/base/envs/py311_gb25MCP_01/bin/python",
      "args": [
        "/path/to/gd25-mcp-tool/mcp-tool/github-tool/server.py"
      ],
      "env": {
        "GITHUB_TOKEN": "your_github_token_here",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**注意**：请根据实际情况修改：
- `command`：你的 conda 环境 Python 路径
- `args`：server.py 的实际路径
- `env.GITHUB_TOKEN`：你的 GitHub Token

详细配置说明请参考 [docs/使用说明.md](./docs/使用说明.md)。

### 使用示例

配置完成后，你可以在 Cursor 中通过自然语言与 GitHub 交互：

- "搜索 Python 中的 hello 函数"
- "获取 owner/repo 仓库的信息"
- "列出 owner/repo 仓库的所有 open Issue"
- "在 owner/repo 仓库中创建一个新 Issue"

## 项目结构

```
github-tool/
├── server.py                    # MCP 服务器主文件（入口点）
├── github_client.py             # GitHub API 客户端封装
├── models.py                    # Pydantic 数据模型定义
├── requirements.txt             # Python 依赖列表
├── cursor-config.json.example   # Cursor 配置示例
├── README.md                    # 本文件
└── docs/                        # 文档目录
    ├── spec.md                  # 项目功能规范
    ├── 使用说明.md              # 安装和使用指南
    └── 代码说明.md              # 代码结构说明
```

## 工具列表

### search_code
在 GitHub 上搜索代码，支持 GitHub 搜索语法。

**示例**：
- `language:python def hello`
- `repo:owner/repo filename:test.py`

### get_repo_info
获取仓库的详细信息。

### get_file_content
获取仓库中指定文件的内容。

### list_issues
列出仓库的 Issue 列表。

### create_issue
在仓库中创建新的 Issue。

### list_pull_requests
列出仓库的 Pull Request 列表。

## 文档

- [功能规范](./docs/spec.md) - 详细的功能说明和 API 规范
- [使用说明](./docs/使用说明.md) - 安装、配置和使用指南
- [代码说明](./docs/代码说明.md) - 代码结构和实现细节

## 依赖

- `mcp>=0.9.0,<1.0.0` - MCP Python SDK
- `PyGithub>=2.1.0,<3.0.0` - GitHub API 客户端
- `pydantic>=2.0.0,<3.0.0` - 数据验证
- `python-dotenv>=1.0.0,<2.0.0` - 环境变量管理

## 安全注意事项

1. **保护 GitHub Token**：
   - 不要将 Token 提交到版本控制系统
   - 使用环境变量或 `.env` 文件
   - 定期轮换 Token

2. **权限最小化**：
   - 只授予必要的权限（scopes）
   - 如果只需要访问公共仓库，使用 `public_repo` 权限即可

## 许可证

本项目遵循项目根目录的 LICENSE 文件。

