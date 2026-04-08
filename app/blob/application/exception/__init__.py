from core.exceptions import CustomException


class BlobNotFoundException(CustomException):
    code = 404
    error_code = "BLOB__NOT_FOUND"
    message = "blob not found"


class BlobNotReadyException(CustomException):
    code = 409
    error_code = "BLOB__NOT_READY"
    message = "blob is not ready"


class BlobStorageNotConfiguredException(CustomException):
    code = 500
    error_code = "BLOB__STORAGE_NOT_CONFIGURED"
    message = "blob storage adapter is not configured"


class BlobStorageLocationMissingException(CustomException):
    code = 404
    error_code = "BLOB__STORAGE_LOCATION_MISSING"
    message = "blob storage location not found"



