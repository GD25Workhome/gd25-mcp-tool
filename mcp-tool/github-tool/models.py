"""
Pydantic 数据模型定义
用于验证输入输出数据的格式和类型
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SearchCodeInput(BaseModel):
    """
    代码搜索工具的输入模型
    
    说明：
    - query: GitHub 代码搜索查询字符串
    - 支持 GitHub 搜索语法，如 "language:python function"
    """
    query: str = Field(
        ...,
        description="GitHub 代码搜索查询字符串（支持 GitHub 搜索语法）",
        examples=["language:python def hello", "repo:owner/repo filename:test.py"]
    )


class GetRepoInfoInput(BaseModel):
    """
    获取仓库信息工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者（用户名或组织名）")
    repo: str = Field(..., description="仓库名称")


class GetFileContentInput(BaseModel):
    """
    获取文件内容工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者")
    repo: str = Field(..., description="仓库名称")
    path: str = Field(..., description="文件路径（相对于仓库根目录）")
    ref: Optional[str] = Field(None, description="分支、标签或提交 SHA（默认：默认分支）")


class ListIssuesInput(BaseModel):
    """
    列出 Issue 工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者")
    repo: str = Field(..., description="仓库名称")
    state: Optional[str] = Field("open", description="Issue 状态：open, closed, all（默认：open）")
    limit: Optional[int] = Field(10, description="返回数量限制（默认：10，最大：100）")


class CreateIssueInput(BaseModel):
    """
    创建 Issue 工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者")
    repo: str = Field(..., description="仓库名称")
    title: str = Field(..., description="Issue 标题")
    body: Optional[str] = Field(None, description="Issue 内容（Markdown 格式）")
    labels: Optional[List[str]] = Field(None, description="标签列表")


class ListPullRequestsInput(BaseModel):
    """
    列出 Pull Request 工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者")
    repo: str = Field(..., description="仓库名称")
    state: Optional[str] = Field("open", description="PR 状态：open, closed, all（默认：open）")
    limit: Optional[int] = Field(10, description="返回数量限制（默认：10，最大：100）")


class ListUserReposInput(BaseModel):
    """
    列出用户仓库工具的输入模型
    """
    username: Optional[str] = Field(None, description="GitHub 用户名（可选，默认：当前认证用户）")
    limit: Optional[int] = Field(100, description="返回数量限制（默认：100，最大：1000）")


class SearchCodeResult(BaseModel):
    """
    代码搜索结果模型
    """
    total_count: int = Field(..., description="总结果数")
    items: List[Dict[str, Any]] = Field(..., description="搜索结果列表")


class RepoInfo(BaseModel):
    """
    仓库信息模型
    """
    name: str = Field(..., description="仓库名称")
    full_name: str = Field(..., description="完整仓库名（owner/repo）")
    description: Optional[str] = Field(None, description="仓库描述")
    language: Optional[str] = Field(None, description="主要编程语言")
    stars: int = Field(..., description="Star 数量")
    forks: int = Field(..., description="Fork 数量")
    open_issues: int = Field(..., description="开放的 Issue 数量")
    default_branch: str = Field(..., description="默认分支")
    html_url: str = Field(..., description="仓库 URL")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class FileContent(BaseModel):
    """
    文件内容模型
    """
    path: str = Field(..., description="文件路径")
    content: str = Field(..., description="文件内容（Base64 解码后）")
    encoding: str = Field(..., description="编码方式")
    size: int = Field(..., description="文件大小（字节）")
    sha: str = Field(..., description="文件 SHA")
    html_url: str = Field(..., description="文件 URL")


class IssueInfo(BaseModel):
    """
    Issue 信息模型
    """
    number: int = Field(..., description="Issue 编号")
    title: str = Field(..., description="标题")
    body: Optional[str] = Field(None, description="内容")
    state: str = Field(..., description="状态：open 或 closed")
    labels: List[str] = Field(default_factory=list, description="标签列表")
    user: str = Field(..., description="创建者用户名")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    html_url: str = Field(..., description="Issue URL")


class PullRequestInfo(BaseModel):
    """
    Pull Request 信息模型
    """
    number: int = Field(..., description="PR 编号")
    title: str = Field(..., description="标题")
    body: Optional[str] = Field(None, description="内容")
    state: str = Field(..., description="状态：open 或 closed")
    user: str = Field(..., description="创建者用户名")
    head: str = Field(..., description="源分支")
    base: str = Field(..., description="目标分支")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    html_url: str = Field(..., description="PR URL")


# 第二阶段工具输入模型

class CreatePullRequestInput(BaseModel):
    """
    创建 Pull Request 工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者")
    repo: str = Field(..., description="仓库名称")
    title: str = Field(..., description="PR 标题")
    body: Optional[str] = Field(None, description="PR 描述（Markdown 格式）")
    head: str = Field(..., description="源分支")
    base: str = Field(..., description="目标分支")
    draft: Optional[bool] = Field(False, description="是否为草稿 PR（默认：False）")


class GetPullRequestInput(BaseModel):
    """
    获取 Pull Request 详细信息工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者")
    repo: str = Field(..., description="仓库名称")
    number: int = Field(..., description="PR 编号")


class UpdateIssueInput(BaseModel):
    """
    更新 Issue 工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者")
    repo: str = Field(..., description="仓库名称")
    number: int = Field(..., description="Issue 编号")
    state: Optional[str] = Field(None, description="状态：open 或 closed（可选）")
    title: Optional[str] = Field(None, description="标题（可选）")
    body: Optional[str] = Field(None, description="内容（可选，Markdown 格式）")
    labels: Optional[List[str]] = Field(None, description="标签列表（可选）")


class SearchRepositoriesInput(BaseModel):
    """
    搜索仓库工具的输入模型
    """
    query: str = Field(..., description="搜索查询字符串（支持 GitHub 搜索语法）")
    sort: Optional[str] = Field("stars", description="排序方式：stars, forks, updated（默认：stars）")
    order: Optional[str] = Field("desc", description="排序顺序：asc 或 desc（默认：desc）")
    limit: Optional[int] = Field(30, description="返回数量限制（默认：30，最大：100）")


class ListBranchesInput(BaseModel):
    """
    列出分支工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者")
    repo: str = Field(..., description="仓库名称")
    limit: Optional[int] = Field(100, description="返回数量限制（默认：100，最大：1000）")


class GetCommitInfoInput(BaseModel):
    """
    获取提交信息工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者")
    repo: str = Field(..., description="仓库名称")
    sha: str = Field(..., description="提交 SHA")


class ListCommitsInput(BaseModel):
    """
    列出提交历史工具的输入模型
    """
    owner: str = Field(..., description="仓库所有者")
    repo: str = Field(..., description="仓库名称")
    sha: Optional[str] = Field(None, description="分支或提交 SHA（可选，默认：默认分支）")
    path: Optional[str] = Field(None, description="文件路径（可选，仅列出该文件的提交）")
    limit: Optional[int] = Field(30, description="返回数量限制（默认：30，最大：100）")

