#!/usr/bin/env python3
"""
GitHub MCP 服务器主文件

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

logger = logging.getLogger('github-mcp-server')

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

from github_client import GitHubClient
from models import (
    SearchCodeInput, GetRepoInfoInput, GetFileContentInput,
    ListIssuesInput, CreateIssueInput, ListPullRequestsInput, ListUserReposInput,
    CreatePullRequestInput, GetPullRequestInput, UpdateIssueInput,
    SearchRepositoriesInput, ListBranchesInput, GetCommitInfoInput, ListCommitsInput
)


# 初始化 GitHub 客户端
github_token = os.getenv('GITHUB_TOKEN')
if not github_token:
    logger.error("未设置 GITHUB_TOKEN 环境变量")
    print(
        "错误：未设置 GITHUB_TOKEN 环境变量。\n"
        "请设置 GitHub 个人访问令牌，例如：\n"
        "export GITHUB_TOKEN='your_github_token_here'\n\n"
        "获取令牌：https://github.com/settings/tokens",
        file=sys.stderr
    )
    sys.exit(1)

logger.info("初始化 GitHub 客户端")
try:
    github_client = GitHubClient(github_token)
except Exception as e:
    logger.error(f"GitHub 客户端初始化失败: {e}")
    print(f"错误：GitHub 客户端初始化失败: {str(e)}", file=sys.stderr)
    sys.exit(1)

# 创建 MCP 服务器实例
# 说明：Server 是 MCP SDK 的核心类，用于处理与 Cursor 的通信
app = Server("github-mcp-server")


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
            name="search_code",
            description=(
                "在 GitHub 上搜索代码。支持 GitHub 搜索语法，"
                "例如：'language:python def hello' 或 'repo:owner/repo filename:test.py'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GitHub 代码搜索查询字符串（支持 GitHub 搜索语法）",
                        "examples": ["language:python def hello", "repo:owner/repo filename:test.py"]
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_repo_info",
            description="获取 GitHub 仓库的详细信息，包括描述、语言、Star 数等",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者（用户名或组织名）"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    }
                },
                "required": ["owner", "repo"]
            }
        ),
        Tool(
            name="get_file_content",
            description="获取 GitHub 仓库中指定文件的内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    },
                    "path": {
                        "type": "string",
                        "description": "文件路径（相对于仓库根目录）"
                    },
                    "ref": {
                        "type": "string",
                        "description": "分支、标签或提交 SHA（可选，默认：默认分支）"
                    }
                },
                "required": ["owner", "repo", "path"]
            }
        ),
        Tool(
            name="list_issues",
            description="列出指定仓库的 Issue 列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    },
                    "state": {
                        "type": "string",
                        "description": "Issue 状态：open, closed, all（默认：open）",
                        "enum": ["open", "closed", "all"],
                        "default": "open"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制（默认：10，最大：100）",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["owner", "repo"]
            }
        ),
        Tool(
            name="create_issue",
            description="在指定仓库中创建新的 Issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    },
                    "title": {
                        "type": "string",
                        "description": "Issue 标题"
                    },
                    "body": {
                        "type": "string",
                        "description": "Issue 内容（Markdown 格式，可选）"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "标签列表（可选）"
                    }
                },
                "required": ["owner", "repo", "title"]
            }
        ),
        Tool(
            name="list_pull_requests",
            description="列出指定仓库的 Pull Request 列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    },
                    "state": {
                        "type": "string",
                        "description": "PR 状态：open, closed, all（默认：open）",
                        "enum": ["open", "closed", "all"],
                        "default": "open"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制（默认：10，最大：100）",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["owner", "repo"]
            }
        ),
        Tool(
            name="list_user_repos",
            description="列出指定用户的所有仓库（如果不指定用户名，则列出当前认证用户的所有仓库）",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "GitHub 用户名（可选，默认：当前认证用户）"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制（默认：100，最大：1000）",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="create_pull_request",
            description="创建 Pull Request，从源分支到目标分支",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    },
                    "title": {
                        "type": "string",
                        "description": "PR 标题"
                    },
                    "body": {
                        "type": "string",
                        "description": "PR 描述（Markdown 格式，可选）"
                    },
                    "head": {
                        "type": "string",
                        "description": "源分支"
                    },
                    "base": {
                        "type": "string",
                        "description": "目标分支"
                    },
                    "draft": {
                        "type": "boolean",
                        "description": "是否为草稿 PR（默认：False）",
                        "default": False
                    }
                },
                "required": ["owner", "repo", "title", "head", "base"]
            }
        ),
        Tool(
            name="get_pull_request",
            description="获取 Pull Request 的详细信息，包括状态、变更文件、评论等",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    },
                    "number": {
                        "type": "integer",
                        "description": "PR 编号"
                    }
                },
                "required": ["owner", "repo", "number"]
            }
        ),
        Tool(
            name="update_issue",
            description="更新 Issue，可以修改状态、标题、内容或标签",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    },
                    "number": {
                        "type": "integer",
                        "description": "Issue 编号"
                    },
                    "state": {
                        "type": "string",
                        "description": "状态：open 或 closed（可选）",
                        "enum": ["open", "closed"]
                    },
                    "title": {
                        "type": "string",
                        "description": "标题（可选）"
                    },
                    "body": {
                        "type": "string",
                        "description": "内容（可选，Markdown 格式）"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "标签列表（可选）"
                    }
                },
                "required": ["owner", "repo", "number"]
            }
        ),
        Tool(
            name="search_repositories",
            description="搜索 GitHub 仓库，支持 GitHub 搜索语法",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询字符串（支持 GitHub 搜索语法）",
                        "examples": ["language:python", "stars:>1000", "user:octocat"]
                    },
                    "sort": {
                        "type": "string",
                        "description": "排序方式：stars, forks, updated（默认：stars）",
                        "enum": ["stars", "forks", "updated"],
                        "default": "stars"
                    },
                    "order": {
                        "type": "string",
                        "description": "排序顺序：asc 或 desc（默认：desc）",
                        "enum": ["asc", "desc"],
                        "default": "desc"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制（默认：30，最大：100）",
                        "default": 30,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_branches",
            description="列出仓库的所有分支",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制（默认：100，最大：1000）",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["owner", "repo"]
            }
        ),
        Tool(
            name="get_commit_info",
            description="获取提交的详细信息，包括变更文件、作者、统计信息等",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    },
                    "sha": {
                        "type": "string",
                        "description": "提交 SHA"
                    }
                },
                "required": ["owner", "repo", "sha"]
            }
        ),
        Tool(
            name="list_commits",
            description="列出仓库的提交历史，支持指定分支或文件路径过滤",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "仓库名称"
                    },
                    "sha": {
                        "type": "string",
                        "description": "分支或提交 SHA（可选，默认：默认分支）"
                    },
                    "path": {
                        "type": "string",
                        "description": "文件路径（可选，仅列出该文件的提交）"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制（默认：30，最大：100）",
                        "default": 30,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["owner", "repo"]
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
    - name: 工具名称
    - arguments: 工具参数（字典格式）
    
    返回：
    - 内容列表（TextContent/ImageContent/EmbeddedResource）
    """
    try:
        if name == "search_code":
            # 验证输入参数
            try:
                search_input = SearchCodeInput(**arguments)
                logger.info(f"搜索代码: {search_input.query}")
            except Exception as e:
                logger.error(f"参数验证错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            # 执行搜索
            try:
                result = github_client.search_code(search_input.query)
                logger.info(f"搜索成功，找到 {result['total_count']} 个结果")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                logger.warning(f"搜索失败: {e}")
                return [
                    TextContent(
                        type="text",
                        text=f"搜索失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"搜索时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"搜索时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "get_repo_info":
            try:
                repo_input = GetRepoInfoInput(**arguments)
                logger.info(f"获取仓库信息: {repo_input.owner}/{repo_input.repo}")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.get_repo_info(repo_input.owner, repo_input.repo)
                logger.info(f"获取仓库信息成功: {repo_input.owner}/{repo_input.repo}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"获取仓库信息失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"获取仓库信息时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"获取仓库信息时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "get_file_content":
            try:
                file_input = GetFileContentInput(**arguments)
                logger.info(f"获取文件内容: {file_input.owner}/{file_input.repo}/{file_input.path}")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.get_file_content(
                    file_input.owner,
                    file_input.repo,
                    file_input.path,
                    file_input.ref
                )
                logger.info(f"获取文件内容成功: {file_input.path}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"获取文件内容失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"获取文件内容时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"获取文件内容时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "list_issues":
            try:
                issues_input = ListIssuesInput(**arguments)
                logger.info(f"列出 Issue: {issues_input.owner}/{issues_input.repo} (state={issues_input.state})")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.list_issues(
                    issues_input.owner,
                    issues_input.repo,
                    issues_input.state or "open",
                    issues_input.limit or 10
                )
                logger.info(f"获取到 {len(result)} 个 Issue")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"count": len(result), "issues": result}, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"列出 Issue 失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"列出 Issue 时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"列出 Issue 时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "create_issue":
            try:
                create_input = CreateIssueInput(**arguments)
                logger.info(f"创建 Issue: {create_input.owner}/{create_input.repo} - {create_input.title}")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.create_issue(
                    create_input.owner,
                    create_input.repo,
                    create_input.title,
                    create_input.body,
                    create_input.labels
                )
                logger.info(f"创建 Issue 成功: #{result['number']}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"创建 Issue 失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"创建 Issue 时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"创建 Issue 时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "list_pull_requests":
            try:
                pr_input = ListPullRequestsInput(**arguments)
                logger.info(f"列出 Pull Request: {pr_input.owner}/{pr_input.repo} (state={pr_input.state})")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.list_pull_requests(
                    pr_input.owner,
                    pr_input.repo,
                    pr_input.state or "open",
                    pr_input.limit or 10
                )
                logger.info(f"获取到 {len(result)} 个 Pull Request")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"count": len(result), "pull_requests": result}, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"列出 Pull Request 失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"列出 Pull Request 时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"列出 Pull Request 时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "list_user_repos":
            try:
                repos_input = ListUserReposInput(**arguments)
                username_str = repos_input.username or "当前认证用户"
                logger.info(f"列出用户仓库: {username_str} (limit={repos_input.limit or 100})")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.list_user_repos(
                    repos_input.username,
                    repos_input.limit or 100
                )
                logger.info(f"获取到 {result['total_count']} 个仓库")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"列出用户仓库失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"列出用户仓库时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"列出用户仓库时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "create_pull_request":
            try:
                pr_input = CreatePullRequestInput(**arguments)
                logger.info(f"创建 PR: {pr_input.owner}/{pr_input.repo} - {pr_input.title}")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.create_pull_request(
                    pr_input.owner,
                    pr_input.repo,
                    pr_input.title,
                    pr_input.head,
                    pr_input.base,
                    pr_input.body,
                    pr_input.draft or False
                )
                logger.info(f"创建 PR 成功: #{result['number']}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"创建 PR 失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"创建 PR 时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"创建 PR 时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "get_pull_request":
            try:
                pr_input = GetPullRequestInput(**arguments)
                logger.info(f"获取 PR: {pr_input.owner}/{pr_input.repo}#{pr_input.number}")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.get_pull_request(
                    pr_input.owner,
                    pr_input.repo,
                    pr_input.number
                )
                logger.info(f"获取 PR 成功: #{pr_input.number}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"获取 PR 失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"获取 PR 时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"获取 PR 时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "update_issue":
            try:
                issue_input = UpdateIssueInput(**arguments)
                logger.info(f"更新 Issue: {issue_input.owner}/{issue_input.repo}#{issue_input.number}")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.update_issue(
                    issue_input.owner,
                    issue_input.repo,
                    issue_input.number,
                    issue_input.state,
                    issue_input.title,
                    issue_input.body,
                    issue_input.labels
                )
                logger.info(f"更新 Issue 成功: #{issue_input.number}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"更新 Issue 失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"更新 Issue 时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"更新 Issue 时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "search_repositories":
            try:
                search_input = SearchRepositoriesInput(**arguments)
                logger.info(f"搜索仓库: {search_input.query}")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.search_repositories(
                    search_input.query,
                    search_input.sort or "stars",
                    search_input.order or "desc",
                    search_input.limit or 30
                )
                logger.info(f"搜索成功，找到 {result['total_count']} 个仓库")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"搜索仓库失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"搜索仓库时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"搜索仓库时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "list_branches":
            try:
                branch_input = ListBranchesInput(**arguments)
                logger.info(f"列出分支: {branch_input.owner}/{branch_input.repo}")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.list_branches(
                    branch_input.owner,
                    branch_input.repo,
                    branch_input.limit or 100
                )
                logger.info(f"获取到 {len(result)} 个分支")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"count": len(result), "branches": result}, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"列出分支失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"列出分支时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"列出分支时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "get_commit_info":
            try:
                commit_input = GetCommitInfoInput(**arguments)
                logger.info(f"获取提交信息: {commit_input.owner}/{commit_input.repo} - {commit_input.sha[:7]}")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.get_commit_info(
                    commit_input.owner,
                    commit_input.repo,
                    commit_input.sha
                )
                logger.info(f"获取提交信息成功: {commit_input.sha[:7]}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"获取提交信息失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"获取提交信息时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"获取提交信息时发生错误: {str(e)}"
                    )
                ]
        
        elif name == "list_commits":
            try:
                commits_input = ListCommitsInput(**arguments)
                logger.info(f"列出提交: {commits_input.owner}/{commits_input.repo}")
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"参数验证错误: {str(e)}"
                    )
                ]
            
            try:
                result = github_client.list_commits(
                    commits_input.owner,
                    commits_input.repo,
                    commits_input.sha,
                    commits_input.path,
                    commits_input.limit or 30
                )
                logger.info(f"获取到 {len(result)} 个提交")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"count": len(result), "commits": result}, indent=2, ensure_ascii=False)
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"列出提交失败: {str(e)}"
                    )
                ]
            except Exception as e:
                logger.error(f"列出提交时发生错误: {e}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"列出提交时发生错误: {str(e)}"
                    )
                ]
        
        else:
            return [
                TextContent(
                    type="text",
                    text=f"未知工具: {name}"
                )
            ]
    
    except Exception as e:
        logger.error(f"处理工具调用时发生未预期的错误: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=f"处理工具调用时发生错误: {str(e)}"
            )
        ]


