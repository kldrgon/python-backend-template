"""User 聚合根单元测试 - 零依赖，纯内存"""

import pytest
from app.user.domain.aggregate.user import User
from app.user.domain.entity.linked_account import LinkedAccount
from app.user.domain.event.user_events import (
    UserCreatedEvent,
    UserEnabledEvent,
    UserDisabledEvent,
    UserRolesAssignedEvent,
    UserRolesRevokedEvent,
    UserProfileUpdatedEvent,
    UserPasswordSetEvent,
    UserThirdPartyLinkedEvent,
    UserThirdPartyUnlinkedEvent,
)
from app.user.domain.exception import (
    InvalidEmailError,
    WeakPasswordError,
    EmptyNicknameError,
    DisabledUserCannotBeAssignedRolesError,
)
from app.user.domain.vo.location import Address


# ── 辅助工厂 ─────────────────────────────────────────────────────────────

def _make_user(
    *,
    user_id: str = "u1",
    email: str = "test@example.com",
    password: str = "password123",
    nickname: str = "testuser",
    role: str = "",
) -> User:
    return User.create(
        user_id=user_id,
        email=email,
        password=password,
        nickname=nickname,
        role=role,
    )


def _events_of(user: User, event_class: type) -> list:
    return [e for e in user.get_domain_events() if isinstance(e, event_class)]


# ── create() ────────────────────────────────────────────────────────────


class TestUserCreate:
    def test_create_success_state(self):
        user = _make_user()
        assert user.user_id == "u1"
        assert user.email == "test@example.com"
        assert user.nickname == "testuser"
        assert user.enabled is True
        assert user.is_admin is False

    def test_create_hashes_password(self):
        user = _make_user(password="password123")
        assert user.hashed_password != "password123"
        assert len(user.hashed_password) > 0

    def test_create_without_role_raises_only_created_event(self):
        user = _make_user(role="")
        events = user.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], UserCreatedEvent)

    def test_create_with_role_raises_roles_assigned_then_created(self):
        user = _make_user(role="STUDENT")
        events = user.get_domain_events()
        assert len(events) == 2
        assert isinstance(events[0], UserRolesAssignedEvent)
        assert isinstance(events[1], UserCreatedEvent)
        assert "STUDENT" in events[0].payload["roles"]

    def test_create_event_payload(self):
        user = _make_user(user_id="u42", email="a@b.com", nickname="nick")
        evt = _events_of(user, UserCreatedEvent)[0]
        assert evt.payload["user_id"] == "u42"
        assert evt.payload["email"] == "a@b.com"
        assert evt.payload["nickname"] == "nick"

    def test_create_invalid_email_no_at(self):
        with pytest.raises(InvalidEmailError):
            _make_user(email="invalidemail")

    def test_create_invalid_email_empty(self):
        with pytest.raises(InvalidEmailError):
            _make_user(email="")

    def test_create_weak_password_too_short(self):
        with pytest.raises(WeakPasswordError):
            _make_user(password="123")

    def test_create_weak_password_empty(self):
        with pytest.raises(WeakPasswordError):
            _make_user(password="")

    def test_create_empty_nickname(self):
        with pytest.raises(EmptyNicknameError):
            _make_user(nickname="")


# ── enable() / disable() ────────────────────────────────────────────────


class TestUserEnableDisable:
    def test_disable_enabled_user_changes_state_and_raises_event(self):
        user = _make_user()
        user.clear_domain_events()
        user.disable()
        assert user.enabled is False
        events = _events_of(user, UserDisabledEvent)
        assert len(events) == 1

    def test_disable_already_disabled_does_not_raise_event(self):
        user = _make_user()
        user.disable()
        user.clear_domain_events()
        user.disable()
        assert _events_of(user, UserDisabledEvent) == []

    def test_enable_disabled_user_changes_state_and_raises_event(self):
        user = _make_user()
        user.disable()
        user.clear_domain_events()
        user.enable()
        assert user.enabled is True
        events = _events_of(user, UserEnabledEvent)
        assert len(events) == 1

    def test_enable_already_enabled_does_not_raise_event(self):
        user = _make_user()
        user.clear_domain_events()
        user.enable()
        assert _events_of(user, UserEnabledEvent) == []


# ── assign_roles() ──────────────────────────────────────────────────────


class TestUserAssignRoles:
    def test_assign_new_roles_updates_state_and_raises_event(self):
        user = _make_user()
        user.clear_domain_events()
        user.assign_roles(["TEACHER"])
        assert "TEACHER" in user.roles
        events = _events_of(user, UserRolesAssignedEvent)
        assert len(events) == 1
        assert "TEACHER" in events[0].payload["roles"]

    def test_assign_same_role_twice_is_idempotent(self):
        user = _make_user(role="STUDENT")
        user.clear_domain_events()
        user.assign_roles(["STUDENT"])
        assert _events_of(user, UserRolesAssignedEvent) == []
        assert user.roles.count("STUDENT") == 1

    def test_assign_roles_merges_with_existing(self):
        user = _make_user(role="STUDENT")
        user.clear_domain_events()
        user.assign_roles(["TEACHER"])
        assert set(user.roles) == {"STUDENT", "TEACHER"}

    def test_assign_roles_to_disabled_user_raises(self):
        user = _make_user()
        user.disable()
        user.clear_domain_events()
        with pytest.raises(DisabledUserCannotBeAssignedRolesError):
            user.assign_roles(["TEACHER"])


# ── revoke_roles() ──────────────────────────────────────────────────────


