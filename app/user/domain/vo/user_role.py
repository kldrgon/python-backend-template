from enum import Enum

class UserRole(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"