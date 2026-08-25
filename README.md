# 微信个人推送机器人

最低成本方案：本地 Python 定时脚本 + 免费微信推送服务。

推荐先用 Server酱：

- 成本：低频个人使用通常可以免费
- 难度：最低，只需要一个 `SENDKEY`
- 适合：每天早上推送天气、新闻摘要、机票关注提醒

如果以后推送频率更高，可以改用 PushPlus，只需要换环境变量。

## 1. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 2. 配置

复制配置模板：

```powershell
Copy-Item .env.example .env
```

打开 `.env`，至少填写其中一种推送方式：

```text
SERVERCHAN_SENDKEY=你的Server酱SendKey
```

或：

```text
PUSHPLUS_TOKEN=你的PushPlus Token
```

## 3. 修改订阅内容

编辑 `config.example.json`，保存为 `config.json`。

默认包含：

- 多地点天气
- 几个新闻 RSS
- 机票关注说明

当前版本还会自动读取 `references/JiPiao-master/data/prices.db`，把 JiPiao 抓到的飞猪机票价格融入每日简报。

## 机票监控

已经接入 `yangka1212/JiPiao` 的飞猪查价结果。

手动跑一次查价：

```powershell
cd "C:\Users\YTY\Documents\ChatGPT\推送机器人\references\JiPiao-master"
..\ticket-price-sentinel-main\.venv\Scripts\python.exe main.py --once
```

后台启动飞猪定时监控：

```powershell
cd "C:\Users\YTY\Documents\ChatGPT\推送机器人"
.\start_jipiao_fliggy.ps1
```

每日简报会展示：

- 低价命中
- 最值得盯的航线
- 接近目标价的航线
- 暂无价格的航线

## GitHub Actions 云端定时

如果不想让笔记本一直开机，可以把这个目录推到 GitHub 仓库，并启用 `.github/workflows/daily-push.yml`。

需要在仓库设置里添加 Secret：

```text
SERVERCHAN_SENDKEY=你的Server酱SendKey
BOT_CONFIG_B64=你的config.json经过base64后的内容
JIPIAO_CONFIG_B64=你的references/JiPiao-master/config.yaml经过base64后的内容
```

路径：

```text
GitHub 仓库 -> Settings -> Secrets and variables -> Actions -> New repository secret
```

工作流默认每天北京时间 08:10、14:10、20:10 运行，也可以在 GitHub 的 Actions 页面手动点 `Run workflow`。

Windows PowerShell 生成 base64：

```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content config.json -Raw)))
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content references\JiPiao-master\config.yaml -Raw)))
```

## 4. 手动运行一次

```powershell
python push_bot.py --config config.json
```

## 5. 设置每天自动运行

Windows 任务计划程序里新建任务：

- 程序：`python`
- 参数：`push_bot.py --config config.json`
- 起始于：本项目目录

例如每天早上 8:00 运行一次。

## 获取 Server酱 SendKey

访问 Server酱官网，登录后绑定微信，复制 SendKey：

https://sct.ftqq.com/

## 获取 PushPlus Token

访问 PushPlus 官网，登录后复制 Token：

https://www.pushplus.plus/
