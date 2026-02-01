import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.api.endpoints import auth, config, novel, sessions, admin

# 定义项目根目录
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(novel.router, prefix="/api", tags=["novel"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# 挂载静态文件
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

@app.get("/")
async def read_root():
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    # 端口保持用户要求的 19000
    print(f"启动服务: http://localhost:19000/static/login.html")
    uvicorn.run(app, host="0.0.0.0", port=19000)
