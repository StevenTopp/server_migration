from typing import Optional
from pydantic import BaseModel

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
    pre_hidden_freecreate_prompt: Optional[str] = ""
    post_hidden_freecreate_prompt: Optional[str] = ""

class Group(BaseModel):
    name: str
    description: str
    allow_free_mode: bool = False

class GroupCreate(BaseModel):
    name: str
    description: str
    allow_free_mode: bool = False

class UserGroupUpdate(BaseModel):
    username: str
    group_name: str
