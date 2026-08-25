$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$JiPiaoRoot = Join-Path $Root "references\JiPiao-master"
$Python = Join-Path $Root "references\ticket-price-sentinel-main\.venv\Scripts\python.exe"

Start-Process `
  -FilePath $Python `
  -ArgumentList "main.py" `
  -WorkingDirectory $JiPiaoRoot `
  -WindowStyle Hidden

Write-Host "JiPiao 飞猪机票监控已后台启动。"
Write-Host "配置文件：$JiPiaoRoot\config.yaml"
Write-Host "日志文件：$JiPiaoRoot\logs\monitor.log"

