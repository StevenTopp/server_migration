import json
import datetime
from pathlib import Path
from app.core.config import (
    USERS_FILE, PROMPT_DATA_ROOT, CONFIG_ROOT, DATA_ROOT,
    DEFAULT_API_CONFIG, DEFAULT_PROMPTS
)

def get_users_db():
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding='utf-8'))
    except:
        return {}

def save_users_db(db):
    USERS_FILE.write_text(json.dumps(db, indent=2), encoding='utf-8')

def get_user_group(username: str) -> str:
    users = get_users_db()
    user_data = users.get(username)
    if not user_data:
        return "default"
    return user_data.get("group", "default")

def update_user_group(username: str, group_name: str):
    users = get_users_db()
    if username not in users:
        raise ValueError("User not found")

    users[username]["group"] = group_name
    save_users_db(users)

def get_user_prompts(username: str):
    prompt_path = PROMPT_DATA_ROOT / f"{username}.json"
    prompts = DEFAULT_PROMPTS.copy()

    if prompt_path.exists():
        try:
            saved_prompts = json.loads(prompt_path.read_text(encoding='utf-8'))

            # 兼容性迁移逻辑
            if "hidden_freecreate_prompt" in saved_prompts:
                if saved_prompts["hidden_freecreate_prompt"]:
                    saved_prompts["pre_hidden_freecreate_prompt"] = saved_prompts["hidden_freecreate_prompt"]
                del saved_prompts["hidden_freecreate_prompt"]

            # 修复空值覆盖默认值问题
            if "pre_hidden_freecreate_prompt" in saved_prompts and not saved_prompts["pre_hidden_freecreate_prompt"]:
                del saved_prompts["pre_hidden_freecreate_prompt"]
            if "post_hidden_freecreate_prompt" in saved_prompts and not saved_prompts["post_hidden_freecreate_prompt"]:
                del saved_prompts["post_hidden_freecreate_prompt"]

            prompts.update(saved_prompts)
        except: pass
    return prompts

def save_user_prompts(username: str, prompts: dict):
    prompt_path = PROMPT_DATA_ROOT / f"{username}.json"
    prompt_path.write_text(json.dumps(prompts, indent=2), encoding='utf-8')

def save_base_config_only(username: str, full_config: dict):
    base_keys = ["base_url", "api_key", "model", "file_path"]
    base_config = {k: full_config.get(k) for k in base_keys}
    config_path = CONFIG_ROOT / f"{username}.json"
    config_path.write_text(json.dumps(base_config, indent=2), encoding='utf-8')

def get_user_config(username: str):
    config_path = CONFIG_ROOT / f"{username}.json"

    config = DEFAULT_API_CONFIG.copy()

    if config_path.exists():
        try:
            saved_config = json.loads(config_path.read_text(encoding='utf-8'))
            # 过滤旧字段
            if "system_prompt_prefix" in saved_config: del saved_config["system_prompt_prefix"]
            if "user_prompt" in saved_config: del saved_config["user_prompt"]
            config.update(saved_config)
        except: pass

    # 合并 Prompts
    prompts = get_user_prompts(username)
    full_config = {**config, **prompts}

    # 路径初始化检查
    user_data_dir = DATA_ROOT / username
    user_data_dir.mkdir(exist_ok=True)
    current_path = Path(full_config["file_path"]) if full_config["file_path"] else None

    if not current_path or not str(current_path).startswith(str(user_data_dir)):
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        new_file = user_data_dir / f"{timestamp}.txt"
        full_config["file_path"] = str(new_file)
        save_base_config_only(username, full_config)

    return full_config

def save_user_config_split(username: str, full_config: dict):
    # 1. 保存 Prompt
    prompts = {
        "system_prompt_prefix": full_config.get("system_prompt_prefix"),
        "user_prompt": full_config.get("user_prompt"),
        "free_create_mode": full_config.get("free_create_mode"),
        "freecreate_prompt": full_config.get("freecreate_prompt"),
        "pre_hidden_freecreate_prompt": full_config.get("pre_hidden_freecreate_prompt"),
        "post_hidden_freecreate_prompt": full_config.get("post_hidden_freecreate_prompt")
    }
    save_user_prompts(username, prompts)

    # 2. 保存基础配置
    save_base_config_only(username, full_config)
