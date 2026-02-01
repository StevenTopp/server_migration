from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import ConfigRequest
from app.services.user_manager import get_user_config, save_user_config_split, get_user_group
from app.services.group_service import can_use_free_mode
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/config")
async def get_config(username: str = Depends(get_current_user)):
    return get_user_config(username)

@router.post("/config")
async def update_config(config: ConfigRequest, username: str = Depends(get_current_user)):
    # 权限检查
    if config.free_create_mode:
        user_group = get_user_group(username)
        if not can_use_free_mode(user_group):
            # 如果不允许，强制设为 False，或者报错
            # 这里选择温和的方式：强制关闭并提示（实际前端可能只是看起来没生效，或者我们可以抛出 403）
            # 为了用户体验，我们抛出明确的错误
            raise HTTPException(status_code=403, detail="当前用户组无权使用自由创作模式")

    # 获取旧配置以保留 file_path (不让前端直接改 file_path 防止越权)
    old_config = get_user_config(username)

    new_config_dict = config.dict()
    new_config_dict["file_path"] = old_config["file_path"] # 强制保留原路径

    # 使用拆分保存逻辑
    save_user_config_split(username, new_config_dict)
    return {"status": "updated", "config": new_config_dict}
