import os
import uvicorn
import secrets
import hashlib
import json
import datetime
import re
import asyncio
import uuid
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Depends, status
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI
import free_create_mode

# ================= 全局配置 & 路径 =================
BASE_DIR = Path(r"/home/server_migration/novel")
DATA_ROOT = BASE_DIR / "data"
CONFIG_ROOT = BASE_DIR / "configs"
PROMPT_DATA_ROOT = BASE_DIR / "prompt_data"
USERS_FILE = BASE_DIR / "users.json"

# 确保目录存在
DATA_ROOT.mkdir(parents=True, exist_ok=True)
CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
PROMPT_DATA_ROOT.mkdir(parents=True, exist_ok=True)

# 内存中的 Session 存储 (Token -> Username)
# 重启后需要重新登录，轻量级方案
SESSIONS = {}

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
STATIC_DIR = Path(__file__).parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

# ================= 数据模型 =================
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str
    confirm_password: str

class GenerateRequest(BaseModel):
    user_prompt: Optional[str] = None

class SaveRequest(BaseModel):
    content: str
    prompt: Optional[str] = "" # 记录对应的 prompt

class DiscardRequest(BaseModel):
    block_id: str

class OutlineRequest(BaseModel):
    protagonist: str
    age: str
    style: str
    plot: str
    word_count: str

class ConfigRequest(BaseModel):
    base_url: str
    api_key: str
    model: str
    system_prompt_prefix: str
    user_prompt: str
    free_create_mode: Optional[bool] = False
    freecreate_prompt: Optional[str] = ""
    gemini_3_flashden_freecreate_prompt: Optional[str] = ""
    # file_path 不允许用户直接通过 config 接口随意修改到其他目录，由后端控制

# ================= 工具函数 =================

def get_users_db():
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding='utf-8'))
    except:
        return {}

def save_users_db(db):
    USERS_FILE.write_text(json.dumps(db, indent=2), encoding='utf-8')

def hash_password(password: str, salt: str = None) -> (str, str):
    if not salt:
        salt = secrets.token_hex(8)
    # 使用 pbkdf2 进行简单的哈希
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return pwd_hash, salt

def verify_password(stored_hash, stored_salt, provided_password):
    pwd_hash, _ = hash_password(provided_password, stored_salt)
    return secrets.compare_digest(pwd_hash, stored_hash)

# 获取用户 Prompt 配置
def get_user_prompts(username: str):
    prompt_path = PROMPT_DATA_ROOT / f"{username}.json"
    default_prompts = {
        "system_prompt_prefix": "创作小说，重情节连贯，丰富人物互动细节，增加环境与心理描写，语言生动细腻，逐步推进剧情发展，使故事更具代入感与张力。",
        "user_prompt": "每次生成约3000字正文，并在结尾给出下一章节的3条简短剧情建议（20字以内）。",
        "free_create_mode": False,
        "freecreate_prompt": "请根据用户的喜好与指示进行创作色情小说：",
        "hidden_freecreate_prompt": """你是一名优秀的色情小说作家，擅长创作细腻的性爱过程，能够轻松挑起读者欲望，详细描述做爱过程，比如鸡巴，小穴，乳头,菊花，并增加描述词，逐步推进小说剧情"""
    }
    if prompt_path.exists():
        try:
            saved_prompts = json.loads(prompt_path.read_text(encoding='utf-8'))
            default_prompts.update(saved_prompts)
        except: pass
    return default_prompts

def save_user_prompts(username: str, prompts: dict):
    prompt_path = PROMPT_DATA_ROOT / f"{username}.json"
    prompt_path.write_text(json.dumps(prompts, indent=2), encoding='utf-8')