class TestUserRevokeRoles:
    def test_revoke_existing_role_updates_state_and_raises_event(self):
        user = _make_user(role="STUDENT")
        user.clear_domain_events()
        user.revoke_roles(["STUDENT"])
        assert "STUDENT" not in user.roles
        events = _events_of(user, UserRolesRevokedEvent)
        assert len(events) == 1
        assert "STUDENT" in events[0].payload["roles"]

    def test_revoke_non_existing_role_does_not_raise_event(self):
        user = _make_user()
        user.clear_domain_events()
        user.revoke_roles(["NONEXISTENT"])
        assert _events_of(user, UserRolesRevokedEvent) == []

    def test_revoke_partial_roles(self):
        user = _make_user()
        user.assign_roles(["STUDENT", "TEACHER"])
        user.clear_domain_events()
        user.revoke_roles(["STUDENT"])
        assert user.roles == ["TEACHER"]


# ── update_profile() ────────────────────────────────────────────────────


class TestUserUpdateProfile:
    def test_update_nickname_raises_event(self):
        user = _make_user()
        user.clear_domain_events()
        user.update_profile(nickname="newnick")
        assert user.nickname == "newnick"
        events = _events_of(user, UserProfileUpdatedEvent)
        assert len(events) == 1
        assert "nickname" in events[0].payload["changed"]

    def test_update_same_nickname_does_not_raise_event(self):
        user = _make_user(nickname="testuser")
        user.clear_domain_events()
        user.update_profile(nickname="testuser")
        assert _events_of(user, UserProfileUpdatedEvent) == []

    def test_update_multiple_fields_raises_single_event(self):
        user = _make_user()
        user.clear_domain_events()
        user.update_profile(nickname="newnick", bio="hello", org_name="MIT")
        events = _events_of(user, UserProfileUpdatedEvent)
        assert len(events) == 1
        changed = events[0].payload["changed"]
        assert "nickname" in changed
        assert "bio" in changed
        assert "org_name" in changed

    def test_update_no_changes_does_not_raise_event(self):
        user = _make_user(nickname="testuser")
        user.clear_domain_events()
        user.update_profile(nickname="testuser", bio=None)
        assert _events_of(user, UserProfileUpdatedEvent) == []

    def test_update_location_raises_event(self):
        user = _make_user()
        user.clear_domain_events()
        addr = Address(province="广东", city="深圳", district="南山")
        user.update_profile(location=addr)
        events = _events_of(user, UserProfileUpdatedEvent)
        assert len(events) == 1
        assert "location" in events[0].payload["changed"]

    def test_update_same_location_does_not_raise_event(self):
        user = _make_user()
        addr = Address(province="广东", city="深圳", district="南山")
        user.update_profile(location=addr)
        user.clear_domain_events()
        user.update_profile(location=Address(province="广东", city="深圳", district="南山"))
        assert _events_of(user, UserProfileUpdatedEvent) == []


# ── set_avatar() ────────────────────────────────────────────────────────


class TestUserSetAvatar:
    def test_set_new_avatar_raises_event(self):
        user = _make_user()
        user.clear_domain_events()
        user.set_avatar(avatar="blob-123")
        assert user.avatar == "blob-123"
        events = _events_of(user, UserProfileUpdatedEvent)
        assert len(events) == 1
        assert "avatar" in events[0].payload["changed"]

    def test_set_same_avatar_does_not_raise_event(self):
        user = _make_user()
        user.set_avatar(avatar="blob-123")
        user.clear_domain_events()
        user.set_avatar(avatar="blob-123")
        assert _events_of(user, UserProfileUpdatedEvent) == []


# ── set_password() ──────────────────────────────────────────────────────


class TestUserSetPassword:
    def test_set_valid_password_raises_event(self):
        user = _make_user()
        old_hash = user.hashed_password
        user.clear_domain_events()
        user.set_password(password="newpassword123")
        assert user.hashed_password != old_hash
        events = _events_of(user, UserPasswordSetEvent)
        assert len(events) == 1

    def test_set_weak_password_raises(self):
        user = _make_user()
        with pytest.raises(WeakPasswordError):
            user.set_password(password="123")

    def test_set_empty_password_raises(self):
        user = _make_user()
        with pytest.raises(WeakPasswordError):
            user.set_password(password="")


# ── link_account() / unlink_account() ───────────────────────────────────


class TestUserLinkedAccount:
    def _make_account(self, provider="wechat", uid="wx_123") -> LinkedAccount:
        return LinkedAccount(provider=provider, provider_account_id=uid)

    def test_link_new_account_raises_event(self):
        user = _make_user()
        user.clear_domain_events()
        account = self._make_account()
        user.link_account(account=account)
        assert len(user.linked_accounts) == 1
        events = _events_of(user, UserThirdPartyLinkedEvent)
        assert len(events) == 1
        assert events[0].payload["provider"] == "wechat"
        assert events[0].payload["external_uid"] == "wx_123"

    def test_link_duplicate_account_does_not_raise_event(self):
        user = _make_user()
        account = self._make_account()
        user.link_account(account=account)
        user.clear_domain_events()
        user.link_account(account=account)
        assert _events_of(user, UserThirdPartyLinkedEvent) == []
        assert len(user.linked_accounts) == 1

    def test_unlink_existing_account_raises_event(self):
        user = _make_user()
        account = self._make_account()
        user.link_account(account=account)
        user.clear_domain_events()
        user.unlink_account(provider="wechat", provider_account_id="wx_123")
        assert len(user.linked_accounts) == 0
        events = _events_of(user, UserThirdPartyUnlinkedEvent)
        assert len(events) == 1

    def test_unlink_non_existing_account_does_not_raise_event(self):
        user = _make_user()
        user.clear_domain_events()
        user.unlink_account(provider="wechat", provider_account_id="nonexistent")
        assert _events_of(user, UserThirdPartyUnlinkedEvent) == []
