"""
Модуль: routes/reports
Назначение: Маршруты для генерации отчётов и экспорта данных
Зависимости: from flask import Blueprint, request, jsonify, send_file, from db import get_db, from auth import login_required, role_required, get_current_user, import csv, io
Экспортирует: bp (Blueprint)
Безопасность: Управляет доступом к аналитическим данным; содержит логику экспорта CSV
"""

from flask import Blueprint, request, jsonify, send_file
from db import get_db
from auth import login_required, role_required, get_current_user
import csv
import io

bp = Blueprint("report_bp", __name__, url_prefix="/api")

@bp.route("/report/load")
@login_required
def report_load():
    """
    Отчёт «Загрузка ПВЗ» по часам/дням.
    Возвращает: pvz_id, date, hour, ops_per_hour, capacity_per_hour, load, overloaded
    """
    user = get_current_user()
    conn = get_db()

    conditions = ["1=1"]
    params = []

    # Role-based filtering
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

    region_filter = request.args.get("region")
    if region_filter:
        conditions.append("p.region=?")
        params.append(region_filter)

    type_filter = request.args.get("type")
    if type_filter and type_filter in ("in","out","return"):
        conditions.append("o.type=?")
        params.append(type_filter)

    date_from = request.args.get("date_from", "2025-03-01")
    date_to   = request.args.get("date_to",   "2025-03-31")
    conditions.append("DATE(o.ts) BETWEEN ? AND ?")
    params.extend([date_from, date_to])

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            o.pvz_id,
            p.address,
            p.region,
            p.capacity_per_hour,
            DATE(o.ts)              AS date,
            CAST(strftime('%H', o.ts) AS INTEGER) AS hour,
            COUNT(*)                AS ops_per_hour,
            SUM(CASE WHEN o.type='in'     THEN 1 ELSE 0 END) AS ops_in,
            SUM(CASE WHEN o.type='out'    THEN 1 ELSE 0 END) AS ops_out,
            SUM(CASE WHEN o.type='return' THEN 1 ELSE 0 END) AS ops_return
        FROM operations o
        JOIN pvz p ON o.pvz_id = p.pvz_id
        {where}
        GROUP BY o.pvz_id, date, hour
        ORDER BY o.pvz_id, date, hour
    """
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    result = []
    total_overloaded = 0
    total_intervals = 0

    for r in rows:
        cap = r["capacity_per_hour"]
        ops = r["ops_per_hour"]
        load = round(ops / cap, 4) if cap else 0
        overloaded = load > 1.0
        if overloaded:
            total_overloaded += 1
        total_intervals += 1
        result.append({
            "pvz_id": r["pvz_id"],
            "address": r["address"],
            "region": r["region"],
            "date": r["date"],
            "hour": r["hour"],
            "ops_per_hour": ops,
            "ops_in": r["ops_in"],
            "ops_out": r["ops_out"],
            "ops_return": r["ops_return"],
            "capacity_per_hour": cap,
            "load": load,
            "load_pct": round(load * 100, 1),
            "overloaded": overloaded
        })

    # KPI
    loads = [r["load"] for r in result]
    # Peak hours: 12-14, 18-20
    peak = [r["load"] for r in result if r["hour"] in (12,13,18,19)]
    avg_peak_load = round(sum(peak)/len(peak)*100, 1) if peak else 0
    avg_load = round(sum(loads)/len(loads)*100, 1) if loads else 0
    overload_share = round(total_overloaded/total_intervals*100, 1) if total_intervals else 0

    return jsonify({
        "data": result,
        "kpi": {
            "avg_load_pct": avg_load,
            "avg_peak_load_pct": avg_peak_load,
            "overload_share_pct": overload_share,
            "total_intervals": total_intervals,
            "total_overloaded": total_overloaded
        }
    })

@bp.route("/report/heatmap")
@login_required
def report_heatmap():
    """Тепловая карта: средняя загрузка по часу × день недели для выбранного ПВЗ."""
    user = get_current_user()
    pvz_id   = request.args.get("pvz_id")
    date_from = request.args.get("date_from", "2025-03-01")
    date_to   = request.args.get("date_to",   "2025-03-31")

    if user["role"] == "operator":
        pvz_id = user["pvz_id"]
    elif not pvz_id:
        conn = get_db()
        if user["role"] == "supervisor":
            row = conn.execute("SELECT pvz_id FROM pvz WHERE region=?", (user.get("region",""),)).fetchone()
        else:
            row = conn.execute("SELECT pvz_id FROM pvz").fetchone()
        conn.close()
        pvz_id = row[0] if row else 1

    conn = get_db()
    # role guard
    if user["role"] == "supervisor":
        allowed = {r[0] for r in conn.execute(
            "SELECT pvz_id FROM pvz WHERE region=?", (user.get("region",""),)
        ).fetchall()}
        if int(pvz_id) not in allowed:
            conn.close()
            return jsonify({"error": "Нет доступа"}), 403

    rows = conn.execute("""
        SELECT
            CAST(strftime('%w', ts) AS INTEGER) AS dow,
            CAST(strftime('%H', ts) AS INTEGER) AS hour,
            COUNT(*) AS ops
        FROM operations
        WHERE pvz_id=? AND DATE(ts) BETWEEN ? AND ?
        GROUP BY dow, hour
    """, (pvz_id, date_from, date_to)).fetchall()

    cap = conn.execute("SELECT capacity_per_hour FROM pvz WHERE pvz_id=?", (pvz_id,)).fetchone()
    cap = cap[0] if cap else 1
    conn.close()

    # dow: 0=Sun in SQLite strftime('%w'), remap to 0=Mon
    DOW_MAP = {0:6, 1:0, 2:1, 3:2, 4:3, 5:4, 6:5}  # sqlite Sun=0 → Mon=0
    DAY_NAMES = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]

    matrix = {}
    for r in rows:
        d = DOW_MAP[r["dow"]]
        h = r["hour"]
        load = round(r["ops"] / cap * 100, 1)
        matrix[f"{d}_{h}"] = {"day": d, "hour": h, "load_pct": load, "ops": r["ops"]}

    return jsonify({
        "pvz_id": pvz_id,
        "capacity_per_hour": cap,
        "day_names": DAY_NAMES,
        "matrix": list(matrix.values())
    })

@bp.route("/export/csv")
@login_required
def export_csv():
    # Re-use report_load logic but return CSV
    user = get_current_user()
    conn = get_db()

    date_from = request.args.get("date_from", "2025-03-01")
    date_to   = request.args.get("date_to",   "2025-03-31")
    pvz_filter  = request.args.get("pvz_id")
    type_filter = request.args.get("type")
    region_filter = request.args.get("region")

    conditions = ["DATE(o.ts) BETWEEN ? AND ?"]
    params = [date_from, date_to]

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

    if pvz_filter:
        conditions.append("o.pvz_id=?")
        params.append(int(pvz_filter))
    if type_filter and type_filter in ("in","out","return"):
        conditions.append("o.type=?")
        params.append(type_filter)
    if region_filter:
        conditions.append("p.region=?")
        params.append(region_filter)

    where = "WHERE " + " AND ".join(conditions)
    rows = conn.execute(f"""
        SELECT o.pvz_id, p.address, p.capacity_per_hour,
               DATE(o.ts) AS date,
               CAST(strftime('%H', o.ts) AS INTEGER) AS hour,
               COUNT(*) AS ops
        FROM operations o JOIN pvz p ON o.pvz_id=p.pvz_id
        {where}
        GROUP BY o.pvz_id, date, hour
        ORDER BY o.pvz_id, date, hour
    """, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["pvz_id","address","date","hour","ops","capacity","load"])
    for r in rows:
        cap = r["capacity_per_hour"]
        ops = r["ops"]
        load = round(ops/cap, 4) if cap else 0
        writer.writerow([r["pvz_id"], r["address"], r["date"], r["hour"], ops, cap, load])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"pvz_load_{date_from}_{date_to}.csv"
    )

@bp.route("/errors")
@role_required("analyst", "supervisor")
def get_errors():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM error_log ORDER BY logged_at DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])