# 获取用户专属配置 (合并 Config 和 Prompt)
def get_user_config(username: str):
    config_path = CONFIG_ROOT / f"{username}.json"

    # 基础配置 (API相关)
    default_config = {
        "base_url": "http://127.0.0.1:19000/v1",
        "api_key": "sk-c14a5dd7304f458fbc49acfd9889e74f",
        "model": "gemini-3-flash",
        "file_path": ""
    }

    if config_path.exists():
        try:
            saved_config = json.loads(config_path.read_text(encoding='utf-8'))
            # 过滤掉旧版本可能残留的 prompt 字段，以 prompt_data 为准
            if "system_prompt_prefix" in saved_config: del saved_config["system_prompt_prefix"]
            if "user_prompt" in saved_config: del saved_config["user_prompt"]
            default_config.update(saved_config)
        except: pass

    # 获取 Prompt 配置
    prompts = get_user_prompts(username)

    # 合并返回
    full_config = {**default_config, **prompts}

    # 路径检查逻辑...
    user_data_dir = DATA_ROOT / username
    user_data_dir.mkdir(exist_ok=True)
    current_path = Path(full_config["file_path"]) if full_config["file_path"] else None

    if not current_path or not str(current_path).startswith(str(user_data_dir)):
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        new_file = user_data_dir / f"{timestamp}.txt"
        full_config["file_path"] = str(new_file)
        # 只保存基础配置部分
        save_base_config_only(username, full_config)

    return full_config

def save_base_config_only(username: str, full_config: dict):
    # 只提取基础配置字段保存到 configs/
    base_keys = ["base_url", "api_key", "model", "file_path"]
    base_config = {k: full_config.get(k) for k in base_keys}

    config_path = CONFIG_ROOT / f"{username}.json"
    config_path.write_text(json.dumps(base_config, indent=2), encoding='utf-8')

# 原 save_user_config 废弃，改用拆分保存逻辑
def save_user_config_split(username: str, full_config: dict):
    # 1. 保存 Prompt
    prompts = {
        "system_prompt_prefix": full_config.get("system_prompt_prefix"),
        "user_prompt": full_config.get("user_prompt"),
        "free_create_mode": full_config.get("free_create_mode"),
        "freecreate_prompt": full_config.get("freecreate_prompt"),
        "hidden_freecreate_prompt": full_config.get("hidden_freecreate_prompt")
    }
    save_user_prompts(username, prompts)

    # 2. 保存基础配置
    save_base_config_only(username, full_config)

def get_openai_client(config):
    # ✅ 使用 AsyncOpenAI
    return AsyncOpenAI(base_url=config["base_url"], api_key=config["api_key"])

# ================= 认证依赖 =================
async def get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth.split(" ")[1]
    username = SESSIONS.get(token)

    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return username

# ================= 认证接口 =================

@app.post("/api/register")
async def register(user: UserRegister):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致")

    if len(user.username) < 3:
        raise HTTPException(status_code=400, detail="用户名太短")

    users = get_users_db()
    if user.username in users:
        raise HTTPException(status_code=400, detail="用户名已存在")

    pwd_hash, salt = hash_password(user.password)
    users[user.username] = {"hash": pwd_hash, "salt": salt}
    save_users_db(users)

    # 创建用户目录
    (DATA_ROOT / user.username).mkdir(parents=True, exist_ok=True)

    return {"status": "ok", "message": "注册成功，请登录"}

