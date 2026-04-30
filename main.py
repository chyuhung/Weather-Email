import os
from config import *
from weather_api import WeatherAPI, CaiyunAPI
from email_sender import send_email
from email_generator import generate_html

# 本地调试加载.env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    print("正在获取天气...")

    # 从环境变量读取敏感信息
    GAODE_KEY = os.getenv("GAODE_KEY")
    CAIYUN_TOKEN = os.getenv("CAIYUN_TOKEN")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")
    # 支持 EMAIL_RECEIVERS（逗号分隔字符串）或 EMAIL_RECEIVER（单个）
    EMAIL_RECEIVERS = os.getenv("EMAIL_RECEIVERS") or os.getenv("EMAIL_RECEIVER") or ""

    if not all([EMAIL_SENDER, EMAIL_AUTH_CODE, EMAIL_RECEIVERS]):
        print("❌ 邮箱环境变量缺失！")
        return

    # ========== 根据数据源选择 API ==========
    if WEATHER_SOURCE == "caiyun":
        if not CAIYUN_TOKEN:
            print("❌ 彩云 API Token 缺失！请设置环境变量 CAIYUN_TOKEN")
            return
        weather = CaiyunAPI.get_weather(LOCATION, CAIYUN_TOKEN, gaode_key=GAODE_KEY, extensions="all")
    else:
        if not GAODE_KEY:
            print("❌ 高德 API Key 缺失！请设置环境变量 GAODE_KEY")
            return
        weather = WeatherAPI.get_weather(LOCATION, GAODE_KEY, extensions="all")

    if not weather["success"]:
        print(f"❌ 天气获取失败: {weather['error']}")
        return

    print(f"✅ 天气获取成功 ({WEATHER_SOURCE}): {weather['city']}")

    live = weather.get("live")
    if live is None:
        print("❌ 天气实况数据为空，请检查配置是否正确")
        return

    # 彩云关键提示打印
    if weather.get("source") == "caiyun" and weather.get("forecast_keypoint"):
        print(f"🌤️ {weather['forecast_keypoint']}")

    # ========== 生成精美邮件（HTML） ==========
    subject, html_body = generate_html(weather)

    print(f"📧 邮件主题: {subject}")
    print("📤 发送邮件中...")

    ok = send_email(
        sender=EMAIL_SENDER,
        auth_code=EMAIL_AUTH_CODE,
        receiver=EMAIL_RECEIVERS,
        subject=subject,
        content=html_body,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT,
        sender_name=SENDER_NAME,
        is_html=True
    )

    if ok:
        print("✅ 邮件发送成功！")
    else:
        print("❌ 邮件发送失败！")

if __name__ == "__main__":
    main()
