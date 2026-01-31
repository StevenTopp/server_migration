# ====== 可改参数 ======
$FRP_VER     = "0.56.0"
$SERVER_ADDR = "YOUR_SERVER_IP"      # 改成你的云服务器公网IP
$SERVER_PORT = "7000"
$TOKEN       = "myStrongToken123"    # 和云服务器 frps.ini 保持一致

$LOCAL_IP    = "127.0.0.1"
$LOCAL_PORT  = "9000"

$REMOTE_IP   = "127.0.0.1"
$REMOTE_PORT = "19000"
# ======================

$BaseDir = "D:\Code\server\package"
$FrpDir  = Join-Path $BaseDir "frp"
New-Item -ItemType Directory -Force -Path $FrpDir | Out-Null

# 检测架构：x64 / arm64
$arch = (Get-CimInstance Win32_OperatingSystem).OSArchitecture
if ($arch -match "64") {
  # 绝大多数 Windows 是 x64
  $FRP_ARCH = "amd64"
} else {
  throw "不支持的系统架构：$arch"
}

$zipName = "frp_${FRP_VER}_windows_${FRP_ARCH}.zip"
$url = "https://github.com/fatedier/frp/releases/download/v$FRP_VER/$zipName"
$zipPath = Join-Path $BaseDir $zipName

Write-Host "`n==> 下载 FRP: $url`n"
Invoke-WebRequest -Uri $url -OutFile $zipPath

Write-Host "`n==> 解压到: $BaseDir`n"
Expand-Archive -Path $zipPath -DestinationPath $BaseDir -Force

# FRP 解压出来是 frp_0.xx_windows_amd64 这种目录
$extracted = Join-Path $BaseDir ("frp_{0}_windows_{1}" -f $FRP_VER, $FRP_ARCH)

# 清理旧目录并移动到 C:\package\frp
if (Test-Path $FrpDir) { Remove-Item -Recurse -Force $FrpDir }
Move-Item -Force $extracted $FrpDir

# 写 frpc.ini
$iniPath = Join-Path $FrpDir "frpc.ini"
@"
[common]
server_addr = $SERVER_ADDR
server_port = $SERVER_PORT
token = $TOKEN

[local_api]
type = tcp
local_ip = $LOCAL_IP
local_port = $LOCAL_PORT

# 映射到云服务器本机端口（不会暴露公网）
remote_ip = $REMOTE_IP
remote_port = $REMOTE_PORT
"@ | Out-File -FilePath $iniPath -Encoding ascii

Write-Host "`n✅ frpc 已安装完成`n目录：$FrpDir`n配置：$iniPath`n"
Write-Host "启动命令（前台运行）："
Write-Host "`"$FrpDir\frpc.exe`" -c `"$iniPath`""
Write-Host "`n启动后去云服务器测试：curl http://127.0.0.1:$REMOTE_PORT/v1/models`n"