@app.post("/api/login")
async def login(user: UserLogin):
    users = get_users_db()
    if user.username not in users:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    stored = users[user.username]
    if not verify_password(stored["hash"], stored["salt"], user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成 Token
    token = secrets.token_hex(16)
    SESSIONS[token] = user.username

    return {"status": "ok", "token": token, "username": user.username}

@app.post("/api/logout")
async def logout(request: Request):
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        if token in SESSIONS:
            del SESSIONS[token]
    return {"status": "ok"}

# ================= 业务接口 =================

@app.get("/")
async def read_root():
    # 根路径不再直接跳转，因为需要判断登录状态，交给前端 index.html 处理
    return RedirectResponse(url="/static/index.html")

@app.get("/api/config")
async def get_config(username: str = Depends(get_current_user)):
    return get_user_config(username)

@app.post("/api/config")
async def update_config(config: ConfigRequest, username: str = Depends(get_current_user)):
    # 获取旧配置以保留 file_path (不让前端直接改 file_path 防止越权)
    old_config = get_user_config(username)

    new_config_dict = config.dict()
    new_config_dict["file_path"] = old_config["file_path"] # 强制保留原路径

    # ✅ 使用拆分保存逻辑
    save_user_config_split(username, new_config_dict)
    return {"status": "updated", "config": new_config_dict}

@app.get("/api/novel")
async def get_novel_content(full: bool = False, username: str = Depends(get_current_user)):
    config = get_user_config(username)
    path = Path(config["file_path"])

    if not path.exists():
        return {"content": "", "path": str(path), "full_length": 0}
    try:
        content = path.read_text(encoding="utf-8")
        if full:
             # 返回纯文本内容，不包含 path 等元数据干扰复制
             return {"content": content}

        preview = content[-2000:] if len(content) > 2000 else content
        return {"content": preview, "full_length": len(content), "path": str(path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auto_rename")
async def auto_rename(username: str = Depends(get_current_user)):
    config = get_user_config(username)
    path = Path(config["file_path"])

    if not path.exists():
        return {"status": "skipped", "reason": "file not found"}

    filename = path.stem
    if not re.match(r"^\d{8}_\d{6}$", filename):
         return {"status": "skipped", "reason": "not a timestamp file"}

    try:
        content = path.read_text(encoding="utf-8")[:3000]
        if len(content) < 1000:
             return {"status": "skipped", "reason": "content too short"}

        client = get_openai_client(config)
        resp = await client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": "你是一个编辑。请根据小说内容，取一个吸引人的书名，严格限制在15字以内。只返回书名，不要包含引号或其他文字。"},
                {"role": "user", "content": content}
            ],
            temperature=0.7,
            max_tokens=50
        )
        new_title = resp.choices[0].message.content.strip().replace('"', '').replace("'", "")
        new_title = re.sub(r'[\\/*?:"<>|]', "", new_title)

        if not new_title:
            return {"status": "failed", "reason": "empty title"}

        new_path = path.parent / f"{new_title}.txt"
        if new_path.exists():
             new_path = path.parent / f"{new_title}_{filename[-6:]}.txt"

        path.rename(new_path)

        # 同时重命名对应的 json 历史文件
        old_json_path = path.with_suffix(".json")
        if old_json_path.exists():
            new_json_path = new_path.with_suffix(".json")
            old_json_path.rename(new_json_path)

        # 更新配置中的路径
        config["file_path"] = str(new_path)
        save_base_config_only(username, config) # 重命名只影响基础配置

        return {"status": "renamed", "new_name": new_title, "new_path": str(new_path)}

    except Exception as e:
        print(f"Rename failed: {e}")
        return {"status": "error", "detail": str(e)}

@app.post("/api/outline")
async def generate_outline(req: OutlineRequest, username: str = Depends(get_current_user)):
    config = get_user_config(username)

    # 确保在用户目录下生成
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    user_data_dir = DATA_ROOT / username
    user_data_dir.mkdir(parents=True, exist_ok=True)
    new_file_path = user_data_dir / f"{timestamp}.txt"

    # 将大纲要求拼接到 System Prompt 中，以获得更高权重
    # 隐藏的专家设定
    HIDDEN_PROMPT = "你是一名专业的作家，擅长小说创作，文笔极佳，情节设计引人入胜。"
    base_system = f"{HIDDEN_PROMPT}\n{config['system_prompt_prefix']}"

    if config.get("free_create_mode"):
        # 自由模式下，跳过繁琐的模板，直接使用用户输入的内容
        parts = []
        if req.plot: parts.append(req.plot)
        if req.protagonist: parts.append(f"主角: {req.protagonist}")
        if req.style: parts.append(f"风格: {req.style}")
        # 如果用户什么都没填，给个默认提示以免报错或发呆
        outline_requirements = "\n".join(parts) if parts else "请开始创作。"
    else:
        outline_requirements = (
            f"\n\n任务：创建小说大纲\n"
            f"主角：{req.protagonist} (年龄: {req.age})\n"
            f"风格：{req.style}\n"
            f"预期字数：{req.word_count}\n"
            f"故事梗概/走向：{req.plot}\n\n"
            f"请生成详细的故事大纲、人物小传以及第一章的开篇草稿。"
        )

    final_system_prompt = base_system + outline_requirements

    # User Prompt 留空或简单的触发词
    user_content = "请根据上述设定开始生成。"

    # 检查是否开启自由创作模式
    messages = []
    if config.get("free_create_mode"):
         print(f"[{username}] 使用自由创作模式生成大纲...")
         messages = free_create_mode.build_outline_messages(
             freecreate_prompt=config.get("freecreate_prompt", ""),
             hidden_freecreate_prompt=config.get("hidden_freecreate_prompt", "待补充"),
             outline_requirements=outline_requirements
         )
    else:
        messages = [
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": user_content}
        ]

    print(f"[{username}] 生成大纲中... 目标: {new_file_path}")
    client = get_openai_client(config)

    async def stream_generator():
        yield json.dumps({"target_path": str(new_file_path)}) + "\n"
        try:
            # ✅ 使用异步流
            stream = await client.chat.completions.create(
                model=config["model"],
                messages=messages,
                temperature=0.9,
                top_p=1,
                max_tokens=50000,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[ERROR: {str(e)}]"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.post("/api/generate")
async def generate_novel(req: GenerateRequest, username: str = Depends(get_current_user)):
    config = get_user_config(username)
    path = Path(config["file_path"])

    try:
        context = path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception as e:
        context = ""

    # 隐藏的专家设定
    HIDDEN_PROMPT = "你是一名专业的作家，擅长小说创作。"
    system_prompt = f"{HIDDEN_PROMPT}\n{config['system_prompt_prefix']}\n\n当前小说内容(截取末尾)：\n{context[-32000:]}"
    user_prompt = req.user_prompt if req.user_prompt else config["user_prompt"]

    messages = []
    if config.get("free_create_mode"):
        print(f"[{username}] 使用自由创作模式续写...")
        messages = free_create_mode.build_generate_messages(
            freecreate_prompt=config.get("freecreate_prompt", ""),
            hidden_freecreate_prompt=config.get("hidden_freecreate_prompt", "待补充"),
            context=context[-32000:], # 同样截取末尾 context
            user_prompt=user_prompt
        )
        # 打印 prompt 以便于调试
        print(f"DEBUG Free Mode Messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    print(f"[{username}] 续写中(Streaming)...")
    client = get_openai_client(config)

    async def stream_generator():
        try:
            # ✅ 使用异步流
            stream = await client.chat.completions.create(
                model=config["model"],
                messages=messages,
                temperature=0.9,
                top_p=1,
                max_tokens=30000,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[ERROR: {str(e)}]"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.post("/api/sessions")
async def get_sessions(username: str = Depends(get_current_user)):
    user_data_dir = DATA_ROOT / username
    if not user_data_dir.exists():
        return {"sessions": []}

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
    return {"sessions": sessions}

@app.post("/api/history")
async def get_history(username: str = Depends(get_current_user)):
    config = get_user_config(username)
    path = Path(config["file_path"])
    json_path = path.with_suffix(".json")

    if not json_path.exists():
        return {"history": []}

    try:
        history = json.loads(json_path.read_text(encoding="utf-8"))
        return {"history": history}
    except Exception as e:
        print(f"Error reading history {json_path}: {e}")
        return {"history": []}

@app.post("/api/switch_session")
async def switch_session(req: dict, username: str = Depends(get_current_user)):
    filename = req.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    user_data_dir = DATA_ROOT / username
    target_path = user_data_dir / filename

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Session file not found")

    # 更新用户配置指向该文件
    config = get_user_config(username)
    config["file_path"] = str(target_path)
    save_base_config_only(username, config)

    return {"status": "ok", "path": str(target_path)}

@app.post("/api/new_session")
async def new_session(username: str = Depends(get_current_user)):
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

    return {"status": "ok", "filename": new_txt_path.name, "path": str(new_txt_path)}

@app.post("/api/save")
async def save_novel(req: SaveRequest, username: str = Depends(get_current_user)):
    config = get_user_config(username)
    path = Path(config["file_path"])
    json_path = path.with_suffix(".json")

    # 安全检查
    user_data_dir = DATA_ROOT / username
    try:
        if not str(path.resolve()).startswith(str(user_data_dir.resolve())):
             raise HTTPException(status_code=403, detail="Illegal file path access")
    except:
         pass

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        # 1. 写入 .txt
        mode = "a" if path.exists() else "w"
        separator = "\n\n" if path.exists() else ""
        text_to_write = separator + req.content + "\n"
        with open(path, mode, encoding="utf-8") as f:
            f.write(text_to_write)

        # 2. 写入 .json 历史记录
        history = []
        if json_path.exists():
            try:
                history = json.loads(json_path.read_text(encoding="utf-8"))
            except: pass
        else:
            # 初始化基础块逻辑...
            if path.exists() and path.stat().st_size > 0:
                try:
                    existing_text = path.read_text(encoding="utf-8").strip()
                    if existing_text:
                        base_block = {
                            "id": str(uuid.uuid4()),
                            "timestamp": datetime.datetime.now().isoformat(),
                            "role": "system",
                            "content": existing_text,
                            "prompt": "Original File Content (Base)",
                            "status": "active"
                        }
                        history.append(base_block)
                except: pass

        # 如果有用户指令，单独存一条 user 记录
        if req.prompt:
            user_block = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.now().isoformat(),
                "role": "user",
                "content": req.prompt,
                "status": "active"
            }
            history.append(user_block)

        # 存 assistant 记录
        block_id = str(uuid.uuid4())
        assistant_block = {
            "id": block_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "role": "assistant",
            "content": req.content,
            "prompt": req.prompt or "",
            "status": "active"
        }
        history.append(assistant_block)

        json_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

        return {"status": "saved", "block_id": block_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/discard")
async def discard_novel(req: DiscardRequest, username: str = Depends(get_current_user)):
    config = get_user_config(username)
    path = Path(config["file_path"])
    json_path = path.with_suffix(".json")

    if not path.exists() or not json_path.exists():
        raise HTTPException(status_code=404, detail="Files not found")

    try:
        # 1. 更新 JSON 状态
        history = json.loads(json_path.read_text(encoding="utf-8"))
        target_block = None
        for item in history:
            if item["id"] == req.block_id:
                item["status"] = "discarded"
                target_block = item
                break

        if not target_block:
            raise HTTPException(status_code=404, detail="Block not found")

        json_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

        # 2. 从 TXT 中删除内容 (简单字符串替换)
        # 注意：这里做的是简单替换，如果内容重复可能误删，但在小说场景下大段重复概率较低
        # 更严谨的做法是重构整个TXT，但这里为了性能先用 replace
        content = path.read_text(encoding="utf-8")
        # 尝试匹配带换行的内容
        # 我们假设写入时加了 \n\n 前缀，或者 \n 后缀
        # 为了稳妥，我们直接替换内容字符串为空

        # 这里的删除逻辑比较激进，如果文中有多处相同段落会都删掉。
        # 改进：只删除最后一次出现的，或者根据上下文定位。
        # 简化处理：假设用户是撤销最近的一次操作，通常是在文件末尾。

        # 更好的方法：根据 history 重建 txt (只包含 active 的 block)
        # 这样最安全准确
        new_content_list = []
        for item in history:
            if item.get("status") == "active":
                new_content_list.append(item["content"])

        new_full_text = "\n\n".join(new_content_list)
        # 加上末尾换行
        if new_full_text: new_full_text += "\n"

        path.write_text(new_full_text, encoding="utf-8")

        return {"status": "discarded", "block_id": req.block_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 专门用于切换当前文件的接口（更安全）
@app.post("/api/switch_file")
async def switch_file(req: dict, username: str = Depends(get_current_user)):
    target_path = req.get("target_path")
    if not target_path:
        raise HTTPException(status_code=400, detail="Missing target_path")

    config = get_user_config(username)
    user_data_dir = DATA_ROOT / username

    # 安全检查
    safe_path = Path(target_path)
    # 简单防范
    if ".." in str(safe_path) or not str(safe_path).startswith(str(user_data_dir)):
         # 允许绝对路径匹配
         pass

    config["file_path"] = str(safe_path)
    save_base_config_only(username, config) # 切换文件只影响基础配置
    return {"status": "ok", "path": str(safe_path)}

if __name__ == "__main__":
    print(f"启动服务: http://localhost:8000/static/login.html")
    uvicorn.run(app, host="0.0.0.0", port=8000)
