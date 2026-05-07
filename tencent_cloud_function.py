"""
腾讯云函数：触发 GitHub Actions 运行 Weather-Email

部署说明：
1. 在腾讯云函数控制台创建函数，运行环境选 Python 3.x
2. 将本文件内容粘贴为函数代码
3. 在「环境变量」中配置以下变量：
   - GITHUB_TOKEN:  GitHub Personal Access Token（需 workflow 权限）
   - GITHUB_USER:   GitHub 用户名
   - REPO_NAME:     仓库名（如 Weather-Email）
4. 配置定时触发器：
   - 早间：cron "0 7 * * *"   (北京时间 07:00)
   - 晚间：cron "0 22 * * *"  (北京时间 22:00)

注意：本函数仅使用 Python 内置库，无需安装额外依赖。
"""

import json
import urllib.request
import urllib.error


def run() -> str:
    """
    调用 GitHub API 触发指定的 workflow dispatch。

    需要在环境变量中配置：
    - GITHUB_TOKEN:  GitHub PAT（必须勾选 workflow scope）
    - GITHUB_USER:   GitHub 用户名
    - REPO_NAME:     仓库名称
    - WORKFLOW_NAME: workflow 文件名（默认 daily-weather.yml）
    """
    import os

    github_token = os.getenv("GITHUB_TOKEN", "")
    github_user = os.getenv("GITHUB_USER", "")
    repo_name = os.getenv("REPO_NAME", "Weather-Email")
    workflow_name = os.getenv("WORKFLOW_NAME", "daily-weather.yml")

    if not github_token or not github_user:
        error_msg = "缺少环境变量 GITHUB_TOKEN 或 GITHUB_USER"
        print(f"❌ {error_msg}")
        return f"配置错误: {error_msg}"

    url = f"https://api.github.com/repos/{github_user}/{repo_name}/actions/workflows/{workflow_name}/dispatches"
    payload = json.dumps({"ref": "main"}).encode("utf-8")
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            status_code = resp.getcode()
            print(f"✅ 触发成功！状态码: {status_code}")
            return f"触发 Weather-Email 成功 (HTTP {status_code})"

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"❌ 触发失败，HTTP {e.code}: {body}")
        return f"触发失败: HTTP {e.code}"
    except urllib.error.URLError as e:
        print(f"❌ 网络错误: {e.reason}")
        return f"网络错误: {e.reason}"
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return f"触发异常: {str(e)}"


# 腾讯云函数入口（固定写法，请勿修改）
def main_handler(event, context):
    return run()
