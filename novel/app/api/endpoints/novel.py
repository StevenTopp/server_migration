from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models.schemas import GenerateRequest, SaveRequest, DiscardRequest, OutlineRequest
from app.services import novel_service
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/novel")
async def get_novel_content(full: bool = False, username: str = Depends(get_current_user)):
    try:
        return novel_service.get_novel_content(username, full)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auto_rename")
async def auto_rename(username: str = Depends(get_current_user)):
    try:
        return await novel_service.auto_rename_novel(username)
    except Exception as e:
        print(f"Rename failed: {e}")
        return {"status": "error", "detail": str(e)}

@router.post("/outline")
async def generate_outline(req: OutlineRequest, username: str = Depends(get_current_user)):
    print(f"[{username}] 生成大纲中...")
    return StreamingResponse(
        novel_service.generate_outline_stream(username, req),
        media_type="text/event-stream"
    )

@router.post("/generate")
async def generate_novel(req: GenerateRequest, username: str = Depends(get_current_user)):
    print(f"[{username}] 续写中...")
    return StreamingResponse(
        novel_service.generate_novel_stream(username, req.user_prompt),
        media_type="text/event-stream"
    )

@router.post("/save")
async def save_novel(req: SaveRequest, username: str = Depends(get_current_user)):
    try:
        block_id = novel_service.save_novel_content(username, req.content, req.prompt)
        return {"status": "saved", "block_id": block_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/discard")
async def discard_novel(req: DiscardRequest, username: str = Depends(get_current_user)):
    try:
        novel_service.discard_novel_block(username, req.block_id)
        return {"status": "discarded", "block_id": req.block_id}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Files not found")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
