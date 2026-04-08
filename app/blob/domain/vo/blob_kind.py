from enum import Enum


class BlobKind(str, Enum):
    TEMPORARY = "temporary"
    PERMANENT = "permanent"

