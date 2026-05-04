# Weather-Email

每日自动推送天气预报邮件，支持早间（morning）和傍晚（evening）两种模式，根据当日/次日天气数据生成穿衣建议与出行提醒。

---

## 功能特性

| 功能 | 说明 |
|-----|-----|
| **双模式推送** | 早间推送今日天气；傍晚推送明日天气 |
| **智能穿衣建议** | 根据温度区间自动生成穿着推荐 |
| **带伞提醒** | 自动判断雨雪天气，提示是否需要带伞 |
| **极端天气预警** | 高温防暑、防晒、大风、冰雪等标签提示 |
| **空气质量参考** | 显示 AQI、PM2.5 等指标（早间模式） |
| **定时执行** | 支持 GitHub Actions 或腾讯云函数触发 |

---

## 项目结构

```
Weather-Email/
├── main.py                 # 入口脚本，支持 --mode morning/evening
├── weather_api.py          # 天气数据获取（彩云天气 API + 高德逆地理）
├── email_generator.py     # HTML 邮件生成（双模式模板）
├── email_sender.py        # 邮件发送（SMTP）
├── config.py              # 通用配置（无敏感信息）
├── .env.example           # 本地环境变量示例
├── requirements.txt       # Python 依赖
├── .github/
│   └── workflows/
│       └── daily-weather.yml   # GitHub Actions 定时任务
└── tencent_cloud_function.py  # 腾讯云函数触发脚本（可选）
```

---

## 环境变量说明

所有敏感信息通过**环境变量**读取，不写入代码。

| 环境变量 | 必填 | 说明 | 示例 |
|---------|-----|------|------|
| `LOCATION` | **必填** | 经纬度，格式 `经度,纬度` | `116.3176,39.9760` |
| `CAIYUN_TOKEN` | 彩云必填 | 彩云天气 API Token | `eyJ...` |
| `GAODE_KEY` | 建议填写 | 高德地图 Key（用于城市名反查） | `a1b2c3d4...` |
| `EMAIL_SENDER` | 必填 | 发件人邮箱 | `sender@example.com` |
| `EMAIL_AUTH_CODE` | 必填 | 邮箱授权码（非登录密码） | `xxxxxx` |
| `EMAIL_RECEIVER` | 必填 | 收件人邮箱（单人） | `receiver@qq.com` |
| `EMAIL_RECEIVERS` | 可选 | 多收件人（逗号分隔，优先于 EMAIL_RECEIVER） | `a@,b@,c@` |
| `WEATHER_SOURCE` | 可选 | 天气数据源，默认 `caiyun` | `caiyun` |

---

## 快速开始

### 1. 安装依赖

```bash
pip install requests
```

### 2. 配置本地环境变量

复制示例文件：

```bash
cp .env.example .env
```

编辑 `.env`，填入你的实际配置：

```env
# 天气
CAIYUN_TOKEN=your-caiyun-token-here
GAODE_KEY=your-gaode-key-here
LOCATION=116.3176,39.9760
WEATHER_SOURCE=caiyun

# 邮件
EMAIL_SENDER=sender@example.com
EMAIL_AUTH_CODE=your-auth-code-here
EMAIL_RECEIVER=receiver@example.com
```

> `.env` 文件不会被提交到 Git（已在 `.gitignore` 中忽略）。

### 3. 运行测试

```bash
python main.py --mode morning   # 早间模式（今日天气）
python main.py --mode evening   # 傍晚模式（明日天气）
```

---

## API 申请

### 彩云天气 API

1. 访问 [彩云天气开放平台](https://open.caiyunapp.com)
2. 注册并获取 Token（个人版免费额度充足）
3. 填入 `CAIYUN_TOKEN`

### 高德地图逆地理（可选）

1. 访问 [高德开放平台](https://console.amap.com/dev/key/app)
2. 创建应用，获取 Web 服务 Key
3. 填入 `GAODE_KEY`（用于将经纬度转换为城市名称）

### 邮件授权码

腾讯企业邮箱：登录 [企业邮箱管理后台](https://exmail.qq.com) → 邮箱设置 → 客户端授权 → 生成授权码

---

## 定时部署

### 方案一：GitHub Actions（推荐）

1. 将项目推送至 GitHub 仓库（公开仓库，或使用 `workflow` scope 的 PAT）
2. 在仓库 `Settings → Secrets and variables → Actions` 中添加 Secrets：

| Secret 名称 | 说明 |
|------------|------|
| `LOCATION` | 经纬度，如 `116.3176,39.9760` |
| `CAIYUN_TOKEN` | 彩云 API Token |
| `GAODE_KEY` | 高德地图 Key |
| `EMAIL_SENDER` | 发件人邮箱 |
| `EMAIL_AUTH_CODE` | 邮箱授权码 |
| `EMAIL_RECEIVER` | 收件人邮箱 |

3. **定时任务**自动运行：
   - 早间推送：每天北京时间 07:00
   - 傍晚推送：每天北京时间 22:00

4. **手动触发**：在 Actions 页面点击 `Run workflow`，会自动根据当前北京时间选择模式

---

### 方案二：腾讯云函数

1. 将 `tencent_cloud_function.py` 部署到腾讯云函数
2. 在云函数环境变量中配置上述所有环境变量
3. 配置两个定时触发器：

| 触发器 | cron 表达式 | 说明 |
|-------|------------|------|
| 早间触发器 | `0 7 * * *` | 北京时间 07:00 |
| 晚间触发器 | `0 22 * * *` | 北京时间 22:00 |

> 腾讯云函数只需 `workflow` scope 的 GitHub PAT，不需要 `repo` scope。

---

## 邮件效果预览

**早间模式**：
- 顶部标题：今日天气预报
- Hero 概览卡：今日最低温 ~ 最高温、天气、湿度、风力
- 三时段卡片：上午 / 下午 / 晚间
- 次要信息：AQI、PM2.5、能见度、气压
- 一句话总结：穿衣建议 + 带伞提醒

**傍晚模式**：
- 顶部标题：明日天气预报
- Hero 概览卡：明日最低温 ~ 最高温、天气、湿度、风力
- 三时段卡片：明天上午 / 下午 / 晚间
- 一句话总结：穿衣建议 + 带伞提醒

---

## 自定义

### 穿衣建议阈值

在 `email_generator.py` 的 `_clothing_advice()` 函数中调整温度区间。

### 修改发件人名称

修改 `config.py` 中的 `SENDER_NAME`。

---

## 故障排查

| 问题 | 可能原因 | 解决方法 |
|-----|---------|---------|
| `彩云API错误` | CAIYUN_TOKEN 无效或超额 | 检查 token 或申请新 token |
| `触发失败：403` | PAT 权限不足 | 确认 PAT 勾选了 `workflow` scope |
| 邮件未收到 | SMTP 认证失败 | 检查授权码是否正确 |
| Action 报错 | Secrets 未配置 | 确认 GitHub 仓库 Secrets 已添加 |
| 天气数据为空 | LOCATION 格式错误 | 检查是否为 `经度,纬度` 格式 |

---

## 安全说明

- 所有 API 密钥、Token、授权码、邮箱、**位置信息**均通过环境变量读取
- `config.py` 不包含任何敏感数据，可直接提交到 Git
- `.gitignore` 已配置忽略 `.env`