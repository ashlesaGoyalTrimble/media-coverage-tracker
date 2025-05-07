from pydantic import BaseModel

class MessageRequest(BaseModel):
    message: str
    stream: bool

class AssistantCreateRequest(BaseModel):
    id: str

class Tool(BaseModel):
    function: dict
    type: str
