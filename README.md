# Weather-Email

每日自动推送天气预报邮件，支持早间（morning）和傍晚（evening）两种模式，基于彩云天气/高德天气 API 获取数据，智能生成穿衣建议与出行提醒。

---

## 功能特性

| 功能 | 说明 |
|-----|------|
| **双模式推送** | 早间推送今日天气；傍晚推送明日天气 |
| **双数据源** | 彩云天气（推荐，数据丰富）与高德天气（支持城市名/adcode） |
| **分时段预报** | 上午/下午/晚间三时段，每时段显示温度区间和降水概率 |
| **生活指数** | 紫外线、穿衣、舒适度、感冒风险、洗车建议 |
| **智能穿衣建议** | 根据温度区间 + 温差自动生成穿着推荐 |
| **带伞提醒** | 自动判断雨雪天气，三时段独立标识 |
| **空气质量** | 早间显示实况 AQI/PM2.5/PM10/O₃，晚间显示预计空气质量 |
| **极端天气预警** | 高温防暑、防晒、大风、冰雪等标签提示 |
| **日出日落** | 显示目标日期的日出日落时间 |
| **自适应配色** | 根据天气语义自动切换邮件主题色（晴/雨/雪/雾/风/雷/高温） |
| **调试模式** | `--dry-run` 生成 HTML 文件本地预览 |
| **多天气预览** | 内置 `preview_demo.py` 一键生成所有天气场景的邮件效果 |
| **定时执行** | 支持 GitHub Actions 或腾讯云函数触发 |

---

## 项目结构

```
Weather-Email/
├── main.py                     # 入口脚本（支持 --mode / --dry-run）
├── weather_api.py              # 天气数据获取（彩云天气 + 高德天气）
├── email_generator.py          # HTML 邮件生成（双模式模板 + 自适应配色）
├── email_sender.py             # 邮件发送（SMTP，内置超时和重试）
├── config.py                   # 通用配置（无敏感信息，支持环境变量覆盖）
├── preview_demo.py             # 本地多天气预览生成器（14 种天气场景）
├── tencent_cloud_function.py   # 腾讯云函数触发脚本（通过 GitHub API）
├── .env.example                # 本地环境变量示例
├── .gitignore
├── LICENSE
├── README.md
└── .github/
    └── workflows/
        └── daily-weather.yml   # GitHub Actions 定时任务
```

---

## 环境变量说明

所有敏感信息通过**环境变量**读取，不写入代码。`config.py` 中的 SMTP 等默认配置均可通过同名环境变量覆盖。

| 环境变量 | 必填 | 说明 | 默认值 |
|---------|-----|------|--------|
| `LOCATION` | **必填** | 经纬度，格式 `经度,纬度` | — |
| `CAIYUN_TOKEN` | 彩云必填 | 彩云天气 API Token | — |
| `GAODE_KEY` | 建议填写 | 高德地图 Key（用于城市名反查） | — |
| `EMAIL_SENDER` | **必填** | 发件人邮箱 | — |
| `EMAIL_AUTH_CODE` | **必填** | 邮箱授权码（非登录密码） | — |
| `EMAIL_RECEIVERS` | **必填** | 收件人（支持多人，逗号分隔，每位单独发送） | — |
| `WEATHER_SOURCE` | 可选 | 天气数据源，`caiyun` 或 `gaode` | `caiyun` |
| `SENDER_NAME` | 可选 | 发件人显示名称 | `Weather-Email` |
| `SMTP_SERVER` | 可选 | SMTP 服务器 | `smtp.exmail.qq.com` |
| `SMTP_PORT` | 可选 | SMTP 端口 | `587` |

---

## Python 版本说明

- **推荐版本：Python 3.12.x**
- GitHub Actions 当前固定使用 **Python 3.12.10**
- 本地开发建议同样使用 **Python 3.12 或更高版本**


---

## 快速开始

### 1. 安装依赖

```bash
pip install requests python-dotenv
```

### 2. 配置本地环境变量

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
EMAIL_RECEIVERS=user1@example.com,user2@example.com
```

> `.env` 文件不会被提交到 Git（已在 `.gitignore` 中忽略）。

### 3. 运行

```bash
python main.py --mode morning    # 早间模式（今日天气）
python main.py --mode evening    # 傍晚模式（明日天气）
python main.py --dry-run         # 调试模式（生成 HTML 本地预览）
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

### 邮箱授权码

