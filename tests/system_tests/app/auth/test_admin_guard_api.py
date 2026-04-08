"""Admin permission guard system tests."""

from uuid import uuid4

from core.helpers.token import TokenHelper


def _headers_for_roles(*, user_id: str, roles: list[str]) -> dict[str, str]:
    normalized_roles = [str(item).upper() for item in roles if item]
    token = TokenHelper.encode(
        payload={
            "user_id": user_id,
            "sub": "access",
            "role": normalized_roles[0] if normalized_roles else None,
            "roles": normalized_roles,
        },
        expire_period=3600,
    )
    return {"Authorization": f"Bearer {token}"}


class TestAdminGuardApi:
    async def test_admin_can_write_kp_course_problem_bank(self, client):
        admin_headers = _headers_for_roles(user_id=f"admin-{uuid4().hex[:8]}", roles=["ADMIN"])
        suffix = uuid4().hex[:8]

        kg_resp = await client.post(
            "/knowledge-graph/v1/graphs",
            json={"name": f"管理员图谱-{suffix}"},
            headers=admin_headers,
        )
        assert kg_resp.status_code == 201

        course_resp = await client.post(
            "/course/v1/courses",
            json={"title": f"管理员课程-{suffix}", "description": []},
            headers=admin_headers,
        )
        assert course_resp.status_code == 201

        problem_resp = await client.post(
            "/problem-bank/v1/problems",
            json={
                "title": f"管理员题目-{suffix}",
                "content": [],
                "tags": ["guard"],
            },
            headers=admin_headers,
        )
        assert problem_resp.status_code == 201

    async def test_non_admin_write_is_forbidden(self, client):
        student_headers = _headers_for_roles(user_id=f"student-{uuid4().hex[:8]}", roles=["STUDENT"])
        suffix = uuid4().hex[:8]

        kg_resp = await client.post(
            "/knowledge-graph/v1/graphs",
            json={"name": f"学生图谱-{suffix}"},
            headers=student_headers,
        )
        assert kg_resp.status_code == 403

        course_resp = await client.post(
            "/course/v1/courses",
            json={"title": f"学生课程-{suffix}", "description": []},
            headers=student_headers,
        )
        assert course_resp.status_code == 403

        problem_resp = await client.post(
            "/problem-bank/v1/problems",
            json={
                "title": f"学生题目-{suffix}",
                "content": [],
                "tags": ["guard"],
            },
            headers=student_headers,
        )
        assert problem_resp.status_code == 403
