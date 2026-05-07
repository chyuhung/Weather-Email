# ============================================================
# Weather-Email 通用配置
# ============================================================
#
# 【设计原则】
#   - 本文件不包含任何敏感信息，可直接提交到 Git
#   - 所有敏感配置通过环境变量读取（.env / GitHub Secrets / 云函数环境变量）
#   - 环境变量可覆盖本文件中的默认值，方便不同部署环境定制
#
# 【环境变量优先级】
#   环境变量 > 本文件默认值
#
# ============================================================

import os

# ========== 天气数据源 ==========
# gaode = 高德天气（支持城市名/adcode/经纬度）
# caiyun = 彩云天气（仅支持经纬度，数据更丰富，推荐）
WEATHER_SOURCE: str = os.getenv("WEATHER_SOURCE", "caiyun")

# ========== 邮件发送者 ==========
SENDER_NAME: str = os.getenv("SENDER_NAME", "Weather-Email")

# ========== SMTP 配置 ==========
# 默认使用腾讯企业邮箱 SMTP，可通过环境变量覆盖为其他服务商
SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.exmail.qq.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
