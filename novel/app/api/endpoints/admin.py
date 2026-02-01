from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.schemas import Group, GroupCreate, UserGroupUpdate
from app.services import group_service, user_manager
from app.api.deps import get_current_user

router = APIRouter()

# 注意：实际生产中 Admin 接口应该有更严格的鉴权（例如检查是否是 admin 组用户）
# 这里为了演示方便，暂时只检查是否登录，或者简单检查是否属于 admin 组

def get_admin_user(username: str = Depends(get_current_user)):
    user_group = user_manager.get_user_group(username)
    if user_group != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return username

@router.get("/groups", response_model=List[Group])
async def list_groups(username: str = Depends(get_current_user)):
    # 普通用户也可以查看有哪些组（可选）
    return group_service.list_groups()

@router.post("/groups", response_model=Group)
async def create_group(group: GroupCreate, admin: str = Depends(get_admin_user)):
    try:
        return group_service.create_group(group)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/users/group")
async def update_user_group(update: UserGroupUpdate, admin: str = Depends(get_admin_user)):
    # 检查组是否存在
    if not group_service.get_group(update.group_name):
        raise HTTPException(status_code=404, detail="目标用户组不存在")

    try:
        user_manager.update_user_group(update.username, update.group_name)
        return {"status": "ok", "message": f"用户 {update.username} 已移动到组 {update.group_name}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
