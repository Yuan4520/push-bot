# 可复用项目与选型

## 推荐组合

### 1. 微信推送：Server酱 / PushPlus

当前项目已经支持：

- Server酱：`.env` 填 `SERVERCHAN_SENDKEY`
- PushPlus：`.env` 填 `PUSHPLUS_TOKEN`

低频个人提醒优先用 Server酱。后续如果要多渠道或更高频率，可以切到 PushPlus。

### 2. 新闻：60s 看世界接口

当前项目已经接入 `60s.viki.moe` 作为新闻兜底源，比普通 RSS 更适合每天推一条微信简报。

### 3. 机票：ticket-price-sentinel

推荐直接使用现成项目：

https://github.com/tangtaizong666/ticket-price-sentinel

原因：

- 面向 Windows 普通用户
- 支持携程登录
- 支持国内单程机票
- 支持目标价监控
- 提供 bat 一键启动
- 使用 Playwright 模拟浏览器访问携程
- 比自己写携程爬虫更省维护

当前项目不直接爬携程，避免重复造轮子和平台风控问题。

它的官方说明里写明了普通用户路径：下载源码或 Release 后双击启动脚本，首次运行会安装依赖和 Playwright Chromium；启动后在本地页面登录携程、快速搜索、设置目标价和检查间隔。默认数据存在本机 `data/`，不会上传到作者服务器。

当前项目可以和它分工：

- `ticket-price-sentinel`：负责实时查价和命中记录。
- 本项目：负责微信推送天气、新闻、关注路线。
- 后续改造：把 `ticket-price-sentinel` 的命中通知改成调用本项目的 Server酱/PushPlus 发送函数。

常用城市/机场代码：

- 广州：`can`
- 深圳：`szx`
- 珠海：`zuh`
- 兰州：`lhw`
- 西宁：`xnn`

要创建的监控任务：

- `can -> lhw`，2026-09-30，1100 元
- `can -> xnn`，2026-09-30，1300 元
- `szx -> lhw`，2026-09-30，1100 元
- `szx -> xnn`，2026-09-30，1300 元
- `zuh -> lhw`，2026-09-30，1100 元
- `zuh -> xnn`，2026-09-30，1300 元
- `can -> lhw`，2026-10-01，1100 元
- `can -> xnn`，2026-10-01，1300 元
- `szx -> lhw`，2026-10-01，1100 元
- `szx -> xnn`，2026-10-01，1300 元
- `zuh -> lhw`，2026-10-01，1100 元
- `zuh -> xnn`，2026-10-01，1300 元

### 4. 机票数据采集：Ctrip-Crawler

https://github.com/Suysker/Ctrip-Crawler

这是一个基于 Selenium / SeleniumWire 的携程机票爬虫，功能更重，偏数据采集和批量分析。它会处理浏览器模拟、Cookie 缓存、验证码人工干预、响应解析和 CSV 输出。

不作为首选的原因：

- 配置更复杂
- 更像爬虫项目，不是普通用户监控提醒工具
- 需要自己改造成目标价提醒和微信推送

如果 `ticket-price-sentinel` 满足不了，再考虑参考它的 Selenium 实现。

## 不优先使用的项目

### flightAlert

https://github.com/omegatao/flightAlert

这是较早的携程 API + Server酱方案，思路有参考价值，但依赖旧版 Server酱和旧携程接口，稳定性不如近期维护的 Windows 工具。

### 大型 Selenium 携程爬虫

这类项目功能强，但依赖浏览器自动化、Cookie、验证码和反爬处理，维护成本高，不适合作为最低成本个人提醒方案。
