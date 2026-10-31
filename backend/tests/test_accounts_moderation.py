"""Email verification, password reset, pro applications, moderator user tools, audit log."""

import re

import pytest

from app.core.email import OUTBOX
from app.modules.accounts.models import Role, UserStatus
from tests.conftest import csrf, register
from tests.test_community import create, login_as


@pytest.fixture(autouse=True)
def clear_outbox():
    OUTBOX.clear()


def link_token(kind: str) -> str:
    body = OUTBOX[-1].get_content()
    m = re.search(rf"/{kind}\?token=([\w-]+)", body)
    assert m, body
    return m.group(1)


def test_register_sends_verification_and_link_verifies(client):
    register(client)
    assert client.get("/api/v1/me").json()["email_verified"] is False
    assert OUTBOX[-1]["To"] == "tech@example.com"
    token = link_token("verify-email")
    r = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 200 and r.json()["email_verified"] is True
    again = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert again.status_code == 400 and again.json()["error"]["code"] == "token_invalid"  # one-time


def test_resend_verification(client):
    register(client)
    OUTBOX.clear()
    assert client.post("/api/v1/auth/verify-email/request", headers=csrf(client)).status_code == 202
    assert len(OUTBOX) == 1


def test_password_reset_flow(client):
    register(client)
    client.cookies.clear()
    OUTBOX.clear()
    r = client.post("/api/v1/auth/forgot-password", json={"email": "TECH@example.com"})
    assert r.status_code == 202
    token = link_token("reset-password")
    assert (
        client.post(
            "/api/v1/auth/reset-password", json={"token": token, "password": "short"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/auth/reset-password", json={"token": token, "password": "brand-new-password"}
        ).status_code
        == 204
    )
    old = client.post(
        "/api/v1/auth/login",
        json={"email": "tech@example.com", "password": "correct-horse-battery"},
    )
    assert old.status_code == 401
    new = client.post(
        "/api/v1/auth/login", json={"email": "tech@example.com", "password": "brand-new-password"}
    )
    assert new.status_code == 200 and new.json()["email_verified"] is True
    # The link only works once
    assert (
        client.post(
            "/api/v1/auth/reset-password", json={"token": token, "password": "another-password"}
        ).status_code
        == 400
    )


def test_forgot_password_doesnt_reveal_accounts(client):
    r = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 202
    assert r.json() == {"status": "sent_if_account_exists"}
    assert OUTBOX == []


def test_pro_application_approved(client, db_session_factory):
    login_as(client, db_session_factory, "tech@example.com")
    assert client.get("/api/v1/pro-requests/mine").json() is None
    short = client.post(
        "/api/v1/pro-requests", json={"statement": "trust me"}, headers=csrf(client)
    )
    assert short.status_code == 422
    statement = "ASE Master Technician, 12 years at an independent shop, L1 certified."
    assert (
        client.post(
            "/api/v1/pro-requests", json={"statement": statement}, headers=csrf(client)
        ).status_code
        == 201
    )
    dup = client.post("/api/v1/pro-requests", json={"statement": statement}, headers=csrf(client))
    assert dup.json()["error"]["code"] == "pro_request_pending"
    assert client.get("/api/v1/mod/pro-requests").status_code == 403

    client.cookies.clear()
    login_as(client, db_session_factory, "mod@example.com", Role.moderator)
    req = client.get("/api/v1/mod/pro-requests").json()[0]
    assert req["statement"] == statement
    client.post(
        f"/api/v1/mod/pro-requests/{req['id']}/approve",
        json={"note": "Checked ASE ID"},
        headers=csrf(client),
    )
    log = client.get("/api/v1/mod/log").json()
    assert log[0]["action"] == "pro_request_approved" and log[0]["reason"] == "Checked ASE ID"

    client.cookies.clear()
    client.post(
        "/api/v1/auth/login",
        json={"email": "tech@example.com", "password": "correct-horse-battery"},
    )
    me = client.get("/api/v1/me").json()
    assert me["role"] == "pro" and me["status"] == "active"
    assert client.get("/api/v1/pro-requests/mine").json()["status"] == "approved"


def test_moderator_can_suspend_user_and_it_takes_effect(client, db_session_factory):
    login_as(client, db_session_factory, "spammer@example.com")
    spammer_id = client.get("/api/v1/me").json()["id"]
    spammer_cookies = dict(client.cookies)
    client.cookies.clear()
    login_as(client, db_session_factory, "mod@example.com", Role.moderator)
    found = client.get("/api/v1/mod/users", params={"q": "spammer"}).json()
    assert [u["id"] for u in found] == [spammer_id]
    no_reason = client.post(
        f"/api/v1/mod/users/{spammer_id}/status", json={"status": "banned"}, headers=csrf(client)
    )
    assert no_reason.status_code == 422
    r = client.post(f"/api/v1/mod/users/{spammer_id}/status", json={"status": "banned", "reason": "Spam links"},
                    headers=csrf(client))  # fmt: skip
    assert r.json()["status"] == "banned"
    assert client.get("/api/v1/mod/log").json()[0]["action"] == "user_banned"

    client.cookies.clear()
    client.cookies.update(spammer_cookies)
    assert client.get("/api/v1/me").status_code == 401  # logged out everywhere
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "spammer@example.com", "password": "correct-horse-battery"},
    )
    assert login.json()["error"]["code"] == "account_disabled"


def test_moderators_cannot_act_on_peers_or_themselves(client, db_session_factory):
    login_as(client, db_session_factory, "mod2@example.com", Role.moderator)
    mod2 = client.get("/api/v1/me").json()["id"]
    client.cookies.clear()
    login_as(client, db_session_factory, "mod@example.com", Role.moderator)
    me = client.get("/api/v1/me").json()["id"]
    body = {"status": "banned", "reason": "test"}
    assert (
        client.post(f"/api/v1/mod/users/{mod2}/status", json=body, headers=csrf(client)).status_code
        == 403
    )
    assert (
        client.post(f"/api/v1/mod/users/{me}/status", json=body, headers=csrf(client)).status_code
        == 409
    )
    # Only admins change roles
    assert client.post(f"/api/v1/admin/users/{mod2}/role", json={"role": "user", "reason": "x y z"},
                       headers=csrf(client)).status_code == 403  # fmt: skip


def test_admin_sets_roles(client, db_session_factory):
    login_as(client, db_session_factory, "joe@example.com")
    joe = client.get("/api/v1/me").json()["id"]
    client.cookies.clear()
    login_as(client, db_session_factory, "admin@example.com", Role.admin)
    r = client.post(f"/api/v1/admin/users/{joe}/role", json={"role": "moderator", "reason": "Trusted helper"},
                    headers=csrf(client))  # fmt: skip
    assert r.json()["role"] == "moderator" and r.json()["status"] == "active"


def test_guide_moderation_is_logged(client, db_session_factory):
    login_as(client, db_session_factory, "mod@example.com", Role.moderator)
    eid = create(client).json()["id"]
    client.post(f"/api/v1/mod/entries/{eid}/hide", headers=csrf(client))
    assert client.get("/api/v1/mod/log").json()[0]["action"] == "entry_hide"


def test_verified_email_requirement_switch(client, db_session_factory, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "require_verified_email", True)
    login_as(client, db_session_factory, "new@example.com", status=UserStatus.active)
    r = create(client)
    assert r.status_code == 403 and r.json()["error"]["code"] == "email_not_verified"
    client.post("/api/v1/auth/verify-email", json={"token": link_token("verify-email")})
    assert create(client).status_code == 201
