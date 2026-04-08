"""BlobReference 聚合根单元测试

覆盖：
- create() 工厂方法：字段赋值、ref_id 唯一性
- get_aggregate_id() 返回 ref_id
- __str__ 输出可读字符串
"""

import pytest

from app.blob.domain.aggregate.blob_reference import BlobReference


class TestBlobReferenceCreate:
    def test_creates_with_correct_fields(self):
        ref = BlobReference.create(
            blob_id="blob-001",
            owner_type="user",
            owner_id="user-001",
            edge_key="avatar",
        )
        assert ref.blob_id == "blob-001"
        assert ref.owner_type == "user"
        assert ref.owner_id == "user-001"
        assert ref.edge_key == "avatar"

    def test_ref_id_is_auto_generated(self):
        ref = BlobReference.create(
            blob_id="blob-001",
            owner_type="user",
            owner_id="user-001",
            edge_key="avatar",
        )
        assert ref.ref_id is not None
        assert len(ref.ref_id) == 32  # uuid4().hex → 32 chars

    def test_each_create_generates_unique_ref_id(self):
        ref1 = BlobReference.create(
            blob_id="blob-001",
            owner_type="user",
            owner_id="user-001",
            edge_key="avatar",
        )
        ref2 = BlobReference.create(
            blob_id="blob-001",
            owner_type="user",
            owner_id="user-001",
            edge_key="avatar",
        )
        assert ref1.ref_id != ref2.ref_id

    def test_get_aggregate_id_returns_ref_id(self):
        ref = BlobReference.create(
            blob_id="blob-001",
            owner_type="user",
            owner_id="user-001",
            edge_key="avatar",
        )
        assert ref.get_aggregate_id() == ref.ref_id

    def test_str_contains_key_info(self):
        ref = BlobReference.create(
            blob_id="blob-001",
            owner_type="post",
            owner_id="post-999",
            edge_key="cover",
        )
        s = str(ref)
        assert "blob-001" in s
        assert "post" in s
        assert "cover" in s

    def test_created_at_defaults_to_none(self):
        ref = BlobReference.create(
            blob_id="blob-001",
            owner_type="user",
            owner_id="user-001",
            edge_key="avatar",
        )
        assert ref.created_at is None
