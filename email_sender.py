import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def _normalize_receivers(receiver):
    """统一转为列表：支持 'a,b,c' 字符串或 ['a','b'] 列表"""
    if isinstance(receiver, str):
        return [r.strip() for r in receiver.split(",") if r.strip()]
    if isinstance(receiver, (list, tuple)):
        return [r for r in receiver if r]
    return []


def send_email(sender, auth_code, receiver, subject, content, smtp_server, smtp_port, sender_name=None, is_html=False):
    receivers = _normalize_receivers(receiver)
    if not receivers:
        print("❌ 没有有效的收件人地址")
        return False

    # 邮件正文
    if is_html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(content, "html", "utf-8"))
    else:
        msg = MIMEText(content, "plain", "utf-8")

    from_header = sender if not sender_name else f"{sender_name} <{sender}>"
    msg["From"] = from_header
    # To 头显示所有收件人，用逗号分隔
    msg["To"] = ", ".join(receivers)
    msg["Subject"] = subject

    try:
        # ===================== 腾讯企业邮箱 专用逻辑 =====================
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, auth_code)
        server.sendmail(sender, receivers, msg.as_string())
        server.quit()
        print(f"✅ 邮件已发送至 {len(receivers)} 位收件人: {receivers}")
        return True

    except Exception as e:
        print("邮件发送异常：", e)
        return False
