from typing import List
from pydantic import BaseModel

class UserRolesAssignCommand(BaseModel):
    user_id: str
    roles: List[str]