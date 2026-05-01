# 云函数：触发 Weather-Email GitHub Action
# 作用：定时调用 GitHub API，运行天气邮件推送任务
# 使用 Python 内置库，无需安装依赖，云函数直接运行

import json
import urllib.request
import urllib.error

def run():
    # ========== 【必须修改这4个信息】 ==========
    GITHUB_TOKEN = "ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # 替换为你的 GitHub 个人访问令牌
    GITHUB_USER = "your-github-username"  # 替换为你的 GitHub 用户名
    REPO_NAME = "your-repo-name"  # 替换为你的 GitHub 仓库名
    WORKFLOW_NAME = "weather-email.yml"  # 替换为你的 GitHub Action 工作流文件名
    # =========================================

    # 构造请求数据：触发 main 分支
    payload = json.dumps({"ref": "main"}).encode('utf-8')

    # 请求头：身份认证
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }

    # GitHub API 地址
    url = f'https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/actions/workflows/{WORKFLOW_NAME}/dispatches'

    # 发送请求触发 Action
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        with urllib.request.urlopen(req) as resp:
            print(f"触发成功！状态码：{resp.getcode()}")
            return "触发 Weather-Email 成功"
    except urllib.error.HTTPError as e:
        print(f"触发失败，错误码：{e.code}，返回信息：{e.read().decode()}")
        return f"触发失败：{e.code}"
    except Exception as e:
        print(f"异常：{str(e)}")
        return f"触发异常：{str(e)}"


# 腾讯云函数入口（固定写法，不用改）
def main_handler(event, context):
    return run()