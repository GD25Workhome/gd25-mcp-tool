# GitHub MCP 服务器规范

## 功能需求

### 1. GitHub 认证配置
- 通过环境变量 `GITHUB_TOKEN` 设置 GitHub 个人访问令牌（Personal Access Token）
- 令牌需要适当的权限（scope）来访问所需的 GitHub API
- 服务器启动时验证令牌有效性

### 2. 工具（Tools）

#### 2.1 search_code 工具
- **功能**：在 GitHub 上搜索代码
- **搜索范围**：
  - **默认**：搜索所有公共（开源）仓库
  - **私有仓库**：如果 GitHub Token 有 `repo` 权限，也可以搜索你有访问权限的私有仓库
  - **限定范围**：可以通过搜索语法限定搜索范围（见下方示例）
- **输入参数**：
  - `query` (string, 必需)：GitHub 代码搜索查询字符串，支持 GitHub 搜索语法
- **输出**：搜索结果（JSON 格式），包含匹配的文件列表
- **搜索语法示例**：
  - `language:python def hello` - 在所有公共仓库的 Python 代码中搜索包含 "def hello" 的代码
  - `repo:owner/repo filename:test.py` - 在指定仓库中搜索文件（可以是公共或你有权限的私有仓库）
  - `user:username language:javascript` - 在指定用户的所有仓库中搜索 JavaScript 代码（包括公共仓库和你有权限的私有仓库）
  - `org:orgname language:python` - 在指定组织的所有仓库中搜索 Python 代码

#### 2.2 get_repo_info 工具
- **功能**：获取 GitHub 仓库的详细信息
- **输入参数**：
  - `owner` (string, 必需)：仓库所有者（用户名或组织名）
  - `repo` (string, 必需)：仓库名称
- **输出**：仓库信息（JSON 格式），包括描述、语言、Star 数、Fork 数等

#### 2.3 get_file_content 工具
- **功能**：获取 GitHub 仓库中指定文件的内容
- **输入参数**：
  - `owner` (string, 必需)：仓库所有者
  - `repo` (string, 必需)：仓库名称
  - `path` (string, 必需)：文件路径（相对于仓库根目录）
  - `ref` (string, 可选)：分支、标签或提交 SHA（默认：默认分支）
- **输出**：文件内容（JSON 格式），包括文件内容、大小、SHA 等

#### 2.4 list_issues 工具
- **功能**：列出指定仓库的 Issue 列表
- **输入参数**：
  - `owner` (string, 必需)：仓库所有者
  - `repo` (string, 必需)：仓库名称
  - `state` (string, 可选)：Issue 状态（open, closed, all，默认：open）
  - `limit` (integer, 可选)：返回数量限制（默认：10，最大：100）
- **输出**：Issue 列表（JSON 格式）

#### 2.5 create_issue 工具
- **功能**：在指定仓库中创建新的 Issue
- **输入参数**：
  - `owner` (string, 必需)：仓库所有者
  - `repo` (string, 必需)：仓库名称
  - `title` (string, 必需)：Issue 标题
  - `body` (string, 可选)：Issue 内容（Markdown 格式）
  - `labels` (array, 可选)：标签列表
- **输出**：创建的 Issue 信息（JSON 格式）

#### 2.6 list_pull_requests 工具
- **功能**：列出指定仓库的 Pull Request 列表
- **输入参数**：
  - `owner` (string, 必需)：仓库所有者
  - `repo` (string, 必需)：仓库名称
  - `state` (string, 可选)：PR 状态（open, closed, all，默认：open）
  - `limit` (integer, 可选)：返回数量限制（默认：10，最大：100）
- **输出**：Pull Request 列表（JSON 格式）

### 3. 资源（Resources）

#### 3.1 github://info 资源
- **功能**：提供 GitHub MCP 工具的功能说明
- **资源 URI**：`github://info`
- **返回内容**：工具列表和功能描述

### 4. Schema 验证
- 使用 Pydantic 定义所有输入输出的数据模型
- 确保类型安全和数据验证
- 提供清晰的错误信息

### 5. 错误处理
- GitHub API 错误：返回 GitHub API 的错误信息
- 参数验证错误：返回验证失败的具体原因
- 网络错误：提供清晰的错误提示
- 权限错误：提示检查 GitHub Token 权限

## 技术实现要求

1. 使用 Python MCP SDK 实现服务器
2. 使用 PyGithub 库与 GitHub API 交互
3. 通过 stdio 与 Cursor 通信
4. 支持异步操作以提高性能
5. 完善的日志记录（用于调试）

## 环境变量

- `GITHUB_TOKEN`：GitHub 个人访问令牌（必需）
- `LOG_LEVEL`：日志级别（可选，默认 INFO）

## GitHub Token 权限要求

GitHub Token 需要以下权限（scopes）：
- `public_repo`：访问公共仓库（必需）
- `repo`：访问私有仓库（如果需要）
- `read:org`：读取组织信息（如果需要访问组织仓库）

## API 限制

- GitHub API 有速率限制（未认证：60 次/小时，认证：5000 次/小时）
- 代码搜索结果限制为前 30 个结果
- Issue 和 PR 列表限制为最多 100 条

