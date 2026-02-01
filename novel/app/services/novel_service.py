import json
import uuid
import datetime
import re
from pathlib import Path
from openai import AsyncOpenAI
from app.core.config import DATA_ROOT
from app.services.user_manager import get_user_config, save_base_config_only
from app.services.prompt_builder import build_generate_messages, build_outline_messages

# --- Helper ---
def get_openai_client(config):
    return AsyncOpenAI(base_url=config["base_url"], api_key=config["api_key"])

# --- File Operations ---

def get_novel_content(username: str, full: bool = False):
    config = get_user_config(username)
    path = Path(config["file_path"])

    if not path.exists():
        return {"content": "", "path": str(path), "full_length": 0}

    content = path.read_text(encoding="utf-8")
    if full:
        return {"content": content}

    preview = content[-2000:] if len(content) > 2000 else content
    return {"content": preview, "full_length": len(content), "path": str(path)}

def save_novel_content(username: str, content: str, prompt: str = ""):
    config = get_user_config(username)
    path = Path(config["file_path"])
    json_path = path.with_suffix(".json")
    user_data_dir = DATA_ROOT / username

    # Security check
    try:
        if not str(path.resolve()).startswith(str(user_data_dir.resolve())):
             raise ValueError("Illegal file path access")
    except:
         # Fallback check if resolve fails
         if str(user_data_dir) not in str(path):
             raise ValueError("Illegal file path access")

    path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Write TXT
    mode = "a" if path.exists() else "w"
    separator = "\n\n" if path.exists() else ""
    text_to_write = separator + content + "\n"
    with open(path, mode, encoding="utf-8") as f:
        f.write(text_to_write)

    # 2. Write JSON history
    history = []
    if json_path.exists():
        try:
            history = json.loads(json_path.read_text(encoding="utf-8"))
        except: pass
    else:
        # Initialize base block if needed
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

    if prompt:
        user_block = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now().isoformat(),
            "role": "user",
            "content": prompt,
            "status": "active"
        }
        history.append(user_block)

    block_id = str(uuid.uuid4())
    assistant_block = {
        "id": block_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "role": "assistant",
        "content": content,
        "prompt": prompt or "",
        "status": "active"
    }
    history.append(assistant_block)

    json_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return block_id

def discard_novel_block(username: str, block_id: str):
    config = get_user_config(username)
    path = Path(config["file_path"])
    json_path = path.with_suffix(".json")

    if not path.exists() or not json_path.exists():
        raise FileNotFoundError("Files not found")

    # Update JSON
    history = json.loads(json_path.read_text(encoding="utf-8"))
    target_block = None
    for item in history:
        if item["id"] == block_id:
            item["status"] = "discarded"
            target_block = item
            break

    if not target_block:
        raise ValueError("Block not found")

    json_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

    # Reconstruct TXT
    new_content_list = []
    for item in history:
        if item.get("status") == "active":
            new_content_list.append(item["content"])

    new_full_text = "\n\n".join(new_content_list)
    if new_full_text: new_full_text += "\n"

    path.write_text(new_full_text, encoding="utf-8")
    return block_id

async def auto_rename_novel(username: str):
    config = get_user_config(username)
    path = Path(config["file_path"])

    if not path.exists():
        return {"status": "skipped", "reason": "file not found"}

    filename = path.stem
    if not re.match(r"^\d{8}_\d{6}$", filename):
         return {"status": "skipped", "reason": "not a timestamp file"}

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

    old_json_path = path.with_suffix(".json")
    if old_json_path.exists():
        new_json_path = new_path.with_suffix(".json")
        old_json_path.rename(new_json_path)

    config["file_path"] = str(new_path)
    save_base_config_only(username, config)

    return {"status": "renamed", "new_name": new_title, "new_path": str(new_path)}

# --- Generation ---

async def generate_novel_stream(username: str, req_user_prompt: str = None):
    config = get_user_config(username)
    path = Path(config["file_path"])

    try:
        context = path.read_text(encoding="utf-8") if path.exists() else ""
    except:
        context = ""

    HIDDEN_PROMPT = "你是一名专业的作家，擅长小说创作。"
    system_prompt = f"{HIDDEN_PROMPT}\n{config['system_prompt_prefix']}\n\n当前小说内容：\n{context}"
    user_prompt = req_user_prompt if req_user_prompt else config["user_prompt"]

    messages = []
    if config.get("free_create_mode"):
        messages = build_generate_messages(
            freecreate_prompt=config.get("freecreate_prompt", ""),
            pre_hidden_freecreate_prompt=config.get("pre_hidden_freecreate_prompt", "待补充"),
            post_hidden_freecreate_prompt=config.get("post_hidden_freecreate_prompt", ""),
            context=context,
            user_prompt=user_prompt
        )
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    client = get_openai_client(config)

    # Logic from previous successful edit:
    # Free Mode -> Non-Stream (Wait & Yield All)
    # Normal Mode -> Stream

    try:
        if config.get("free_create_mode"):
            resp = await client.chat.completions.create(
                model=config["model"],
                messages=messages,
                temperature=0.9,
                top_p=1,
                max_tokens=10000,
                stream=False
            )
            full_content = resp.choices[0].message.content
            yield full_content
        else:
            stream = await client.chat.completions.create(
                model=config["model"],
                messages=messages,
                temperature=0.9,
                top_p=1,
                max_tokens=10000,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"\n[ERROR: {str(e)}]"

async def generate_outline_stream(username: str, req):
    config = get_user_config(username)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    user_data_dir = DATA_ROOT / username
    user_data_dir.mkdir(parents=True, exist_ok=True)
    new_file_path = user_data_dir / f"{timestamp}.txt"

    HIDDEN_PROMPT = "你是一名专业的作家，擅长小说创作，文笔极佳，情节设计引人入胜。"
    base_system = f"{HIDDEN_PROMPT}\n{config['system_prompt_prefix']}"

    if config.get("free_create_mode"):
        parts = []
        if req.plot: parts.append(req.plot)
        if req.protagonist: parts.append(f"主角: {req.protagonist}")
        if req.style: parts.append(f"风格: {req.style}")
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
    user_content = "请根据上述设定开始生成。"

    messages = []
    if config.get("free_create_mode"):
         messages = build_outline_messages(
             freecreate_prompt=config.get("freecreate_prompt", ""),
             pre_hidden_freecreate_prompt=config.get("pre_hidden_freecreate_prompt", "待补充"),
             post_hidden_freecreate_prompt=config.get("post_hidden_freecreate_prompt", ""),
             outline_requirements=outline_requirements
         )
    else:
        messages = [
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": user_content}
        ]

    client = get_openai_client(config)

    yield json.dumps({"target_path": str(new_file_path)}) + "\n"

    try:
        # Outline usually needs stream too
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
