from pydantic import BaseModel


class SuccessResponse(BaseModel):
    result: str
    message: str
