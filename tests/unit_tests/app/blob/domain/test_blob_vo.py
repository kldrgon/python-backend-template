"""Blob 值对象单元测试

覆盖：
- SHA256Hash：格式校验、大小写归一化、相等性
- MimeType：格式校验、类型判断方法
- StorageLocator：创建、unique_key、相等性、is_s3_compatible
"""

import pytest
from pydantic import ValidationError

from app.blob.domain.vo.hash import SHA256Hash
from app.blob.domain.vo.mime_type import MimeType
from app.blob.domain.entity.storage_locator import StorageLocator


VALID_SHA256 = "a" * 64


# --- SHA256Hash ---


class TestSHA256Hash:
    def test_valid_hash_created(self):
        h = SHA256Hash(value=VALID_SHA256)
        assert str(h) == VALID_SHA256

    def test_uppercase_normalised_to_lowercase(self):
        h = SHA256Hash(value=VALID_SHA256.upper())
        assert str(h) == VALID_SHA256.lower()

    def test_invalid_length_raises(self):
        with pytest.raises(ValidationError):
            SHA256Hash(value="abc123")

    def test_invalid_chars_raises(self):
        with pytest.raises(ValidationError):
            SHA256Hash(value="z" * 64)

    def test_equality_with_string(self):
        h = SHA256Hash(value=VALID_SHA256)
        assert h == VALID_SHA256

    def test_equality_with_same_hash(self):
        h1 = SHA256Hash(value=VALID_SHA256)
        h2 = SHA256Hash(value=VALID_SHA256)
        assert h1 == h2

    def test_inequality_with_different_hash(self):
        h1 = SHA256Hash(value="a" * 64)
        h2 = SHA256Hash(value="b" * 64)
        assert h1 != h2

    def test_hashable(self):
        h = SHA256Hash(value=VALID_SHA256)
        s = {h}
        assert h in s


# --- MimeType ---


class TestMimeType:
    def test_valid_mime_type(self):
        m = MimeType(value="image/png")
        assert str(m) == "image/png"

    def test_uppercase_normalised(self):
        m = MimeType(value="Image/PNG")
        assert str(m) == "image/png"

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError):
            MimeType(value="notamimetype")

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            MimeType(value="")

    def test_is_image(self):
        assert MimeType(value="image/jpeg").is_image() is True
        assert MimeType(value="text/plain").is_image() is False

    def test_is_text(self):
        assert MimeType(value="text/html").is_text() is True

    def test_is_video(self):
        assert MimeType(value="video/mp4").is_video() is True

    def test_main_type(self):
        assert MimeType(value="application/json").main_type == "application"

    def test_sub_type(self):
        assert MimeType(value="application/json").sub_type == "json"

    def test_equality_with_string(self):
        m = MimeType(value="image/png")
        assert m == "image/png"

    def test_from_filename(self):
        m = MimeType.from_filename("photo.jpg")
        assert m.is_image()

    def test_from_filename_unknown_returns_octet_stream(self):
        m = MimeType.from_filename("file.unknownextension123")
        assert str(m) == "application/octet-stream"


# --- StorageLocator ---


class TestStorageLocator:
    def _make(self, **kwargs):
        defaults = dict(
            storage_provider="minio",
            bucket="test-bucket",
            object_key="uploads/test.png",
            region="us-east-1",
        )
        defaults.update(kwargs)
        return StorageLocator(**defaults)

    def test_valid_locator(self):
        loc = self._make()
        assert loc.storage_provider == "minio"
        assert loc.bucket == "test-bucket"
        assert loc.object_key == "uploads/test.png"

    def test_provider_normalised_to_lowercase(self):
        loc = self._make(storage_provider="S3")
        assert loc.storage_provider == "s3"

    def test_empty_provider_raises(self):
        with pytest.raises(ValidationError):
            self._make(storage_provider="")

    def test_bucket_too_short_raises(self):
        with pytest.raises(ValidationError):
            self._make(bucket="ab")

    def test_bucket_too_long_raises(self):
        with pytest.raises(ValidationError):
            self._make(bucket="a" * 64)

    def test_empty_object_key_raises(self):
        with pytest.raises(ValidationError):
            self._make(object_key="")

    def test_unique_key(self):
        loc = self._make()
        assert loc.unique_key == "minio:test-bucket:uploads/test.png"

    def test_equality(self):
        loc1 = self._make()
        loc2 = self._make()
        assert loc1 == loc2

    def test_inequality_different_key(self):
        loc1 = self._make(object_key="uploads/a.png")
        loc2 = self._make(object_key="uploads/b.png")
        assert loc1 != loc2

    def test_is_s3_compatible_minio(self):
        assert self._make(storage_provider="minio").is_s3_compatible() is True

    def test_is_s3_compatible_s3(self):
        assert self._make(storage_provider="s3").is_s3_compatible() is True

    def test_is_s3_compatible_gcs(self):
        assert self._make(storage_provider="gcs").is_s3_compatible() is False

    def test_str_representation(self):
        loc = self._make()
        s = str(loc)
        assert "minio" in s
        assert "test-bucket" in s

    def test_hashable(self):
        loc = self._make()
        s = {loc}
        assert loc in s
