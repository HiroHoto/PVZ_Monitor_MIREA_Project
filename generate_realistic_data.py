import random
from datetime import datetime, timedelta
import json
import numpy as np
from scipy.stats import poisson

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

def generate_ops_for_pvz(pvz, start_date, end_date, capacity):
    """
    Генерирует операции для одного ПВЗ на заданный период.
    """
    ops = []
    current_id = 1
    
    HOUR_WEIGHTS = {
        9: 0.5, 10: 0.7, 11: 0.9, 12: 1.3, 13: 1.5,
        14: 1.2, 15: 0.8, 16: 0.7, 17: 0.9, 18: 1.6,
        19: 1.4, 20: 0.6
    }
    TYPE_DIST = {"out": 0.60, "in": 0.28, "return": 0.12}
    WEEKEND_FACTOR = {5: 0.75, 6: 0.55}  # Суббота, Воскресенье
    
    date = start_date
    while date <= end_date:
        weekday = date.weekday()
        factor = WEEKEND_FACTOR.get(weekday, 1.0)
        
        # Центральные ПВЗ загружены сильнее
        location_factor = 1.3 if pvz["region"] == "Центральный" else 0.85
        
        for hour, weight in HOUR_WEIGHTS.items():
            expected = capacity * factor * location_factor * weight
            actual_count = poisson.rvs(expected) if expected > 0 else 0
            
            for _ in range(actual_count):
                op_type = weighted_choice(TYPE_DIST)
                minute = cluster_aware_minute(hour, op_type)
                ts = datetime(date.year, date.month, date.day, hour, minute)
                ops.append({
                    "op_id": current_id,
                    "pvz_id": pvz["pvz_id"],
                    "ts": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "type": op_type
                })
                current_id += 1
        
        date += timedelta(days=1)
    
    return ops

def main():
    with open("data/pvz.json", encoding="utf-8") as f:
        pvz_list = json.load(f)
    
    all_ops = []
    start_date = datetime(2025, 3, 1)
    end_date = datetime(2025, 3, 31)
    
    for pvz in pvz_list:
        ops = generate_ops_for_pvz(
            pvz=pvz,
            start_date=start_date,
            end_date=end_date,
            capacity=pvz["capacity_per_hour"]
        )
        all_ops.extend(ops)
    
    # Сохранение в файл
    with open("data/operations_new.json", "w", encoding="utf-8") as f:
        json.dump(all_ops, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()