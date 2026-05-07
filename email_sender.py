"""
邮件发送模块
- 通过 SMTP 协议发送邮件（支持 HTML 和纯文本）
- 支持多收件人（逗号分隔字符串或列表）
- 内置连接超时和重试机制
"""

import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Union


def _normalize_receivers(receiver: Union[str, list, tuple, None]) -> list[str]:
    """
    将收件人参数统一转为邮件地址列表。

    支持格式：
    - 单个字符串: "user@example.com"
    - 逗号分隔字符串: "a@example.com,b@example.com"
    - 列表/元组: ["a@example.com", "b@example.com"]
    """
    if not receiver:
        return []
    if isinstance(receiver, str):
        return [addr.strip() for addr in receiver.split(",") if addr.strip()]
    if isinstance(receiver, (list, tuple)):
        return [addr for addr in receiver if addr]
    return []


def send_email(
    sender: str,
    auth_code: str,
    receiver: Union[str, list, tuple],
    subject: str,
    content: str,
    smtp_server: str,
    smtp_port: int = 587,
    sender_name: Optional[str] = None,
    is_html: bool = False,
    timeout: int = 30,
    max_retries: int = 2,
) -> bool:
    """
    发送邮件。

    Args:
        sender:       发件人邮箱地址
        auth_code:    邮箱授权码（非登录密码）
        receiver:     收件人，支持字符串、逗号分隔字符串或列表
        subject:      邮件主题
        content:      邮件正文
        smtp_server:  SMTP 服务器地址
        smtp_port:    SMTP 端口（默认 587）
        sender_name:  发件人显示名称（可选，如 "Weather-Email"）
        is_html:      是否为 HTML 格式（默认 False）
        timeout:      连接超时时间（秒，默认 30）
        max_retries:  最大重试次数（默认 2）

    Returns:
        True 发送成功，False 发送失败
    """
    receivers = _normalize_receivers(receiver)
    if not receivers:
        print("❌ 没有有效的收件人地址")
        return False

    # 构造邮件对象
    if is_html:
        msg = MIMEMultipart("alternative")
        # 同时附上纯文本版本，提升兼容性（部分邮件客户端优先显示纯文本）
        msg.attach(MIMEText("请使用支持 HTML 的邮件客户端查看此邮件。", "plain", "utf-8"))
        msg.attach(MIMEText(content, "html", "utf-8"))
    else:
        msg = MIMEText(content, "plain", "utf-8")

    # 邮件头
    from_header = f"{sender_name} <{sender}>" if sender_name else sender
    msg["From"] = from_header
    msg["To"] = ", ".join(receivers)
    msg["Subject"] = subject
    msg["X-Mailer"] = "Weather-Email"

    # 带重试的发送逻辑
    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=timeout)
            try:
                server.starttls()         # 启用 TLS 加密
                server.login(sender, auth_code)
                server.sendmail(sender, receivers, msg.as_string())
            finally:
                server.quit()             # 确保连接关闭

            print(f"✅ 邮件已发送至 {len(receivers)} 位收件人")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ SMTP 认证失败: {e}")
            return False  # 认证错误无需重试
        except smtplib.SMTPException as e:
            last_error = e
            print(f"⚠️ SMTP 错误 (第 {attempt}/{max_retries} 次): {e}")
        except (ConnectionError, TimeoutError, OSError) as e:
            last_error = e
            print(f"⚠️ 网络超时或连接错误 (第 {attempt}/{max_retries} 次): {e}")
        except Exception as e:
            last_error = e
            print(f"⚠️ 邮件发送异常 (第 {attempt}/{max_retries} 次): {e}")

        # 重试前等待
        if attempt < max_retries:
            time.sleep(2)

    print(f"❌ 邮件发送失败，已重试 {max_retries} 次")
    if last_error:
        print(f"   最后错误: {last_error}")
    return False
