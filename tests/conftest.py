import pytest
from app import create_app
from db import init_db
import os

@pytest.fixture
def app():
    # Используем тестовую БД в памяти или временный файл
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    
    with app.app_context():
        init_db()
    
    yield app

@pytest.fixture
def client(app):
    return app.test_client()