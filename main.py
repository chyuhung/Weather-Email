import os
from config import *
from weather_api import WeatherAPI
from email_sender import send_email

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
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

    if not all([GAODE_KEY, EMAIL_SENDER, EMAIL_AUTH_CODE, EMAIL_RECEIVER]):
        print("❌ 环境变量缺失！")
        return

    # ========== 从 config 读取配置，完全灵活 ==========
    weather = WeatherAPI.get_weather(LOCATION, GAODE_KEY, extensions=WEATHER_TYPE)

    if not weather["success"]:
        print(f"❌ 天气获取失败: {weather['error']}")
        return

    print(f"✅ 天气获取成功: {weather['city']}")
    live = weather["live"]

    # ========== 根据 config 中的 WEATHER_FIELDS 动态生成邮件内容 ==========
    content = "【今日天气播报】\n"
    content += "------------------------\n"

    field_map = {
        "城市": f"城市：{live['city']}",
        "温度": f"温度：{live['temperature']}℃",
        "天气": f"天气：{live['weather']}",
        "湿度": f"湿度：{live['humidity']}%",
        "风向": f"风向：{live['wind_direction']}",
        "风力": f"风力：{live['wind_power']}级",
        "更新时间": f"更新时间：{live['report_time']}"
    }

    for field in WEATHER_FIELDS:
        if field in field_map:
            content += field_map[field] + "\n"

    # ========== 发送邮件 ==========
    print("📤 发送邮件中...")
    ok = send_email(
        sender=EMAIL_SENDER,
        auth_code=EMAIL_AUTH_CODE,
        receiver=EMAIL_RECEIVER,
        subject=f"{live['city']} {live['weather']} {live['temperature']}℃",
        content=content,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT
    )

    if ok:
        print("✅ 邮件发送成功！")
    else:
        print("❌ 邮件发送失败！")

if __name__ == "__main__":
    main()