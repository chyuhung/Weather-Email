"""
Weather-Email 入口脚本
- 支持早晚两种推送模式：morning（今日）/ evening（明日）
- 支持 --dry-run 参数仅生成邮件内容不发送（用于调试）
- 所有敏感配置通过环境变量读取
"""

import argparse
import os
import sys
from config import SMTP_SERVER, SMTP_PORT, SENDER_NAME, WEATHER_SOURCE
from weather_api import WeatherAPI, CaiyunAPI
from email_sender import send_email, _normalize_receivers
from email_generator import generate_html

# 本地开发环境加载 .env 文件（生产环境不需要）
try:
    from dotenv import load_dotenv
    load_dotenv(encoding="utf-8-sig")
except ImportError:
    pass


def _load_env() -> dict[str, str | None]:
    """从环境变量加载配置，返回配置字典"""
    return {
        "GAODE_KEY": os.getenv("GAODE_KEY"),
        "CAIYUN_TOKEN": os.getenv("CAIYUN_TOKEN"),
        "EMAIL_SENDER": os.getenv("EMAIL_SENDER"),
        "EMAIL_AUTH_CODE": os.getenv("EMAIL_AUTH_CODE"),
        "EMAIL_RECEIVERS": os.getenv("EMAIL_RECEIVERS") or "",
        "LOCATION": os.getenv("LOCATION"),
    }


def _validate_config(config: dict) -> list[str]:
    """校验必填环境变量，返回缺失的变量名列表"""
    required = {
        "EMAIL_SENDER": "发件人邮箱",
        "EMAIL_AUTH_CODE": "邮箱授权码",
        "EMAIL_RECEIVERS": "收件人邮箱",
        "LOCATION": "经纬度",
    }
    missing = []
    for key, label in required.items():
        if not config.get(key):
            missing.append(f"{key}({label})")
    return missing


def main():
    parser = argparse.ArgumentParser(
        description="Weather-Email 天气邮件推送",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --mode morning     # 早间模式：推送今日天气
  python main.py --mode evening     # 晚间模式：推送明日天气
  python main.py --dry-run          # 调试模式：仅生成邮件内容，不发送
        """,
    )
    parser.add_argument(
        "--mode", choices=["morning", "evening"], default="evening",
        help="推送模式: morning=早间推送, evening=晚间推送 (默认: evening)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="调试模式：仅生成邮件内容并输出，不实际发送",
    )
    args = parser.parse_args()

    # ========== 加载配置 ==========
    config = _load_env()

    # 必填校验
    missing = _validate_config(config)
    if missing:
        print(f"❌ 缺少必填环境变量: {', '.join(missing)}")
        print("   请参考 .env.example 配置环境变量")
        sys.exit(1)

    print(f"🌤️ 正在获取天气... (模式: {args.mode}, 数据源: {WEATHER_SOURCE})")

    # ========== 获取天气数据 ==========
    weather = None
    if WEATHER_SOURCE == "caiyun":
        if not config["CAIYUN_TOKEN"]:
            print("❌ 彩云 API Token 缺失！请设置环境变量 CAIYUN_TOKEN")
            sys.exit(1)
        # hourlysteps=48: 覆盖完整的下一天（无论何时运行都能保证数据充足）
        # 早间模式需 dailysteps=1（仅今天），晚间模式需 dailysteps=2（今天+明天）
        hourlysteps = 48
        dailysteps = 1 if args.mode == "morning" else 2
        weather = CaiyunAPI.get_weather(
            config["LOCATION"], config["CAIYUN_TOKEN"],
            gaode_key=config["GAODE_KEY"],
            extensions="all",
            hourlysteps=hourlysteps,
            dailysteps=dailysteps,
        )
    else:
        if not config["GAODE_KEY"]:
            print("❌ 高德 API Key 缺失！请设置环境变量 GAODE_KEY")
            sys.exit(1)
        weather = WeatherAPI.get_weather(
            config["LOCATION"], config["GAODE_KEY"], extensions="all"
        )

    if not weather or not weather.get("success"):
        error_msg = weather.get("error", "未知错误") if weather else "无响应"
        print(f"❌ 天气获取失败: {error_msg}")
        sys.exit(1)

    print(f"✅ 天气获取成功 ({WEATHER_SOURCE}): {weather.get('city', '未知')}")

    if not weather.get("live"):
        print("❌ 天气实况数据为空，请检查 LOCATION 是否正确")
        sys.exit(1)

    # 输出彩云关键提示
    if weather.get("source") == "caiyun":
        kp = weather.get("forecast_keypoint", "")
        hd = weather.get("hourly_description", "")
        if kp:
            print(f"📌 关键提示: {kp}")
        if hd:
            print(f"📋 小时预报: {hd}")

    # ========== 生成邮件 ==========
    subject, html_body = generate_html(weather, mode=args.mode)
    print(f"📧 邮件主题: {subject}")

    # dry-run 模式：输出 HTML 到文件并退出
    if args.dry_run:
        output_file = f"weather_{args.mode}_{os.getenv('LOCATION', 'debug').replace(',', '_')}.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_body)
        print(f"🔍 调试模式：邮件内容已写入 {output_file}")
        print(f"   可用浏览器打开该文件预览邮件效果")
        return

    # ========== 发送邮件（逐封单独发送） ==========
    receivers = _normalize_receivers(config["EMAIL_RECEIVERS"])
    if not receivers:
        print("❌ 没有有效的收件人地址")
        sys.exit(1)

    print(f"📤 正在发送 {len(receivers)} 封邮件...")
    failed = 0
    for addr in receivers:
        ok = send_email(
            sender=config["EMAIL_SENDER"],
            auth_code=config["EMAIL_AUTH_CODE"],
            receiver=addr.strip(),
            subject=subject,
            content=html_body,
            smtp_server=SMTP_SERVER,
            smtp_port=SMTP_PORT,
            sender_name=SENDER_NAME,
            is_html=True,
        )
        if ok:
            print(f"   ✅ → {addr}")
        else:
            print(f"   ❌ → {addr}")
            failed += 1

    if failed == 0:
        print(f"✅ 全部 {len(receivers)} 封邮件发送成功！")
    else:
        print(f"⚠️ 发送完成：{len(receivers) - failed}/{len(receivers)} 成功，{failed} 封失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
