def test_create_operation_invalid_type(client):
    """Проверка правила валидации №4: Тип операции"""
    # Сначала логинимся
    client.post('/api/login', json={"username": "operator1", "password": "op1pass"})
    
    # Отправляем некорректный тип
    response = client.post('/api/operations', json={
        "pvz_id": 1,
        "type": "unknown_action",
        "ts": "2026-05-13T15:00:00"
    })
    assert response.status_code == 400
    assert "Тип операции" in response.json['error']

def test_create_operation_outside_schedule(client):
    """Проверка правила валидации №3: Рабочие часы"""
    client.post('/api/login', json={"username": "operator1", "password": "op1pass"})
    
    # Пытаемся создать операцию в 3 часа ночи
    response = client.post('/api/operations', json={
        "pvz_id": 1,
        "type": "in",
        "ts": "2026-05-13T03:00:00"
    })
    assert response.status_code == 400
    assert "ts:" in response.json['error']
