# 微信自定义推送机器人

这是一个低成本的个人微信推送方案：用 Python 拉取天气、新闻和机票价格，再通过 Server 酱推送到微信；用 GitHub Actions 定时运行，这样电脑不用一直开机。

适合这些需求：

- 每天固定时间收到天气和新闻简报。
- 高频监测某段日期的机票价格。
- 只有命中低价条件时才发微信提醒。
- 同一趟航班避免重复提醒，只有再次降价才重新提醒。

## 技术方案

整体分成两条链路：

1. 普通简报链路
   - 配置文件：`config.json`
   - 程序入口：`push_bot.py`
   - 云端定时：`.github/workflows/daily-push.yml`
   - 当前默认：每天北京时间 10:00 推送天气和新闻。

2. 机票监控链路
   - 配置文件：`references/JiPiao-master/config.yaml`
   - 程序入口：`references/JiPiao-master/main.py --once`
   - 云端定时：`.github/workflows/flight-monitor.yml`
   - 当前默认：约每 30 分钟查一次票价，只有命中低价才推送。

推送渠道默认使用 Server 酱。Server 酱的好处是接入简单，只需要一个 `SERVERCHAN_SENDKEY`，个人低频使用成本最低。

## 当前示例规则

当前机票监控规则是：

- 航线：西宁 `XNN` -> 深圳 `SZX`
- 日期：`2026-09-20` 到 `2026-09-30`
- 价格：低于或等于 `600` 元才通知
- 限制：出发和到达必须是同一天
- 去重：同一天同一趟航班只通知一次，除非之后查到更低价格

## 准备工作

需要：

- 一个 GitHub 账号
- 一个 Server 酱账号
- Python 3.12 或较新版本
- 一个 GitHub 仓库

Server 酱地址：

https://sct.ftqq.com/

登录 Server 酱后，绑定微信，复制自己的 `SendKey`。

## 本地安装

进入项目目录：

```powershell
cd "C:\Users\YTY\Documents\ChatGPT\推送机器人"
```

安装普通简报依赖：

```powershell
python -m pip install -r requirements.txt
```

安装机票监控依赖：

```powershell
python -m pip install -r references\JiPiao-master\requirements.txt
```

## 配置普通简报

普通简报配置在 `config.json`。

示例：

```json
{
  "title": "今日个人简报",
  "brief_only": true,
  "weather": {
    "enabled": true,
    "cities": [
      {
        "name": "深圳市坪山区",
        "query": "Pingshan,Shenzhen"
      },
      {
        "name": "广州市越秀区",
        "query": "Yuexiu,Guangzhou"
      }
    ]
  },
  "news": {
    "enabled": true,
    "daily_60s_enabled": true,
    "max_items": 8,
    "keywords": [],
    "feeds": [
      "https://www.thepaper.cn/rss_news.jsp",
      "https://www.zaobao.com.sg/realtime/rss.xml",
      "https://rsshub.app/36kr/newsflashes"
    ]
  },
  "flights": {
    "enabled": false
  }
}
```

常用修改：

- 改标题：修改 `title`
- 改天气地点：修改 `weather.cities`
- 只看关键词新闻：在 `news.keywords` 里填关键词
- 每天简报不带机票：保持 `brief_only: true` 和 `flights.enabled: false`

本地测试普通简报：

```powershell
.\.venv\Scripts\python.exe push_bot.py --config config.json --dry-run
```

真正推送：

```powershell
$env:SERVERCHAN_SENDKEY="你的Server酱SendKey"
.\.venv\Scripts\python.exe push_bot.py --config config.json
```

## 配置机票监控

机票配置在：

```text
references/JiPiao-master/config.yaml
```

示例：

```yaml
routes:
  - from: XNN
    from_name: 西宁
    to: SZX
    to_name: 深圳
    dates:
      - "2026-09-20"
      - "2026-09-21"
      - "2026-09-22"
      - "2026-09-23"
      - "2026-09-24"
      - "2026-09-25"
      - "2026-09-26"
      - "2026-09-27"
      - "2026-09-28"
      - "2026-09-29"
      - "2026-09-30"
    alert_threshold: 600

platforms:
  - fliggy

crawler:
  direct_only: true
  timeout_seconds: 45
  delay_min: 5
  delay_max: 15

output:
  db_path: data/prices.db
  log_path: logs/monitor.log

notifier:
  push_drop_min: 1
  push_rise_min: 50
  serverchan:
    enabled: true
    send_key: ""
    channel: ""
```

字段说明：

- `from` / `to`：机场三字码，例如西宁 `XNN`、深圳 `SZX`、广州 `CAN`
- `dates`：要监控的出发日期
- `alert_threshold`：低于或等于这个价格才通知
- `platforms`：当前推荐 `fliggy`
- `direct_only`：尽量只看直飞或非中转结果
- `push_drop_min: 1`：同一航班再次降价 1 元及以上才再次提醒

