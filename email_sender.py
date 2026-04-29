import smtplib
from email.mime.text import MIMEText

def send_email(sender, auth_code, receiver, subject, content, smtp_server, smtp_port):
    msg = MIMEText(content, "plain", "utf-8")
    msg["From"] = sender
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