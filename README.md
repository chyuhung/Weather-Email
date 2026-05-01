# Weather-Email

每日自动推送天气预报邮件，支持早间（morning）和傍晚（evening）两种模式，根据当日/次日天气数据生成穿衣建议与出行提醒。

---

## 功能特性

| 功能 | 说明 |
|-----|-----|
| **双模式推送** | 早间推送今日天气；傍晚推送明日天气 |
| **智能穿衣建议** | 根据温度区间（-10℃ ~ 35℃+）自动生成穿着推荐 |
| **带伞提醒** | 自动判断雨雪天气，提示是否需要带伞 |
| **极端天气预警** | 高温防暑、防晒、大风、冰雪等标签提示 |
| **空气质量参考** | 显示 AQI、PM2.5 等指标（早间模式） |
| **定时执行** | 支持 GitHub Actions 定时任务或腾讯云函数触发 |

---

## 项目结构

```
Weather-Email/
├── main.py                 # 入口脚本，支持 --mode morning/evening
├── weather_api.py          # 天气数据获取（彩云天气 API + 高德逆地理）
├── email_generator.py       # HTML 邮件生成（双模式模板）
├── email_sender.py         # 邮件发送（SMTP）
├── config.py               # 敏感配置（需创建 config.py 或设置环境变量）
├── requirements.txt        # Python 依赖
├── .github/
│   └── workflows/
│       └── daily-weather.yml   # GitHub Actions 定时任务
└── tencent_cloud_function.py  # 腾讯云函数触发脚本（可选）
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install requests
```

### 2. 配置 config.py

创建 `config.py`，填写以下配置：

```python
# 彩云天气（必填）
CAIYUN_TOKEN = "your-caiyun-token"

# 高德地图逆地理（必填）
GAODE_KEY = "your-gaode-key"

# 发件人邮箱
EMAIL_SENDER = "sender@example.com"

# 邮箱授权码（或登录密码）
EMAIL_AUTH_CODE = "your-auth-code"

# 收件人邮箱
EMAIL_RECEIVER = "receiver@example.com"
```

> 高德逆地理用于将经纬度转换为城市名称。如不需要可留空。

### 3. 配置 .env（可选，优先读取环境变量）

```env
CAIYUN_TOKEN=your-caiyun-token
GAODE_KEY=your-gaode-key
EMAIL_SENDER=sender@example.com
EMAIL_AUTH_CODE=your-auth-code
EMAIL_RECEIVER=receiver@example.com
```

### 4. 运行测试

```bash
# 早间模式（今日天气）
python main.py --mode morning

# 傍晚模式（明日天气）
python main.py --mode evening
```

---

## 配置说明

### 彩云天气 API

1. 访问 [彩云天气开放平台](https://open.caiyunapp.com)
2. 注册并获取 Token（个人版免费额度充足）
3. 填入 `CAIYUN_TOKEN`

### 高德地图逆地理

1. 访问 [高德开放平台](https://console.amap.com/dev/key/app)
2. 创建应用，获取 Web 服务 Key
3. 填入 `GAODE_KEY`

> 如不填写 `GAODE_KEY`，城市名称显示为"未知"，但天气数据不受影响。

### 邮件发送

使用腾讯企业邮箱 SMTP（推荐）：

| 配置项 | 值 |
|-------|-----|
| 服务器 | `smtp.exmail.qq.com` |
| 端口 | `587`（STARTTLS） |
| 用户名 | 发件人邮箱地址 |
| 授权码 | 企业邮箱密码或管理后台生成的授权码 |

其他 SMTP 服务器（如 Gmail、163 等）也可使用，修改 `email_sender.py` 中的服务器地址即可。

---

## 定时部署

### 方案一：GitHub Actions（推荐）

1. 将项目推送至 GitHub 仓库（**需设为公开仓库**，或使用 `workflow` scope 的 PAT）
2. 在 GitHub 仓库 `Settings → Secrets` 中添加以下 Secrets：
   - `CAIYUN_TOKEN`
   - `GAODE_KEY`
   - `EMAIL_SENDER`
   - `EMAIL_AUTH_CODE`
   - `EMAIL_RECEIVER`
3. Actions 会自动按定时计划运行：
   - 早间推送：每天北京时间 07:00
   - 傍晚推送：每天北京时间 22:00
4. 手动触发：在 Actions 页面点击 `Run workflow`，会自动根据当前北京时间选择模式

#### 手动触发 GitHub Actions

在 GitHub 仓库页面：`Actions → 天气邮件推送（早晚双时段）→ Run workflow`

---

### 方案二：腾讯云函数

1. 将 `tencent_cloud_function.py` 部署到腾讯云函数
2. 配置触发器：

| 触发器 | cron 表达式 | 说明 |
|-------|------------|------|
| 早间触发器 | `0 7 * * *` | 北京时间 07:00 |
| 晚间触发器 | `0 22 * * *` | 北京时间 22:00 |

3. 腾讯云函数只需 `workflow` scope 的 GitHub PAT，无需 `repo` scope

---

## 邮件效果预览

**早间模式**：
- 顶部标题：今日天气预报
- Hero 实况卡：当前温度、天气、湿度、风力
- 三时段卡片：上午 / 下午 / 晚间
- 次要信息：AQI、PM2.5、能见度、气压
- 一句话总结：穿衣建议 + 带伞提醒

**傍晚模式**：
- 顶部标题：明日天气预报
- Hero 概览卡：明日最高温 / 最低温
- 三时段卡片：明天上午 / 下午 / 晚间
- 一句话总结：穿衣建议 + 带伞提醒

---

## 自定义

### 修改推送地点

在 `main.py` 中修改经纬度：

```python
# 重庆蔡家岗街道
LAT, LON = 29.735, 106.506
```

### 穿衣建议阈值

在 `email_generator.py` 的 `_clothing_advice()` 函数中调整温度区间。

### 修改发件人邮箱

修改 `email_sender.py` 中的 SMTP 配置，或在 `config.py` 中更新 `EMAIL_SENDER`。

---

## 故障排查

| 问题 | 可能原因 | 解决方法 |
|-----|---------|---------|
| `彩云API错误` | CAIYUN_TOKEN 无效或超额 | 检查 token 或申请新 token |
| `触发失败：403` | PAT 权限不足 | 确认 PAT 勾选了 `workflow` scope |
| 邮件未收到 | SMTP 认证失败 | 检查授权码是否正确 |
| Action 报错 | Secrets 未配置 | 确认 GitHub 仓库 Secrets 已添加 |
| HTML 显示乱码 | 编码问题 | 确保文件为 UTF-8 编码 |
