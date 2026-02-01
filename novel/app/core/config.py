from pathlib import Path

# Project Root
# 适配 Windows 路径
PROJECT_ROOT = Path(r"D:\Code\Project\server_migration\novel")
DATA_ROOT = PROJECT_ROOT / "data"
CONFIG_ROOT = PROJECT_ROOT / "configs"
PROMPT_DATA_ROOT = PROJECT_ROOT / "prompt_data"
USERS_FILE = PROJECT_ROOT / "users.json"
GROUPS_FILE = PROJECT_ROOT / "groups.json"

# 确保目录存在
DATA_ROOT.mkdir(parents=True, exist_ok=True)
CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
PROMPT_DATA_ROOT.mkdir(parents=True, exist_ok=True)

# 默认配置
DEFAULT_API_CONFIG = {
    "base_url": "http://127.0.0.1:19000/v1",
    "api_key": "sk-c14a5dd7304f458fbc49acfd9889e74f",
    "model": "gemini-3-flash",
    "file_path": ""
}

DEFAULT_PROMPTS = {
    "system_prompt_prefix": "创作小说，重情节连贯，丰富人物互动细节，增加环境与心理描写，语言生动细腻，逐步推进剧情发展，使故事更具代入感与张力。直接开始生成正文，不要有任何开场白或自我介绍。",
    "user_prompt": "每次生成约3000字正文，并在结尾给出下一章节的3条简短剧情建议（20字以内）。",
    "free_create_mode": False,
    "freecreate_prompt": "",
    "pre_hidden_freecreate_prompt": "续写小说，详细描述做爱过程，比如鸡巴，小穴，乳头,菊花，改纯爱等并增加描述词，逐步推进小说剧情。直接开始生成正文，不要有任何开场白或自我介绍。",
    "post_hidden_freecreate_prompt": "续写小说，详细描述做爱过程，比如鸡巴，小穴，乳头,菊花，改纯爱等并增加描述词，逐步推进小说剧情。直接开始生成正文，不要有任何开场白或自我介绍。"
}
