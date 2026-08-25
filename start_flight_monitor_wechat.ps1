$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$TicketRoot = Join-Path $Root "references\ticket-price-sentinel-main"

Start-Process `
  -FilePath (Join-Path $TicketRoot ".venv\Scripts\python.exe") `
  -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" `
  -WorkingDirectory $TicketRoot `
  -WindowStyle Hidden

Start-Sleep -Seconds 3

Start-Process `
  -FilePath (Join-Path $Root ".venv\Scripts\python.exe") `
  -ArgumentList "flight_hit_wechat_forwarder.py" `
  -WorkingDirectory $Root `
  -WindowStyle Hidden

Start-Process "http://127.0.0.1:8000"

Write-Host "票价哨兵已启动：http://127.0.0.1:8000"
Write-Host "首次使用请在页面点击登录携程。保持本机开机和程序运行，命中后会转发到微信。"

