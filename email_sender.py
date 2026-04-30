import smtplib
from email.mime.text import MIMEText

def send_email(sender, auth_code, receiver, subject, content, smtp_server, smtp_port, sender_name=None):
    msg = MIMEText(content, "plain", "utf-8")
    from_header = sender if not sender_name else f"{sender_name} <{sender}>"
    msg["From"] = from_header
    msg["To"] = receiver
    msg["Subject"] = subject

    try:
        # ===================== 腾讯企业邮箱 专用逻辑 =====================
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # 开启 TLS（腾讯必须用这个）
        server.login(sender, auth_code)  # auth_code = 你的邮箱密码（不过期）
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        return True

    except Exception as e:
        print("邮件发送异常：", e)
        return False