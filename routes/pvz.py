"""
Модуль: routes/pvz
Назначение: Маршруты для работы с пунктами выдачи (ПВЗ)
Зависимости: from flask import Blueprint, jsonify, from db import get_db, from auth import login_required, get_current_user
Экспортирует: bp (Blueprint)
Безопасность: Управляет доступом к данным ПВЗ; содержит фильтрацию по ролям
"""

from flask import Blueprint, jsonify
from db import get_db
from auth import login_required, get_current_user

bp = Blueprint("pvz_bp", __name__, url_prefix="/api")

@bp.route("/pvz")
@login_required
def get_pvz_list():
    user = get_current_user()
    conn = get_db()
    if user["role"] == "operator":
        rows = conn.execute(
            "SELECT * FROM pvz WHERE pvz_id=?", (user["pvz_id"],)
        ).fetchall()
    elif user["role"] == "supervisor":
        rows = conn.execute(
            "SELECT * FROM pvz WHERE region=?", (user.get("region", ""),)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM pvz").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@bp.route("/pvz/<int:pvz_id>")
@login_required
def get_pvz(pvz_id):
    user = get_current_user()
    if user["role"] == "operator" and user["pvz_id"] != pvz_id:
        return jsonify({"error": "Нет доступа"}), 403
    conn = get_db()
    pvz = conn.execute("SELECT * FROM pvz WHERE pvz_id=?", (pvz_id,)).fetchone()
    schedule = conn.execute(
        "SELECT * FROM schedule WHERE pvz_id=? ORDER BY weekday", (pvz_id,)
    ).fetchall()
    conn.close()
    if not pvz:
        return jsonify({"error": "ПВЗ не найден"}), 404
    return jsonify({
        "pvz": dict(pvz),
        "schedule": [dict(s) for s in schedule]
    })

@bp.route("/regions")
@login_required
def get_regions():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT region FROM pvz ORDER BY region").fetchall()
    conn.close()
    return jsonify([r[0] for r in rows])