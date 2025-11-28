"""
GitHub API 客户端封装

说明：
这个模块封装了 GitHub API 的调用，提供简洁的接口供 MCP 服务器使用。
使用 PyGithub 库与 GitHub API 交互。
"""

import base64
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from github import Github, GithubException
    from github.Repository import Repository
    from github.ContentFile import ContentFile
    from github.Issue import Issue
    from github.PullRequest import PullRequest
except ImportError as e:
    raise ImportError(
        "无法导入 PyGithub 库。请安装依赖：\n"
        "pip install PyGithub"
    ) from e

logger = logging.getLogger('github-mcp-client')


class GitHubClient:
    """
    GitHub API 客户端类
    
    说明：
    - 封装 GitHub API 调用
    - 处理错误和异常
    - 提供类型安全的数据转换
    """
    
    def __init__(self, token: str):
        """
        初始化 GitHub 客户端
        
        参数：
        - token: GitHub 个人访问令牌（Personal Access Token）
        """
        if not token:
            raise ValueError("GitHub token 不能为空")
        
        self.github = Github(token)
        logger.info("GitHub 客户端初始化成功")
    
    def search_code(self, query: str) -> Dict[str, Any]:
        """
        搜索代码
        
        参数：
        - query: GitHub 代码搜索查询字符串
        
        返回：
        - 包含搜索结果和总数的字典
        """
        try:
            logger.info(f"搜索代码: {query}")
            results = self.github.search_code(query)
            
            items = []
            # 限制返回前 30 个结果（GitHub API 限制）
            for item in list(results[:30]):
                items.append({
                    "name": item.name,
                    "path": item.path,
                    "repository": {
                        "full_name": item.repository.full_name,
                        "html_url": item.repository.html_url
                    },
                    "html_url": item.html_url,
                    "sha": item.sha
                })
            
            return {
                "total_count": results.totalCount,
                "items": items
            }
        except GithubException as e:
            logger.error(f"搜索代码失败: {e}")
            raise ValueError(f"搜索代码失败: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"搜索代码时发生错误: {e}", exc_info=True)
            raise ValueError(f"搜索代码时发生错误: {str(e)}")
    
    def get_repository(self, owner: str, repo: str) -> Repository:
        """
        获取仓库对象
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        
        返回：
        - Repository 对象
        """
        try:
            full_name = f"{owner}/{repo}"
            repository = self.github.get_repo(full_name)
            logger.debug(f"获取仓库: {full_name}")
            return repository
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"仓库不存在: {owner}/{repo}")
            logger.error(f"获取仓库失败: {e}")
            raise ValueError(f"获取仓库失败: {e.data.get('message', str(e))}")
    
    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        获取仓库信息
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        
        返回：
        - 仓库信息字典
        """
        try:
            repository = self.get_repository(owner, repo)
            
            return {
                "name": repository.name,
                "full_name": repository.full_name,
                "description": repository.description,
                "language": repository.language,
                "stars": repository.stargazers_count,
                "forks": repository.forks_count,
                "open_issues": repository.open_issues_count,
                "default_branch": repository.default_branch,
                "html_url": repository.html_url,
                "created_at": repository.created_at.isoformat() if repository.created_at else None,
                "updated_at": repository.updated_at.isoformat() if repository.updated_at else None
            }
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"获取仓库信息失败: {e}", exc_info=True)
            raise ValueError(f"获取仓库信息失败: {str(e)}")
    
    def get_file_content(self, owner: str, repo: str, path: str, ref: Optional[str] = None) -> Dict[str, Any]:
        """
        获取文件内容
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        - path: 文件路径
        - ref: 分支、标签或提交 SHA（可选）
        
        返回：
        - 文件内容字典
        """
        try:
            repository = self.get_repository(owner, repo)
            
            # 获取文件内容
            if ref:
                content_file = repository.get_contents(path, ref=ref)
            else:
                content_file = repository.get_contents(path)
            
            if not isinstance(content_file, ContentFile):
                raise ValueError(f"路径 '{path}' 不是文件（可能是目录）")
            
            # 解码 Base64 内容
            try:
                content = base64.b64decode(content_file.content).decode('utf-8')
            except Exception as e:
                logger.warning(f"解码文件内容失败: {e}")
                content = f"[无法解码文件内容: {str(e)}]"
            
            return {
                "path": content_file.path,
                "content": content,
                "encoding": content_file.encoding or "base64",
                "size": content_file.size,
                "sha": content_file.sha,
                "html_url": content_file.html_url
            }
        except ValueError:
            raise
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"文件不存在: {owner}/{repo}/{path}")
            logger.error(f"获取文件内容失败: {e}")
            raise ValueError(f"获取文件内容失败: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"获取文件内容时发生错误: {e}", exc_info=True)
            raise ValueError(f"获取文件内容时发生错误: {str(e)}")
    
    def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        列出仓库的 Issue
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        - state: Issue 状态（open, closed, all）
        - limit: 返回数量限制（最大 100）
        
        返回：
        - Issue 信息列表
        """
        try:
            repository = self.get_repository(owner, repo)
            
            # 验证状态参数
            if state not in ["open", "closed", "all"]:
                raise ValueError(f"无效的状态参数: {state}，必须是 open、closed 或 all")
            
            # 限制返回数量
            limit = min(max(1, limit), 100)
            
            issues = repository.get_issues(state=state)
            issue_list = []
            
            for issue in list(issues[:limit]):
                # 过滤掉 Pull Request（GitHub API 中 PR 也是 Issue）
                if issue.pull_request:
                    continue
                
                issue_list.append({
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body,
                    "state": issue.state,
                    "labels": [label.name for label in issue.labels],
                    "user": issue.user.login if issue.user else "unknown",
                    "created_at": issue.created_at.isoformat() if issue.created_at else None,
                    "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                    "html_url": issue.html_url
                })
            
            logger.info(f"获取到 {len(issue_list)} 个 Issue")
            return issue_list
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"列出 Issue 失败: {e}", exc_info=True)
            raise ValueError(f"列出 Issue 失败: {str(e)}")
    
    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        创建 Issue
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        - title: Issue 标题
        - body: Issue 内容（可选）
        - labels: 标签列表（可选）
        
        返回：
        - 创建的 Issue 信息
        """
        try:
            repository = self.get_repository(owner, repo)
            
            issue = repository.create_issue(
                title=title,
                body=body or "",
                labels=labels or []
            )
            
            logger.info(f"创建 Issue #{issue.number}: {title}")
            
            return {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "labels": [label.name for label in issue.labels],
                "user": issue.user.login if issue.user else "unknown",
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
                "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                "html_url": issue.html_url
            }
        except ValueError:
            raise
        except GithubException as e:
            logger.error(f"创建 Issue 失败: {e}")
            raise ValueError(f"创建 Issue 失败: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"创建 Issue 时发生错误: {e}", exc_info=True)
            raise ValueError(f"创建 Issue 时发生错误: {str(e)}")
    
    def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        列出仓库的 Pull Request
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        - state: PR 状态（open, closed, all）
        - limit: 返回数量限制（最大 100）
        
        返回：
        - Pull Request 信息列表
        """
        try:
            repository = self.get_repository(owner, repo)
            
            # 验证状态参数
            if state not in ["open", "closed", "all"]:
                raise ValueError(f"无效的状态参数: {state}，必须是 open、closed 或 all")
            
            # 限制返回数量
            limit = min(max(1, limit), 100)
            
            pull_requests = repository.get_pulls(state=state)
            pr_list = []
            
            for pr in list(pull_requests[:limit]):
                pr_list.append({
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "state": pr.state,
                    "user": pr.user.login if pr.user else "unknown",
                    "head": pr.head.ref,
                    "base": pr.base.ref,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                    "html_url": pr.html_url
                })
            
            logger.info(f"获取到 {len(pr_list)} 个 Pull Request")
            return pr_list
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"列出 Pull Request 失败: {e}", exc_info=True)
            raise ValueError(f"列出 Pull Request 失败: {str(e)}")
    
    def list_user_repos(
        self,
        username: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        列出用户的所有仓库
        
        参数：
        - username: GitHub 用户名（可选，默认：当前认证用户）
        - limit: 返回数量限制（最大 1000）
        
        返回：
        - 包含仓库列表和统计信息的字典
        """
        try:
            # 限制返回数量
            limit = min(max(1, limit), 1000)
            
            # 获取用户对象
            if username:
                user = self.github.get_user(username)
                logger.info(f"获取用户 {username} 的仓库列表")
            else:
                user = self.github.get_user()
                logger.info(f"获取当前认证用户 {user.login} 的仓库列表")
            
            # 获取所有仓库
            repos = user.get_repos()
            repo_list = []
            
            for repo in list(repos[:limit]):
                repo_list.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "language": repo.language,
                    "private": repo.private,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "open_issues": repo.open_issues_count,
                    "default_branch": repo.default_branch,
                    "html_url": repo.html_url,
                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
                })
            
            # 统计信息
            total = len(repo_list)
            public_count = sum(1 for r in repo_list if not r["private"])
            private_count = sum(1 for r in repo_list if r["private"])
            
            logger.info(f"获取到 {total} 个仓库（公开: {public_count}, 私有: {private_count}）")
            
            return {
                "user": user.login,
                "total_count": total,
                "public_count": public_count,
                "private_count": private_count,
                "repos": repo_list
            }
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"用户不存在: {username}")
            logger.error(f"列出用户仓库失败: {e}")
            raise ValueError(f"列出用户仓库失败: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"列出用户仓库时发生错误: {e}", exc_info=True)
            raise ValueError(f"列出用户仓库时发生错误: {str(e)}")
    
    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
        draft: bool = False
    ) -> Dict[str, Any]:
        """
        创建 Pull Request
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        - title: PR 标题
        - head: 源分支
        - base: 目标分支
        - body: PR 描述（可选）
        - draft: 是否为草稿 PR（默认：False）
        
        返回：
        - 创建的 PR 信息
        """
        try:
            repository = self.get_repository(owner, repo)
            
            pr = repository.create_pull(
                title=title,
                body=body or "",
                head=head,
                base=base,
                draft=draft
            )
            
            logger.info(f"创建 PR #{pr.number}: {title}")
            
            return {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "user": pr.user.login if pr.user else "unknown",
                "head": pr.head.ref,
                "base": pr.base.ref,
                "draft": pr.draft,
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                "html_url": pr.html_url
            }
        except ValueError:
            raise
        except GithubException as e:
            logger.error(f"创建 PR 失败: {e}")
            raise ValueError(f"创建 PR 失败: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"创建 PR 时发生错误: {e}", exc_info=True)
            raise ValueError(f"创建 PR 时发生错误: {str(e)}")
    
    def get_pull_request(self, owner: str, repo: str, number: int) -> Dict[str, Any]:
        """
        获取 Pull Request 详细信息
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        - number: PR 编号
        
        返回：
        - PR 详细信息
        """
        try:
            repository = self.get_repository(owner, repo)
            pr = repository.get_pull(number)
            
            # 获取变更文件列表
            files = pr.get_files()
            changed_files = []
            for file in list(files):
                changed_files.append({
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes
                })
            
            # 获取评论数量
            comments_count = pr.comments
            
            logger.info(f"获取 PR #{number} 详细信息")
            
            return {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "user": pr.user.login if pr.user else "unknown",
                "head": pr.head.ref,
                "base": pr.base.ref,
                "draft": pr.draft,
                "merged": pr.merged,
                "mergeable": pr.mergeable,
                "comments": comments_count,
                "changed_files": changed_files,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files_count": len(changed_files),
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "html_url": pr.html_url
            }
        except ValueError:
            raise
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"PR 不存在: #{number}")
            logger.error(f"获取 PR 失败: {e}")
            raise ValueError(f"获取 PR 失败: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"获取 PR 时发生错误: {e}", exc_info=True)
            raise ValueError(f"获取 PR 时发生错误: {str(e)}")
    
    def update_issue(
        self,
        owner: str,
        repo: str,
        number: int,
        state: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        更新 Issue
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        - number: Issue 编号
        - state: 状态（open 或 closed，可选）
        - title: 标题（可选）
        - body: 内容（可选）
        - labels: 标签列表（可选）
        
        返回：
        - 更新后的 Issue 信息
        """
        try:
            repository = self.get_repository(owner, repo)
            issue = repository.get_issue(number)
            
            # 构建更新参数
            edit_params = {}
            if state is not None:
                if state not in ["open", "closed"]:
                    raise ValueError(f"无效的状态参数: {state}，必须是 open 或 closed")
                edit_params["state"] = state
            if title is not None:
                edit_params["title"] = title
            if body is not None:
                edit_params["body"] = body
            if labels is not None:
                edit_params["labels"] = labels
            
            # 执行更新
            if edit_params:
                issue.edit(**edit_params)
                # 重新获取更新后的 Issue
                issue = repository.get_issue(number)
            
            logger.info(f"更新 Issue #{number}")
            
            return {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "labels": [label.name for label in issue.labels],
                "user": issue.user.login if issue.user else "unknown",
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
                "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                "html_url": issue.html_url
            }
        except ValueError:
            raise
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"Issue 不存在: #{number}")
            logger.error(f"更新 Issue 失败: {e}")
            raise ValueError(f"更新 Issue 失败: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"更新 Issue 时发生错误: {e}", exc_info=True)
            raise ValueError(f"更新 Issue 时发生错误: {str(e)}")
    
    def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        搜索仓库
        
        参数：
        - query: 搜索查询字符串（支持 GitHub 搜索语法）
        - sort: 排序方式（stars, forks, updated，默认：stars）
        - order: 排序顺序（asc 或 desc，默认：desc）
        - limit: 返回数量限制（最大 100）
        
        返回：
        - 搜索结果
        """
        try:
            # 验证排序参数
            if sort not in ["stars", "forks", "updated"]:
                raise ValueError(f"无效的排序方式: {sort}，必须是 stars、forks 或 updated")
            if order not in ["asc", "desc"]:
                raise ValueError(f"无效的排序顺序: {order}，必须是 asc 或 desc")
            
            # 限制返回数量
            limit = min(max(1, limit), 100)
            
            logger.info(f"搜索仓库: {query} (sort={sort}, order={order})")
            results = self.github.search_repositories(query, sort=sort, order=order)
            
            items = []
            for repo in list(results[:limit]):
                items.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "language": repo.language,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "open_issues": repo.open_issues_count,
                    "private": repo.private,
                    "html_url": repo.html_url,
                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
                })
            
            return {
                "total_count": results.totalCount,
                "items": items
            }
        except ValueError:
            raise
        except GithubException as e:
            logger.error(f"搜索仓库失败: {e}")
            raise ValueError(f"搜索仓库失败: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"搜索仓库时发生错误: {e}", exc_info=True)
            raise ValueError(f"搜索仓库时发生错误: {str(e)}")
    
    def list_branches(
        self,
        owner: str,
        repo: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        列出仓库的分支
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        - limit: 返回数量限制（最大 1000）
        
        返回：
        - 分支列表
        """
        try:
            repository = self.get_repository(owner, repo)
            
            # 限制返回数量
            limit = min(max(1, limit), 1000)
            
            branches = repository.get_branches()
            branch_list = []
            
            for branch in list(branches[:limit]):
                branch_list.append({
                    "name": branch.name,
                    "sha": branch.commit.sha,
                    "protected": branch.protected,
                    "html_url": f"{repository.html_url}/tree/{branch.name}"
                })
            
            logger.info(f"获取到 {len(branch_list)} 个分支")
            return branch_list
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"列出分支失败: {e}", exc_info=True)
            raise ValueError(f"列出分支失败: {str(e)}")
    
    def get_commit_info(self, owner: str, repo: str, sha: str) -> Dict[str, Any]:
        """
        获取提交信息
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        - sha: 提交 SHA
        
        返回：
        - 提交详细信息
        """
        try:
            repository = self.get_repository(owner, repo)
            commit = repository.get_commit(sha)
            
            # 获取变更文件
            files = commit.files
            changed_files = []
            for file in files:
                changed_files.append({
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes
                })
            
            logger.info(f"获取提交信息: {sha[:7]}")
            
            return {
                "sha": commit.sha,
                "message": commit.commit.message,
                "author": {
                    "name": commit.commit.author.name,
                    "email": commit.commit.author.email,
                    "date": commit.commit.author.date.isoformat() if commit.commit.author.date else None
                },
                "committer": {
                    "name": commit.commit.committer.name,
                    "email": commit.commit.committer.email,
                    "date": commit.commit.committer.date.isoformat() if commit.commit.committer.date else None
                },
                "stats": {
                    "additions": commit.stats.additions,
                    "deletions": commit.stats.deletions,
                    "total": commit.stats.total
                },
                "changed_files": changed_files,
                "changed_files_count": len(changed_files),
                "html_url": commit.html_url
            }
        except ValueError:
            raise
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"提交不存在: {sha}")
            logger.error(f"获取提交信息失败: {e}")
            raise ValueError(f"获取提交信息失败: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"获取提交信息时发生错误: {e}", exc_info=True)
            raise ValueError(f"获取提交信息时发生错误: {str(e)}")
    
    def list_commits(
        self,
        owner: str,
        repo: str,
        sha: Optional[str] = None,
        path: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        列出仓库的提交历史
        
        参数：
        - owner: 仓库所有者
        - repo: 仓库名称
        - sha: 分支或提交 SHA（可选，默认：默认分支）
        - path: 文件路径（可选，仅列出该文件的提交）
        - limit: 返回数量限制（最大 100）
        
        返回：
        - 提交列表
        """
        try:
            repository = self.get_repository(owner, repo)
            
            # 限制返回数量
            limit = min(max(1, limit), 100)
            
            # 获取提交列表
            if sha:
                commits = repository.get_commits(sha=sha, path=path)
            else:
                commits = repository.get_commits(path=path)
            
            commit_list = []
            for commit in list(commits[:limit]):
                commit_list.append({
                    "sha": commit.sha,
                    "message": commit.commit.message.split('\n')[0],  # 只取第一行
                    "author": {
                        "name": commit.commit.author.name,
                        "email": commit.commit.author.email,
                        "date": commit.commit.author.date.isoformat() if commit.commit.author.date else None
                    },
                    "committer": {
                        "name": commit.commit.committer.name,
                        "email": commit.commit.committer.email,
                        "date": commit.commit.committer.date.isoformat() if commit.commit.committer.date else None
                    },
                    "html_url": commit.html_url
                })
            
            logger.info(f"获取到 {len(commit_list)} 个提交")
            return commit_list
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"列出提交失败: {e}", exc_info=True)
            raise ValueError(f"列出提交失败: {str(e)}")

