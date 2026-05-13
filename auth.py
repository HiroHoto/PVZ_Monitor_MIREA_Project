"""
Модуль: auth
Назначение: Декораторы и helpers для авторизации пользователей
Зависимости: from config import USERS, from flask import session, jsonify, functools.wraps
Экспортирует: login_required(), role_required(), get_current_user()
Безопасность: Управляет сессиями пользователей; содержит логику проверки ролей
"""

from functools import wraps
from flask import session, jsonify
from config import USERS

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Требуется авторизация"}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user" not in session:
                return jsonify({"error": "Требуется авторизация"}), 401
            user = USERS.get(session["user"])
            if not user or user["role"] not in roles:
                return jsonify({"error": "Недостаточно прав"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_current_user():
    username = session.get("user")
    if not username:
        return None
    u = USERS.get(username, {})
    return {"username": username, **u}