import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user, get_password_hash
from app.db.session import Base
from app.models.entities import PasswordResetCase, User
from app.schemas.common import PasswordResetRequest, PasswordResetVerifyRequest, PasswordResetConfirmRequest, WechatMiniProgramAccountRequest, RegisterRequest
from app.services.auth_service import request_password_reset, issue_password_reset_code, verify_password_reset, confirm_password_reset, login_user, setup_wechat_miniprogram_account, register_user

ADMIN = SimpleNamespace(username='admin', isAdmin=True, permissions={})


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([User(username='alice', hashed_password=get_password_hash('old-password')), User(username='wxmp_test', hashed_password='unused')])
        session.commit()
        yield session
    engine.dispose()


def issue(db):
    request_password_reset(db, PasswordResetRequest(username='alice', contact='acceptance@example.invalid'))
    return issue_password_reset_code(db, ADMIN, db.query(PasswordResetCase).one().id)['code']


@pytest.mark.parametrize('managed', [True, False])
def test_reset_revokes_both_clients_and_legacy_tokens_and_code_is_single_use(db, managed):
    legacy = create_access_token({'sub': 'alice'})
    tokens = [legacy]
    if managed:
        tokens += [login_user(db, 'alice', 'old-password', client)['access_token'] for client in ['web', 'wechat']]
    code = issue(db)
    verify_password_reset(db, PasswordResetVerifyRequest(username='alice', code=code))
    request = PasswordResetConfirmRequest(username='alice', code=code, newPassword='new-password')
    confirm_password_reset(db, request)
    for token in tokens:
        with pytest.raises(HTTPException) as error:
            asyncio.run(get_current_user(token, db))
        assert error.value.status_code == 401
    with pytest.raises(HTTPException):
        confirm_password_reset(db, request)
    with pytest.raises(HTTPException):
        login_user(db, 'alice', 'old-password')
    fresh = login_user(db, 'alice', 'new-password')
    assert fresh['userId'] == str(db.query(User).filter_by(username='alice').one().id)
    assert asyncio.run(get_current_user(fresh['access_token'], db)).username == 'alice'


def test_expired_and_locked_codes_require_admin_reissue(db, monkeypatch):
    values = iter([123456, 234567, 345678])
    monkeypatch.setattr('app.services.auth_service.secrets.randbelow', lambda _: next(values))
    first = issue(db)
    case = db.query(PasswordResetCase).one()
    case.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    with pytest.raises(HTTPException):
        verify_password_reset(db, PasswordResetVerifyRequest(username='alice', code=first))
    second = issue_password_reset_code(db, ADMIN, case.id)['code']
    for _ in range(8):
        with pytest.raises(HTTPException):
            verify_password_reset(db, PasswordResetVerifyRequest(username='alice', code=first))
    assert case.status == 'locked'
    with pytest.raises(HTTPException):
        verify_password_reset(db, PasswordResetVerifyRequest(username='alice', code=second))
    third = issue_password_reset_code(db, ADMIN, case.id)['code']
    assert third != second and case.failed_attempts == 0
    assert verify_password_reset(db, PasswordResetVerifyRequest(username='alice', code=third))['success']


@pytest.mark.parametrize('username', ['有中文', 'bad name', 'a/b', 'wxmp_reserved', 'WXMP_reserved'])
def test_registration_and_wechat_setup_share_character_and_reserved_prefix_rules(db, username):
    with pytest.raises(HTTPException) as error:
        register_user(db, RegisterRequest(username=username, password='new-password'))
    assert error.value.status_code == 400
    with pytest.raises(HTTPException) as error:
        setup_wechat_miniprogram_account(db, SimpleNamespace(username='wxmp_test'), WechatMiniProgramAccountRequest(username=username, password='new-password'))
    assert error.value.status_code == 400
    assert db.query(User).filter_by(username='wxmp_test').one()


def test_wechat_conflict_gives_action_without_merging_identity(db):
    alice_id = db.query(User).filter_by(username='alice').one().id
    with pytest.raises(HTTPException) as error:
        setup_wechat_miniprogram_account(db, SimpleNamespace(username='wxmp_test'), WechatMiniProgramAccountRequest(username='alice', password='new-password'))
    assert error.value.status_code == 409 and '登录' in error.value.detail
    assert db.query(User).filter_by(username='alice').one().id == alice_id
    assert db.query(User).count() == 2
