import os
import argparse
from config import SMTP_SERVER, SMTP_PORT, SENDER_NAME, WEATHER_SOURCE
from weather_api import WeatherAPI, CaiyunAPI
from email_sender import send_email
from email_generator import generate_html

# 本地调试加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    parser = argparse.ArgumentParser(description="Weather-Email 天气邮件推送")
    parser.add_argument("--mode", choices=["morning", "evening"], default="evening",
                        help="推送模式: morning=早间推送, evening=晚间推送")
    args = parser.parse_args()

    # ========== 从环境变量读取配置 ==========
    GAODE_KEY       = os.getenv("GAODE_KEY")
    CAIYUN_TOKEN    = os.getenv("CAIYUN_TOKEN")
    EMAIL_SENDER    = os.getenv("EMAIL_SENDER")
    EMAIL_AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")
    EMAIL_RECEIVERS = os.getenv("EMAIL_RECEIVERS") or os.getenv("EMAIL_RECEIVER") or ""
    LOCATION        = os.getenv("LOCATION")  # 必填，格式 "经度,纬度"

    # 必填校验
    missing = [k for k, v in [
        ("EMAIL_SENDER",   EMAIL_SENDER),
        ("EMAIL_AUTH_CODE", EMAIL_AUTH_CODE),
        ("EMAIL_RECEIVER",  EMAIL_RECEIVERS),
        ("LOCATION",        LOCATION),
    ] if not v]

    if missing:
        print(f"❌ 缺少必填环境变量: {', '.join(missing)}")
        return

    print(f"正在获取天气... (模式: {args.mode})")

    # ========== 获取天气数据 ==========
    if WEATHER_SOURCE == "caiyun":
        if not CAIYUN_TOKEN:
            print("❌ 彩云 API Token 缺失！请设置环境变量 CAIYUN_TOKEN")
            return
        weather = CaiyunAPI.get_weather(
            LOCATION, CAIYUN_TOKEN,
            gaode_key=GAODE_KEY,
            extensions="all",
            hourlysteps=48
        )
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
        print("❌ 天气实况数据为空，请检查 LOCATION 是否正确")
        return

    # 彩云关键提示
    if weather.get("source") == "caiyun" and weather.get("forecast_keypoint"):
        print(f"🌤️ {weather['forecast_keypoint']}")

    # ========== 生成邮件 ==========
    subject, html_body = generate_html(weather, mode=args.mode)

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