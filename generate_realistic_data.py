import random
from datetime import datetime, timedelta
import json
import numpy as np
from scipy.stats import poisson

# ─── КОНСТАНТА СРЕДНЕЙ ЗАГРУЗКИ ──────────────────────────────────────────────
BASE_UTILIZATION = 0.80  # средняя загрузка ~80% от capacity

# ─── СПРАВОЧНИК ТОВАРОВ И ВЕСОВ ──────────────────────────────────────────────
PRODUCTS_BY_TYPE = {
    "in": [
        ("Смартфон",       (0.15, 0.50)),
        ("Ноутбук",        (1.50, 3.50)),
        ("Планшет",        (0.40, 0.90)),
        ("Наушники",       (0.20, 0.45)),
        ("Книга",          (0.20, 1.50)),
        ("Одежда",         (0.30, 2.00)),
        ("Косметика",      (0.10, 0.80)),
        ("Обувь",          (0.50, 1.50)),
        ("Игрушка",        (0.15, 2.00)),
        ("Бытовая химия",  (0.50, 5.00)),
        ("Продукты",       (0.50, 10.00)),
        ("Мебель",         (5.00, 50.00)),
        ("Аксессуар",      (0.05, 0.30)),
    ],
    "out": [
        ("Смартфон",       (0.15, 0.50)),
        ("Ноутбук",        (1.50, 3.50)),
        ("Планшет",        (0.40, 0.90)),
        ("Наушники",       (0.20, 0.45)),
        ("Книга",          (0.20, 1.50)),
        ("Одежда",         (0.30, 2.00)),
        ("Косметика",      (0.10, 0.80)),
        ("Обувь",          (0.50, 1.50)),
        ("Аксессуар",      (0.05, 0.30)),
    ],
    "return": [
        ("Смартфон",       (0.15, 0.50)),
        ("Ноутбук",        (1.50, 3.50)),
        ("Одежда",         (0.30, 2.00)),
        ("Обувь",          (0.50, 1.50)),
        ("Косметика",      (0.10, 0.80)),
        ("Книга",          (0.20, 1.50)),
    ]
}

def weighted_choice(weights):
    """
    Выбирает случайный элемент по весам.
    weights: {"key": weight, ...}
    """
    population = list(weights.keys())
    weights = list(weights.values())
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for c, w in zip(population, weights):
        if upto + w >= r:
            return c
        upto += w
    return population[-1]

def cluster_aware_minute(hour, op_type):
    """
    Генерирует минуты с учётом кластеризации.
    """
    if op_type == "in":
        # Приёмка — пачками по 5–15 мин
        return random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    elif op_type == "out":
        # Выдача — волны по 1–3 мин
        return random.choice([0, 1, 2, 3, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    else:
        # Возвраты — одиночные
        return random.randint(0, 59)

def generate_ops_for_pvz(pvz, start_date, end_date, capacity, schedule):
    """
    Генерирует операции для одного ПВЗ на заданный период.
    schedule: dict {weekday: (open_hour, close_hour)} для данного ПВЗ.
    Если weekday нет в schedule — ПВЗ не работает в этот день.
    """
    ops = []
    
    HOUR_WEIGHTS = {
        9: 0.5, 10: 0.7, 11: 0.9, 12: 1.3, 13: 1.5,
        14: 1.2, 15: 0.8, 16: 0.7, 17: 0.9, 18: 1.6,
        19: 1.4, 20: 0.6
    }
    max_weight = max(HOUR_WEIGHTS.values())  # 1.6
    TYPE_DIST = {"out": 0.60, "in": 0.28, "return": 0.12}
    WEEKEND_FACTOR = {5: 0.75, 6: 0.55}  # Суббота, Воскресенье
    
    date = start_date
    while date <= end_date:
        weekday = date.weekday()
        
        # Пропуск дней, когда ПВЗ не работает
        if weekday not in schedule:
            date += timedelta(days=1)
            continue
        
        oh, ch = schedule[weekday]  # open_hour, close_hour
        factor = WEEKEND_FACTOR.get(weekday, 1.0)
        
        # Центральные ПВЗ загружены сильнее
        location_factor = 1.15 if pvz["region"] == "Центральный" else 1.0
        
        for hour, weight in HOUR_WEIGHTS.items():
            # Пропуск часов вне расписания ПВЗ
            if hour < oh or hour >= ch:
                continue
            
            norm_weight = weight / max_weight
            expected = capacity * factor * location_factor * norm_weight * BASE_UTILIZATION
            actual_count = poisson.rvs(expected) if expected > 0 else 0
            
            for _ in range(actual_count):
                op_type = weighted_choice(TYPE_DIST)
                minute = cluster_aware_minute(hour, op_type)
                ts = datetime(date.year, date.month, date.day, hour, minute)
                # Выбор товара и веса
                product_choices = PRODUCTS_BY_TYPE[op_type]
                product_name, (w_min, w_max) = random.choice(product_choices)
                weight_kg = round(random.uniform(w_min, w_max), 2)
                ops.append({
                    "pvz_id": pvz["pvz_id"],
                    "ts": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "type": op_type,
                    "product_name": product_name,
                    "weight_kg": weight_kg
                })
        
        date += timedelta(days=1)
    
    return ops

def main():
    with open("data/pvz.json", encoding="utf-8") as f:
        pvz_list = json.load(f)
    
    # Загрузка расписания и построение lookup: {pvz_id: {weekday: (open_hour, close_hour)}}
    with open("data/schedule.json", encoding="utf-8") as f:
        schedule_raw = json.load(f)
    
    schedule_lookup = {}
    for entry in schedule_raw:
        pvz_id = entry["pvz_id"]
        weekday = entry["weekday"]
        oh = int(entry["open_time"].split(":")[0])
        ch = int(entry["close_time"].split(":")[0])
        schedule_lookup.setdefault(pvz_id, {})[weekday] = (oh, ch)
    
    all_ops = []
    start_date = datetime(2025, 3, 1)
    end_date = datetime(2025, 3, 31)
    
    for pvz in pvz_list:
        pvz_schedule = schedule_lookup.get(pvz["pvz_id"], {})
        ops = generate_ops_for_pvz(
            pvz=pvz,
            start_date=start_date,
            end_date=end_date,
            capacity=pvz["capacity_per_hour"],
            schedule=pvz_schedule
        )
        all_ops.extend(ops)
    
    # Назначаем глобально уникальные op_id один раз после сбора всех операций
    for i, op in enumerate(all_ops, start=1):
        op["op_id"] = i
    
    # Сохранение в файл (operations.json — подхватывается init_db)
    with open("data/operations.json", "w", encoding="utf-8") as f:
        json.dump(all_ops, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()