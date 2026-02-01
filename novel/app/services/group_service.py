import json
from typing import List, Optional
from app.core.config import GROUPS_FILE
from app.models.schemas import Group, GroupCreate

# 默认组配置
DEFAULT_GROUPS = {
    "default": {
        "name": "default",
        "description": "默认用户组",
        "allow_free_mode": False
    },
    "vip": {
        "name": "vip",
        "description": "VIP用户组",
        "allow_free_mode": True
    },
    "admin": {
        "name": "admin",
        "description": "管理员组",
        "allow_free_mode": True
    }
}

def get_groups_db() -> dict:
    if not GROUPS_FILE.exists():
        # 初始化默认组
        save_groups_db(DEFAULT_GROUPS)
        return DEFAULT_GROUPS
    try:
        return json.loads(GROUPS_FILE.read_text(encoding='utf-8'))
    except:
        return {}

def save_groups_db(db: dict):
    GROUPS_FILE.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding='utf-8')

def get_group(group_name: str) -> Optional[dict]:
    groups = get_groups_db()
    return groups.get(group_name)

def create_group(group: GroupCreate) -> dict:
    groups = get_groups_db()
    if group.name in groups:
        raise ValueError(f"Group {group.name} already exists")

    group_data = group.dict()
    groups[group.name] = group_data
    save_groups_db(groups)
    return group_data

def list_groups() -> List[dict]:
    groups = get_groups_db()
    return list(groups.values())

def can_use_free_mode(group_name: str) -> bool:
    group = get_group(group_name)
    if not group:
        # 如果组不存在，默认不允许 (安全起见)
        # 也可以 fallback 到 default 组
        default_group = get_group("default")
        return default_group.get("allow_free_mode", False) if default_group else False

    return group.get("allow_free_mode", False)
