# ============================================================
# Weather-Email 通用配置（无敏感信息）
# ============================================================
#
# 【位置配置】LOCATION 通过环境变量 LOCATION 读取，不写入代码
#   在 .env / GitHub Secrets / 云函数环境变量中设置
#   格式示例: LOCATION=116.3176,39.9760
#
# 【其他敏感配置】通过环境变量读取，不写入代码：
#   CAIYUN_TOKEN, GAODE_KEY, EMAIL_SENDER,
#   EMAIL_AUTH_CODE, EMAIL_RECEIVER / EMAIL_RECEIVERS
#
# ============================================================

# ========== 天气数据源 ==========
# gaode = 高德天气（支持城市名/adcode/经纬度）
# caiyun = 彩云天气（仅支持经纬度，数据更丰富）
WEATHER_SOURCE = "caiyun"  # 可选: "gaode" 或 "caiyun"

# ========== 邮件字段配置 ==========
# 邮件正文显示哪些字段（可自由增删）
WEATHER_FIELDS = [
    "城市",
    "温度",
    "体感温度",  # 彩云特有
    "天气",
    "湿度",
    "风向",
    "风力",
    "能见度",  # 彩云特有
    "气压",    # 彩云特有
    "AQI",     # 彩云特有
    "PM2.5",   # 彩云特有
    "空气质量", # 彩云特有
    "更新时间"
]

# ========== SMTP 配置 ==========
SENDER_NAME = "Weather-Email"
SMTP_SERVER = "smtp.exmail.qq.com"
SMTP_PORT   = 587