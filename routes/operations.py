"""
Модуль: routes/operations
Назначение: Маршруты для работы с операциями (CRUD)
Зависимости: from flask import Blueprint, request, jsonify, from db import get_db, from auth import login_required, role_required, get_current_user, from datetime import datetime
Экспортирует: bp (Blueprint)
Безопасность: Управляет доступом к данным операций; содержит фильтрацию по ролям и валидацию данных
"""

from flask import Blueprint, request, jsonify
from db import get_db
from auth import login_required, role_required, get_current_user
from datetime import datetime

bp = Blueprint("ops_bp", __name__, url_prefix="/api")

@bp.route("/operations", methods=["GET"])
@login_required
def get_operations():
    user = get_current_user()
    conn = get_db()

    conditions = []
    params = []

    if user["role"] == "operator":
        conditions.append("o.pvz_id=?")
        params.append(user["pvz_id"])
    elif user["role"] == "supervisor":
        pvz_ids = [r[0] for r in conn.execute(
            "SELECT pvz_id FROM pvz WHERE region=?", (user.get("region",""),)
        ).fetchall()]
        if pvz_ids:
            conditions.append(f"o.pvz_id IN ({','.join('?'*len(pvz_ids))})")
            params.extend(pvz_ids)

    pvz_filter = request.args.get("pvz_id")
    if pvz_filter:
        conditions.append("o.pvz_id=?")
        params.append(int(pvz_filter))

    type_filter = request.args.get("type")
    if type_filter and type_filter in ("in","out","return"):
        conditions.append("o.type=?")
        params.append(type_filter)

    date_from = request.args.get("date_from")
    date_to   = request.args.get("date_to")
    if date_from:
        conditions.append("DATE(o.ts)>=?")
        params.append(date_from)
    if date_to:
        conditions.append("DATE(o.ts)<=?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    limit = int(request.args.get("limit", 200))
    offset = int(request.args.get("offset", 0))

    sql = f"""
        SELECT o.op_id, o.pvz_id, p.address, o.ts, o.type
        FROM operations o JOIN pvz p ON o.pvz_id=p.pvz_id
        {where}
        ORDER BY o.ts DESC
        LIMIT ? OFFSET ?
    """
    total_sql = f"SELECT COUNT(*) FROM operations o JOIN pvz p ON o.pvz_id=p.pvz_id {where}"
    total = conn.execute(total_sql, params).fetchone()[0]
    rows = conn.execute(sql, params + [limit, offset]).fetchall()
    conn.close()
    return jsonify({
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [dict(r) for r in rows]
    })

@bp.route("/operations", methods=["POST"])
@role_required("operator", "analyst")
def create_operation():
    user = get_current_user()
    data = request.get_json()
    pvz_id  = data.get("pvz_id")
    ts_str  = data.get("ts")
    op_type = data.get("type")

    # Validate inputs
    if not all([pvz_id, ts_str, op_type]):
        return jsonify({"error": "Необходимы pvz_id, ts, type"}), 400
    if op_type not in ("in", "out", "return"):
        return jsonify({"error": "Тип операции должен быть: in, out, return"}), 400

    # Operator can only add to their own pvz
    if user["role"] == "operator" and user["pvz_id"] != pvz_id:
        return jsonify({"error": "Нет доступа к данному ПВЗ"}), 403

    try:
        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({"error": "Формат ts: YYYY-MM-DD HH:MM:SS"}), 400

    conn = get_db()
    pvz = conn.execute("SELECT * FROM pvz WHERE pvz_id=?", (pvz_id,)).fetchone()
    if not pvz:
        conn.close()
        return jsonify({"error": f"ПВЗ {pvz_id} не найден"}), 400

    weekday = ts.weekday()
    sched = conn.execute(
        "SELECT open_time, close_time FROM schedule WHERE pvz_id=? AND weekday=?",
        (pvz_id, weekday)
    ).fetchone()

    if not sched:
        reason = f"ПВЗ {pvz_id} не работает в этот день недели ({weekday})"
        conn.execute(
            "INSERT INTO error_log(pvz_id,ts,op_type,reason) VALUES(?,?,?,?)",
            (pvz_id, ts_str, op_type, reason)
        )
        conn.commit()
        conn.close()
        return jsonify({"error": reason}), 400

    oh = int(sched["open_time"].split(":")[0])
    ch = int(sched["close_time"].split(":")[0])
    if not (oh <= ts.hour < ch):
        reason = f"Время {ts_str} вне рабочих часов ПВЗ {pvz_id} ({oh}:00-{ch}:00)"
        conn.execute(
            "INSERT INTO error_log(pvz_id,ts,op_type,reason) VALUES(?,?,?,?)",
            (pvz_id, ts_str, op_type, reason)
        )
        conn.commit()
        conn.close()
        return jsonify({"error": reason}), 400

    cur = conn.execute(
        "INSERT INTO operations(pvz_id,ts,type) VALUES(?,?,?)",
        (pvz_id, ts_str, op_type)
    )
    conn.commit()
    op_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "op_id": op_id}), 201