from pydantic import BaseModel

class UserGetByUsernameCommand(BaseModel):
    username:str


class UserGetByIdCommand(BaseModel):
    user_id: str