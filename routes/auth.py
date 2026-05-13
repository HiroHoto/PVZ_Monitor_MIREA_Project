"""
Модуль: routes/auth
Назначение: Маршруты для авторизации пользователей
Зависимости: from flask import Blueprint, request, jsonify, session, from config import USERS, from auth import get_current_user
Экспортирует: bp (Blueprint)
Безопасность: Управляет сессиями и аутентификацией; содержит конфиденциальные данные в запросах
"""

from flask import Blueprint, request, jsonify, session
from config import USERS
from auth import get_current_user

bp = Blueprint("auth_bp", __name__, url_prefix="/api")

@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    user = USERS.get(username)
    if not user or user["password"] != password:
        return jsonify({"error": "Неверный логин или пароль"}), 401
    session["user"] = username
    return jsonify({
        "ok": True,
        "username": username,
        "role": user["role"],
        "name": user["name"]
    })

@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

@bp.route("/me")
def me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Не авторизован"}), 401
    return jsonify(user)