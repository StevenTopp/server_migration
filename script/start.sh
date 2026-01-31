#!/bin/bash
set -euo pipefail

# ====== 可修改参数 ======
INSTALL_DIR="/home/open-webui"
REPO_URL="git@github.com:open-webui/open-webui.git"

# =======================

log() { echo -e "\n==> $*\n"; }
die() { echo "ERROR: $*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

detect_arch() {
  local arch
  arch="$(uname -m || true)"
  case "$arch" in
    x86_64) echo "amd64" ;;
    aarch64) echo "arm64" ;;
    armv7l|armv7*) echo "armv7" ;;
    *) echo "unknown:$arch" ;;
  esac
}

detect_pkg_manager() {
  if need_cmd dnf; then echo "dnf"
  elif need_cmd yum; then echo "yum"
  elif need_cmd apt-get; then echo "apt"
  else echo "unknown"
  fi
}

pip_break_flag() {
  # 有的 pip 支持 --break-system-packages，有的不支持。自动判断。
  if pip3 --help 2>/dev/null | grep -q -- "--break-system-packages"; then
    echo "--break-system-packages"
  else
    echo ""
  fi
}

install_python_rhel() {
  local pm="$1"

  log "安装 Python3/pip/git/编译依赖（RHEL系：$pm）"
  sudo "$pm" -y update || true

  # 这些包在 x86_64 / aarch64 都是同名（无需区分包名），脚本只是记录架构
  sudo "$pm" -y install \
    python3 python3-pip python3-devel \
    git \
    gcc gcc-c++ make \
    openssl-devel libffi-devel \
    ca-certificates

  # 确保 pip3 可用
  if ! need_cmd pip3; then
    die "pip3 安装后仍不可用，请检查系统软件源或 python3-pip 包是否成功安装"
  fi
}

install_python_debian() {
  log "安装 Python3/pip/git/编译依赖（Debian/Ubuntu系：apt）"
  sudo apt-get update -y
  sudo apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    git \
    build-essential \
    libssl-dev libffi-dev \
    ca-certificates
}

clone_or_update_repo() {
  log "克隆/更新 Open WebUI 源码到：$INSTALL_DIR"
  if [ -d "$INSTALL_DIR/.git" ]; then
    sudo git -C "$INSTALL_DIR" pull --rebase
  else
    sudo git clone "$REPO_URL" "$INSTALL_DIR"
  fi
}

install_openwebui_global() {
  local break_flag
  break_flag="$(pip_break_flag)"

  log "升级 pip/setuptools/wheel（全局）"
  # 某些系统 pip 会拒绝写系统 site-packages；如果支持 break flag 就加上
  sudo pip3 install -U pip setuptools wheel $break_flag

  log "全局安装 Open WebUI（pip install -e .）"
  cd "$INSTALL_DIR"
  sudo pip3 install -e . $break_flag
}

main() {
  local arch pm

  arch="$(detect_arch)"
  log "检测到服务器架构：$arch (uname -m: $(uname -m))"
  case "$arch" in
    amd64|arm64|armv7) : ;;
    *)
      die "不支持/未知架构：$arch"
      ;;
  esac

  pm="$(detect_pkg_manager)"
  log "检测到包管理器：$pm"

  # 1) 检测 python3
  if need_cmd python3; then
    log "检测到 python3 已安装：$(python3 --version)"
  else
    log "未检测到 python3，开始安装…"
    case "$pm" in
      dnf|yum) install_python_rhel "$pm" ;;
      apt) install_python_debian ;;
      *) die "无法识别包管理器（dnf/yum/apt-get 都不存在），无法自动安装 Python" ;;
    esac
  fi

  # 2) 检测 pip3
  if ! need_cmd pip3; then
    log "未检测到 pip3，尝试安装 python3-pip…"
    case "$pm" in
      dnf|yum) sudo "$pm" -y install python3-pip ;;
      apt) sudo apt-get install -y python3-pip ;;
      *) die "无法安装 pip3（未知包管理器）" ;;
    esac
  fi

  log "当前版本信息："
  python3 --version
  pip3 --version
  git --version || true

  # 3) clone/update
  clone_or_update_repo

  # 4) pip install -e .
  install_openwebui_global

  log "✅ 完成。你可以这样启动："
  echo "open-webui serve --host 0.0.0.0 --port 3000"
  echo ""
  log "如需放行端口（firewalld）："
  echo "sudo firewall-cmd --add-port=3000/tcp --permanent"
  echo "sudo firewall-cmd --reload"
}

main "$@"