- **腾讯企业邮箱**：登录 [企业邮箱管理后台](https://exmail.qq.com) → 邮箱设置 → 客户端授权
- **QQ 邮箱**：设置 → 账户 → POP3/SMTP 服务 → 生成授权码

---

## 本地预览

### 调试模式

```bash
python main.py --dry-run
```

会在当前目录生成 `weather_{mode}_{location}.html` 文件，可用浏览器直接打开预览。

### 多天气场景预览

内置 `preview_demo.py` 可一键生成 14 种天气场景（晴、多云、阴、小雨、暴雨、小雪、大雪、雾、浓雾、微风、大风、雷阵雨、强雷暴、高温）的早晚双模式邮件 HTML：

```bash
python preview_demo.py          # 生成所有场景（morning + evening）
python preview_demo.py --mode morning   # 仅生成早间模式
python preview_demo.py --mode evening   # 仅生成傍晚模式
python preview_demo.py --open          # 生成后自动打开索引页
```

生成的文件会以 `preview_{编号}_{模式}_{主题}.html` 命名，并附带一个 `preview_index.html` 索引页方便浏览。

---

## 定时部署

### 方案一：GitHub Actions（推荐）

1. 将项目推送至 GitHub 仓库
2. 在仓库 `Settings → Secrets and variables → Actions` 中添加以下 Secrets：

| Secret | 说明 |
|--------|------|
| `LOCATION` | 经纬度，如 `116.3176,39.9760` |
| `CAIYUN_TOKEN` | 彩云 API Token |
| `GAODE_KEY` | 高德地图 Key |
| `EMAIL_SENDER` | 发件人邮箱 |
| `EMAIL_AUTH_CODE` | 邮箱授权码 |
| `EMAIL_RECEIVERS` | 收件人（支持多人，逗号分隔） |

3. **定时任务**自动运行：
   - 早间推送：每天北京时间 07:00（推送今日天气）
   - 傍晚推送：每天北京时间 22:00（推送明日天气）

   > workflow 中的 cron 触发器默认注释，需手动取消注释启用。脚本在运行时按北京时间自动选择 morning / evening 模式。

4. **手动触发**：在 Actions 页面点击 `Run workflow`，自动根据北京时间选择模式

---

### 方案二：腾讯云函数

1. 将 `tencent_cloud_function.py` 部署到腾讯云函数
2. 在云函数环境变量中配置：
   - `GITHUB_TOKEN`: GitHub PAT（需 workflow scope）
   - `GITHUB_USER`: GitHub 用户名
   - `REPO_NAME`: 仓库名称

3. 配置两个定时触发器：

| 触发器 | cron 表达式 | 说明 |
|-------|------------|------|
| 早间 | `0 7 * * *` | 北京时间 07:00 |
| 晚间 | `0 22 * * *` | 北京时间 22:00 |

---

## 邮件效果

### 早间模式
- Hero 卡片：今日温度区间 + 天气 + 湿度 + 日出日落 + 实况温度
- 天气关键点：优先使用 API 的 hourly_description
- 三时段卡片：上午/下午/晚间（温度区间、降水概率、风力、湿度）
- 空气质量：实况 AQI、PM2.5、PM10、O₃
- 生活指数：紫外线、穿衣、舒适度、感冒风险、洗车
- 着装建议：根据温度和温差生成
- 实况次要信息：能见度、气压、云量、降水强度

### 晚间模式
- Hero 卡片：明日温度区间 + 天气 + 湿度 + 日出日落
- 天气关键点：明日降水/温度/风力预警
- 三时段卡片：明天上午/下午/晚间
- 预计空气质量：明日 AQI 和 PM2.5
- 生活指数 + 着装建议

### 自适应配色
邮件配色根据天气语义自动切换，每种天气都有专属主题色：
- ☀️ 晴天 → 天蓝系
- ⛅ 多云/阴 → 浅灰系
- 🌧️ 雨天 → 冷灰蓝系
- ❄️ 雪天 → 冰白淡蓝系
- 🌫️ 雾/霾 → 暖灰系
- 💨 大风 → 青灰系
- ⛈️ 雷暴 → 深紫灰系
- 🔥 高温 → 橙红系

---

## 自定义

### 调整穿衣建议阈值

在 `email_generator.py` 的 `_clothing_advice()` 函数中修改温度区间。

### 修改 SMTP 服务商

通过环境变量覆盖 `SMTP_SERVER` 和 `SMTP_PORT`，或修改 `config.py` 默认值。

常用 SMTP 配置参考：

| 服务商 | SMTP_SERVER | SMTP_PORT |
|--------|------------|-----------|
| 腾讯企业邮箱 | smtp.exmail.qq.com | 587 |
| QQ 邮箱 | smtp.qq.com | 587 |
| 163 邮箱 | smtp.163.com | 465 |
| Gmail | smtp.gmail.com | 587 |

### 修改发件人名称

设置环境变量 `SENDER_NAME` 或修改 `config.py` 中的默认值。

---

## 故障排查

| 问题 | 可能原因 | 解决方法 |
|-----|---------|---------|
| `请求超时` | 网络连接问题 | 检查服务器网络或增加超时时间 |
| `彩云API错误` | CAIYUN_TOKEN 无效或超额 | 检查 token 或申请新 token |
| `SMTP 认证失败` | 授权码错误或过期 | 重新生成邮箱授权码 |
| `触发失败：403` | PAT 权限不足 | 确认 PAT 勾选了 `workflow` scope |
| Action 报错 | Secrets 未配置 | 确认 GitHub Secrets 已全部添加 |
| 天气数据为空 | LOCATION 格式错误 | 检查是否为 `经度,纬度` 格式 |

---

## 安全说明

- 所有 API 密钥、Token、授权码、邮箱、**位置信息**均通过环境变量读取
- `config.py` 不包含任何敏感数据，可直接提交到 Git
- `.gitignore` 已配置忽略 `.env` 和生成的 HTML 文件
- SMTP 连接使用 TLS 加密
