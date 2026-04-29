import smtplib
from email.mime.text import MIMEText

def send_email(sender, auth_code, receiver, subject, content, smtp_server, smtp_port):
    """发送邮件工具函数"""
    msg = MIMEText(content, "plain", "utf-8")
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender, auth_code)
            server.sendmail(sender, [receiver], msg.as_string())
        return True
    except:
        return False