本地测试机票监控：

```powershell
cd "C:\Users\YTY\Documents\ChatGPT\推送机器人\references\JiPiao-master"
$env:SERVERCHAN_SENDKEY="你的Server酱SendKey"
..\..\.venv\Scripts\python.exe main.py --once
```

如果没有低于阈值的机票，本地运行成功也不会发微信，这是正常的。

## 去重逻辑

机票通知状态存在 sqlite 数据库：

```text
references/JiPiao-master/data/prices.db
```

程序会按这些信息识别“同一趟航班”：

- 出发城市
- 到达城市
- 出发日期
- 航司
- 航班号
- 出发时间
- 到达时间

同一个航班第一次低于阈值会通知。之后如果价格没有更低，就跳过；如果又降价，就再次通知。

GitHub Actions 每次运行都是新机器，所以 `flight-monitor.yml` 使用 `actions/cache` 保存 `data` 目录，让去重状态能跨运行保留。

## 上传到 GitHub

把项目推到自己的 GitHub 仓库。仓库可以公开，但不要把真实 `config.yaml`、`.env`、数据库、日志提交上去。

推荐 `.gitignore` 排除：

```text
.env
.venv/
data/
references/JiPiao-master/data/
references/JiPiao-master/logs/
references/JiPiao-master/debug/
references/JiPiao-master/user_data/
```

## 配置 GitHub Secrets

打开：

```text
GitHub 仓库 -> Settings -> Secrets and variables -> Actions -> New repository secret
```

添加三个 secret：

```text
SERVERCHAN_SENDKEY=你的Server酱SendKey
BOT_CONFIG_B64=config.json 的 base64
JIPIAO_CONFIG_B64=references/JiPiao-master/config.yaml 的 base64
```

Windows PowerShell 生成 base64：

```powershell
cd "C:\Users\YTY\Documents\ChatGPT\推送机器人"

[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content config.json -Raw)))
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content references\JiPiao-master\config.yaml -Raw)))
```

第一个结果填进 `BOT_CONFIG_B64`，第二个结果填进 `JIPIAO_CONFIG_B64`。

每次改了 `config.json` 或 `config.yaml`，都要重新生成并更新对应 secret，否则 GitHub Actions 仍会用旧配置。

## GitHub Actions 定时

普通简报：

```yaml
name: Daily WeChat Push

on:
  workflow_dispatch:
  schedule:
    - cron: "0 2 * * *"
```

GitHub cron 使用 UTC。`0 2 * * *` 表示 UTC 02:00，也就是北京时间 10:00。

机票监控：

```yaml
name: Flight Price Monitor

on:
  workflow_dispatch:
  schedule:
    - cron: "*/30 * * * *"
```

`*/30 * * * *` 表示大约每 30 分钟运行一次。GitHub Actions 定时可能会延迟几分钟，偶尔也可能漏触发一次。

## 手动运行

进入 GitHub 仓库：

```text
Actions -> 选择 workflow -> Run workflow
```

注意：

- 手动运行 `Daily WeChat Push` 会立即发普通简报。
- 手动运行 `Flight Price Monitor` 只会查机票，命中低价才发微信。
- 如果 Actions 页面显示黄色圆圈，表示正在运行。
- 绿色勾表示成功。
- 红色叉表示失败，需要点进去看失败步骤。

## 自定义示例

改成广州飞北京，9 月 25 到 9 月 30，低于 700 提醒：

```yaml
routes:
  - from: CAN
    from_name: 广州
    to: PEK
    to_name: 北京
    dates:
      - "2026-09-25"
      - "2026-09-26"
      - "2026-09-27"
      - "2026-09-28"
      - "2026-09-29"
      - "2026-09-30"
    alert_threshold: 700
```

每天 8:30 发普通简报：

```yaml
schedule:
  - cron: "30 0 * * *"
```

北京时间换 UTC 的方法：

```text
北京时间 - 8 小时 = GitHub cron 时间
```

## 常见问题

为什么没到时间，手动 run 完也发了？

因为 `workflow_dispatch` 是手动触发，点 `Run workflow` 会立刻运行，不受定时时间限制。

为什么到点没收到？

先看 Actions 有没有生成新 run。如果没有，通常是 GitHub 定时延迟、漏触发，或者配置提交时间晚于当天触发时间。如果有 run，再看它是绿色成功还是红色失败。

为什么机票监控成功但没推送？

这通常是正常的。只有满足价格阈值、同日到达、且没有重复通知时才会推送。

为什么要用 base64 secret？

因为配置文件里可能有私人行程、推送 key 等信息。放进 GitHub Secrets 比直接提交到公开仓库更安全。

为什么不用电脑一直开机？

因为 GitHub Actions 在云端定时跑脚本。只要仓库和 Secrets 配好，本地电脑关机也不影响推送。
