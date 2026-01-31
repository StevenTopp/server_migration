$ErrorActionPreference = "Stop"

# ========= 参数（你只需要改 IP 和 token） =========
$FRP_VER     = "0.67.0"
$SERVER_ADDR = "82.157.252.157"
$SERVER_PORT = "7000"
$TOKEN       = "myStrongToken123"

$LOCAL_IP    = "127.0.0.1"
$LOCAL_PORT  = "9000"

$REMOTE_IP   = "127.0.0.1"
$REMOTE_PORT = "19000"

$BaseDir     = "D:\Code\server\package"
# ================================================

Write-Host ""
Write-Host "==> Step 1: 检测架构"

$FRP_ARCH = "amd64"

Write-Host "架构: $FRP_ARCH"

Write-Host ""
Write-Host "==> Step 2: 创建目录"
New-Item -ItemType Directory -Force -Path $BaseDir | Out-Null

Write-Host ""
Write-Host "==> Step 3: 下载 FRP"

$zipName = "frp_${FRP_VER}_windows_${FRP_ARCH}.zip"
$url     = "https://github.com/fatedier/frp/releases/download/v$FRP_VER/$zipName"
$zipPath = Join-Path $BaseDir $zipName

Invoke-WebRequest -Uri $url -OutFile $zipPath

Write-Host ""
Write-Host "==> Step 4: 解压 FRP"

Expand-Archive -Path $zipPath -DestinationPath $BaseDir -Force

$ExtractedDir = Join-Path $BaseDir "frp_${FRP_VER}_windows_${FRP_ARCH}"

Write-Host ""
Write-Host "FRP 解压目录: $ExtractedDir"

Write-Host ""
Write-Host "==> Step 5: 写入 frpc.ini"

$iniPath = Join-Path $ExtractedDir "frpc.ini"

$configLines = @(
"[common]"
"server_addr = $SERVER_ADDR"
"server_port = $SERVER_PORT"
"token = $TOKEN"
""
"[local_api]"
"type = tcp"
"local_ip = $LOCAL_IP"
"local_port = $LOCAL_PORT"
""
"# 映射到云服务器本机端口（不会暴露公网）"
"remote_ip = $REMOTE_IP"
"remote_port = $REMOTE_PORT"
)

$configLines | Set-Content -Path $iniPath -Encoding ASCII

Write-Host ""
Write-Host "✅ 安装完成！"
Write-Host ""
Write-Host "启动命令："
Write-Host "cd `"$ExtractedDir`""
Write-Host ".\frpc.exe -c .\frpc.ini"
Write-Host ""
Write-Host "云服务器测试："
Write-Host "curl http://127.0.0.1:$REMOTE_PORT/v1/models"
Write-Host ""
