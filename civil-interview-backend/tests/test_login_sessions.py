import asyncio
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.session import Base
from app.models.entities import User
from app.core.security import create_access_token, get_current_user, get_password_hash
from app.services.auth_service import login_user, register_user
from app.schemas.common import RegisterRequest


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(username='session_test', hashed_password=get_password_hash('test-password')))
        session.commit()
        yield session


def current(db, token):
    return asyncio.run(get_current_user(token, db))


def test_clients_coexist_and_only_same_client_is_replaced(db):
    first = login_user(db, 'session_test', 'test-password', 'web')['access_token']
    mini = login_user(db, 'session_test', 'test-password', 'wechat')['access_token']
    assert current(db, first).username == current(db, mini).username == 'session_test'
    newer = login_user(db, 'session_test', 'test-password', 'web')['access_token']
    assert newer != first
    with pytest.raises(HTTPException) as error:
        current(db, first)
    assert error.value.status_code == 401 and '其他' in error.value.detail
    assert current(db, newer).username == current(db, mini).username


def test_wrong_password_does_not_replace_session_and_is_chinese(db):
    token = login_user(db, 'session_test', 'test-password')['access_token']
    with pytest.raises(HTTPException) as error:
        login_user(db, 'session_test', 'wrong-password')
    assert error.value.detail == '用户名或密码错误'
    assert current(db, token).username == 'session_test'


def test_legacy_token_expires_on_first_managed_login(db):
    old = create_access_token({'sub': 'session_test'})
    assert current(db, old).username == 'session_test'
    login_user(db, 'session_test', 'test-password')
    with pytest.raises(HTTPException):
        current(db, old)


def test_registration_rejects_invalid_username_with_readable_reason(db):
    with pytest.raises(HTTPException) as error:
        register_user(db, RegisterRequest(username='bad name', password='test-password'))
    assert error.value.status_code == 400 and '用户名' in error.value.detail
