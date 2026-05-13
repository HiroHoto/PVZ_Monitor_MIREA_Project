"""
Модуль: config
Назначение: Централизованное хранение конфигурации приложения и демо-пользователей
Зависимости: нет (только stdlib os)
Экспортирует: SECRET_KEY, BASE_DIR, DB_PATH, DATA_DIR, USERS
Безопасность: Содержит пароли демо-пользователей и SECRET_KEY в открытом виде;
              в продакшене заменить на переменные окружения
"""

import os

SECRET_KEY = "pvz-secret-key-2025"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "pvz.db")
DATA_DIR = os.path.join(BASE_DIR, "data")

# ─── DEMO USERS (roles) ───────────────────────────────────────────────────────
USERS = {
    "operator1":   {"password": "op1pass",  "role": "operator",   "pvz_id": 1, "name": "Иванов А."},
    "operator2":   {"password": "op2pass",  "role": "operator",   "pvz_id": 2, "name": "Петрова Б."},
    "supervisor1": {"password": "suppass",  "role": "supervisor", "region": "Центральный", "name": "Козлов В."},
    "analyst1":    {"password": "anapass",  "role": "analyst",    "name": "Смирнова Г."},
}