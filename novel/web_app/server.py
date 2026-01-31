import os
import uvicorn
import secrets
import base64
import datetime
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from openai import OpenAI
import asyncio

# ================= 配置区域 =================
# 🔐 安全验证配置 (支持环境变量)
AUTH_USER = os.getenv("AUTH_USER", "steven")
AUTH_PASS = os.getenv("AUTH_PASS", "qwer1234")

# 默认配置
DEFAULT_CONFIG = {
    "base_url": "http://127.0.0.1:19000/v1",
    "api_key": "sk-c14a5dd7304f458fbc49acfd9889e74f",
    "model": "gemini-3-pro",
    "file_path": r"D:\Code\models\aa.txt",
    "system_prompt_prefix": "续写小说，详细描述互动细节，并增加描述词，逐步推进小说剧情，",
    "user_prompt": "每次生成6000字，并在最后给出下一章节1条20字建议"
}

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🛡️ 全局 Basic Auth 中间件
# ==========================================
@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return Response(status_code=401, headers={"WWW-Authenticate": "Basic"}, content="Unauthorized")

    try:
        scheme, credentials = auth_header.split()
        if scheme.lower() != 'basic':
            raise ValueError
        decoded = base64.b64decode(credentials).decode("ascii")
        username, password = decoded.split(":", 1)

        is_user_ok = secrets.compare_digest(username, AUTH_USER)
        is_pass_ok = secrets.compare_digest(password, AUTH_PASS)

        if not (is_user_ok and is_pass_ok):
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"}, content="Invalid credentials")
    except (ValueError, IndexError):
        return Response(status_code=401, headers={"WWW-Authenticate": "Basic"}, content="Invalid header")

    return await call_next(request)

# 挂载静态文件
STATIC_DIR = Path(__file__).parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

# ================= 模型定义 =================
class GenerateRequest(BaseModel):
    user_prompt: str = None

class SaveRequest(BaseModel):
    content: str

class ConfigRequest(BaseModel):
    base_url: str
    api_key: str
    model: str
    file_path: str
    system_prompt_prefix: str
    user_prompt: str

class OutlineRequest(BaseModel):
    protagonist: str
    age: str
    style: str
    plot: str
    word_count: str

# 内存配置
current_config = DEFAULT_CONFIG.copy()

def get_client():
    return OpenAI(base_url=current_config["base_url"], api_key=current_config["api_key"])

# ================= API 路由 =================
@app.get("/")
async def read_root():
    return {"status": "ok", "message": "Novel Generator API"}

@app.get("/api/config")
async def get_config():
    return current_config

@app.post("/api/config")
async def update_config(config: ConfigRequest):
    global current_config
    current_config.update(config.dict())
    return {"status": "updated", "config": current_config}

@app.get("/api/novel")
async def get_novel_content():
    path = Path(current_config["file_path"])
    if not path.exists():
        return {"content": "", "path": str(path)}
    try:
        content = path.read_text(encoding="utf-8")
        preview = content[-2000:] if len(content) > 2000 else content
        return {"content": preview, "full_length": len(content), "path": str(path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/outline")
async def generate_outline(req: OutlineRequest):
    # 生成时间戳文件路径
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(r"D:\Code\Project\server_migration\novel\data")
    if not base_dir.exists():
        base_dir.mkdir(parents=True)
    new_file_path = base_dir / f"{timestamp}.txt"

    prompt = (
        f"任务：创建小说大纲\n"
        f"主角：{req.protagonist} (年龄: {req.age})\n"
        f"风格：{req.style}\n"
        f"预期字数：{req.word_count}\n"
        f"故事梗概/走向：{req.plot}\n\n"
        f"请生成详细的故事大纲、人物小传以及第一章的开篇草稿。"
    )

    print(f"生成大纲中... 目标: {new_file_path}")
    client = get_client()

    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=current_config["model"],
            messages=[
                {"role": "system", "content": "你是一个专业的小说主编和策划。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=8192,
            stream=False
        )
        content = resp.choices[0].message.content
        return {"result": content, "target_path": str(new_file_path)}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate")
async def generate_novel(req: GenerateRequest):
    path = Path(current_config["file_path"])
    try:
        context = path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception as e:
        context = ""

    system_prompt = f"{current_config['system_prompt_prefix']}\n\n当前小说内容(截取末尾)：\n{context[-8000:]}" # 限制上下文长度防止溢出
    user_prompt = req.user_prompt if req.user_prompt else current_config["user_prompt"]

    print("续写中...")
    client = get_client()

    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=current_config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.9,
            max_tokens=8192,
            stream=False
        )
        content = resp.choices[0].message.content
        return {"result": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save")
async def save_novel(req: SaveRequest):
    path = Path(current_config["file_path"])
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # 如果文件不存在，则是新建，用 write；如果存在，则是续写，用 append
        mode = "a" if path.exists() else "w"
        separator = "\n\n" if path.exists() else ""

        with open(path, mode, encoding="utf-8") as f:
            f.write(separator + req.content + "\n")

        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print(f"启动服务: http://localhost:8000/static/index.html")
    print(f"🔐 认证开启 - 用户名: {AUTH_USER} | 密码: {AUTH_PASS}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