@app.list_resources()
async def list_resources() -> list[Resource]:
    """
    列出服务器提供的所有资源
    
    说明：
    - 资源（Resources）是 MCP 服务器提供的标准化数据或上下文
    - Cursor 可以读取资源来获取信息（如仓库信息、文件内容）
    - 资源通过 URI 标识，格式：repo://owner/repo 或 file://owner/repo/path
    
    返回：
    - Resource 对象列表
    """
    # GitHub MCP 工具主要提供工具（Tools），资源（Resources）较少使用
    # 但我们可以提供一些示例资源
    return [
        Resource(
            uri="github://info",
            name="GitHub 工具信息",
            description="GitHub MCP 工具的功能说明",
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
    - 支持以下 URI 格式：
      - github://info - 工具信息
      - repo://owner/repo - 仓库信息
      - file://owner/repo/path - 文件内容（支持可选 ref 参数：file://owner/repo/path?ref=branch）
      - issue://owner/repo/number - Issue 信息
    
    参数：
    - uri: 资源 URI
    
    返回：
    - 资源内容的字符串表示（通常是 JSON）
    """
    try:
        if uri == "github://info":
            info = {
                "name": "GitHub MCP 服务器",
                "description": "提供 GitHub 代码搜索、仓库信息、文件内容、Issue 和 PR 管理功能",
                "tools": [
                    "search_code",
                    "get_repo_info",
                    "get_file_content",
                    "list_issues",
                    "create_issue",
                    "list_pull_requests",
                    "list_user_repos",
                    "create_pull_request",
                    "get_pull_request",
                    "update_issue",
                    "search_repositories",
                    "list_branches",
                    "get_commit_info",
                    "list_commits"
                ]
            }
            return json.dumps(info, indent=2, ensure_ascii=False)
        
        # 处理 repo://owner/repo 资源
        if uri.startswith("repo://"):
            parts = uri[7:].split("/")
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1]
                logger.info(f"读取仓库资源: {owner}/{repo}")
                result = github_client.get_repo_info(owner, repo)
                return json.dumps(result, indent=2, ensure_ascii=False)
        
        # 处理 file://owner/repo/path 资源
        if uri.startswith("file://"):
            # 解析 URI: file://owner/repo/path?ref=branch
            uri_part = uri[7:]
            if "?" in uri_part:
                path_part, query_part = uri_part.split("?", 1)
                ref = None
                for param in query_part.split("&"):
                    if param.startswith("ref="):
                        ref = param[4:]
            else:
                path_part = uri_part
                ref = None
            
            parts = path_part.split("/", 2)
            if len(parts) >= 3:
                owner = parts[0]
                repo = parts[1]
                file_path = parts[2]
                logger.info(f"读取文件资源: {owner}/{repo}/{file_path}")
                result = github_client.get_file_content(owner, repo, file_path, ref)
                return json.dumps(result, indent=2, ensure_ascii=False)
        
        # 处理 issue://owner/repo/number 资源
        if uri.startswith("issue://"):
            parts = uri[8:].split("/")
            if len(parts) >= 3:
                owner = parts[0]
                repo = parts[1]
                try:
                    issue_number = int(parts[2])
                    logger.info(f"读取 Issue 资源: {owner}/{repo}#{issue_number}")
                    # 使用 list_issues 获取单个 Issue 的信息
                    issues = github_client.list_issues(owner, repo, "all", 100)
                    for issue in issues:
                        if issue["number"] == issue_number:
                            return json.dumps(issue, indent=2, ensure_ascii=False)
                    raise ValueError(f"Issue #{issue_number} 不存在")
                except ValueError:
                    raise
                except Exception as e:
                    raise ValueError(f"获取 Issue 失败: {str(e)}")
        
        logger.warning(f"未知资源 URI: {uri}")
        return json.dumps(
            {"error": f"未知资源 URI: {uri}"},
            ensure_ascii=False
        )
    
    except ValueError as e:
        logger.error(f"读取资源失败: {e}")
        return json.dumps(
            {"error": str(e)},
            ensure_ascii=False
        )
    except Exception as e:
        logger.error(f"读取资源时发生错误: {e}", exc_info=True)
        return json.dumps(
            {"error": f"读取资源时发生错误: {str(e)}"},
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
            name="search-code-example",
            description="代码搜索示例：在 GitHub 上搜索特定语言的代码",
            arguments=[
                {
                    "name": "language",
                    "description": "编程语言（如 python, javascript, java）",
                    "required": True
                },
                {
                    "name": "keyword",
                    "description": "搜索关键词",
                    "required": True
                }
            ]
        ),
        Prompt(
            name="get-repo-example",
            description="获取仓库信息示例",
            arguments=[
                {
                    "name": "owner",
                    "description": "仓库所有者（用户名或组织名）",
                    "required": True
                },
                {
                    "name": "repo",
                    "description": "仓库名称",
                    "required": True
                }
            ]
        ),
        Prompt(
            name="create-issue-example",
            description="创建 Issue 示例",
            arguments=[
                {
                    "name": "owner",
                    "description": "仓库所有者",
                    "required": True
                },
                {
                    "name": "repo",
                    "description": "仓库名称",
                    "required": True
                },
                {
                    "name": "title",
                    "description": "Issue 标题",
                    "required": True
                },
                {
                    "name": "body",
                    "description": "Issue 内容（可选）",
                    "required": False
                }
            ]
        ),
        Prompt(
            name="create-pr-example",
            description="创建 Pull Request 示例",
            arguments=[
                {
                    "name": "owner",
                    "description": "仓库所有者",
                    "required": True
                },
                {
                    "name": "repo",
                    "description": "仓库名称",
                    "required": True
                },
                {
                    "name": "title",
                    "description": "PR 标题",
                    "required": True
                },
                {
                    "name": "head",
                    "description": "源分支",
                    "required": True
                },
                {
                    "name": "base",
                    "description": "目标分支",
                    "required": True
                },
                {
                    "name": "body",
                    "description": "PR 描述（可选）",
                    "required": False
                }
            ]
        ),
        Prompt(
            name="search-repo-example",
            description="搜索仓库示例",
            arguments=[
                {
                    "name": "query",
                    "description": "搜索查询字符串（支持 GitHub 搜索语法）",
                    "required": True
                },
                {
                    "name": "language",
                    "description": "编程语言（可选，如 python, javascript）",
                    "required": False
                },
                {
                    "name": "stars",
                    "description": "Star 数条件（可选，如 >1000）",
                    "required": False
                }
            ]
        ),
        Prompt(
            name="manage-branch-example",
            description="分支管理示例",
            arguments=[
                {
                    "name": "owner",
                    "description": "仓库所有者",
                    "required": True
                },
                {
                    "name": "repo",
                    "description": "仓库名称",
                    "required": True
                },
                {
                    "name": "action",
                    "description": "操作类型：list（列出分支）",
                    "required": True
                }
            ]
        ),
        Prompt(
            name="commit-history-example",
            description="提交历史示例",
            arguments=[
                {
                    "name": "owner",
                    "description": "仓库所有者",
                    "required": True
                },
                {
                    "name": "repo",
                    "description": "仓库名称",
                    "required": True
                },
                {
                    "name": "branch",
                    "description": "分支名称（可选，默认：默认分支）",
                    "required": False
                },
                {
                    "name": "path",
                    "description": "文件路径（可选，仅列出该文件的提交）",
                    "required": False
                }
            ]
        )
    ]


async def main():
    """
    主函数：启动 MCP 服务器
    
    说明：
    - 启动 stdio 服务器，开始监听来自 Cursor 的请求
    - stdio 服务器通过标准输入/输出与 Cursor 通信
    """
    logger.info("启动 GitHub MCP 服务器")
    
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


if __name__ == "__main__":
    # 运行主函数
    # 说明：asyncio.run() 用于运行异步主函数
    asyncio.run(main())

