import json
import datetime
from pathlib import Path
from app.core.config import DATA_ROOT
from app.services.user_manager import get_user_config, save_base_config_only

def list_user_sessions(username: str):
    user_data_dir = DATA_ROOT / username
    if not user_data_dir.exists():
        return []

    sessions = []
    # 遍历所有 txt 文件
    for file in user_data_dir.glob("*.txt"):
        try:
            stat = file.stat()
            # 获取对应的 json 历史，尝试读取最后一条互动时间，或者文件修改时间
            json_path = file.with_suffix(".json")
            last_msg = ""
            if json_path.exists():
                try:
                    history = json.loads(json_path.read_text(encoding="utf-8"))
                    if history:
                        last_msg = history[-1].get("content", "")[:50] + "..."
                except: pass

            sessions.append({
                "filename": file.name,
                "path": str(file),
                "updated_at": stat.st_mtime,
                "preview": last_msg or "(无历史记录)",
                "size": stat.st_size
            })
        except Exception as e:
            print(f"Error reading session {file}: {e}")

    # 按时间倒序排序
    sessions.sort(key=lambda x: x["updated_at"], reverse=True)
    return sessions

def get_session_history(username: str):
    config = get_user_config(username)
    path = Path(config["file_path"])
    json_path = path.with_suffix(".json")

    if not json_path.exists():
        return []

    try:
        history = json.loads(json_path.read_text(encoding="utf-8"))
        return history
    except Exception as e:
        print(f"Error reading history {json_path}: {e}")
        return []

def switch_user_session(username: str, filename: str):
    user_data_dir = DATA_ROOT / username
    target_path = user_data_dir / filename

    if not target_path.exists():
        raise FileNotFoundError("Session file not found")

    # 更新用户配置指向该文件
    config = get_user_config(username)
    config["file_path"] = str(target_path)
    save_base_config_only(username, config)

    return str(target_path)

def create_new_session(username: str):
    config = get_user_config(username)

    # 1. 生成新文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    user_data_dir = DATA_ROOT / username
    user_data_dir.mkdir(parents=True, exist_ok=True)

    new_txt_path = user_data_dir / f"{timestamp}.txt"
    new_json_path = user_data_dir / f"{timestamp}.json"

    # 2. 创建空文件
    new_txt_path.touch()
    new_json_path.write_text("[]", encoding="utf-8")

    # 3. 切换上下文
    config["file_path"] = str(new_txt_path)
    save_base_config_only(username, config)

    return {"filename": new_txt_path.name, "path": str(new_txt_path)}

def switch_file_path(username: str, target_path: str):
    config = get_user_config(username)
    user_data_dir = DATA_ROOT / username

    # 安全检查
    safe_path = Path(target_path)
    # 简单防范 (允许绝对路径匹配，但需在一定范围内，或由调用者保证)
    # 这里的逻辑参考原 server.py
    # if ".." in str(safe_path) or not str(safe_path).startswith(str(user_data_dir)):
    #      pass

    config["file_path"] = str(safe_path)
    save_base_config_only(username, config)
    return str(safe_path)
