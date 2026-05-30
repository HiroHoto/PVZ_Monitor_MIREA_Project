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

def test_create_operation_with_product_and_weight(client):
    """Проверка создания операции с товаром и весом"""
    client.post('/api/login', json={"username": "operator1", "password": "op1pass"})
    response = client.post('/api/operations', json={
        "pvz_id": 1,
        "type": "in",
        "ts": "2026-05-13 10:00:00",
        "product_name": "Смартфон",
        "weight_kg": 0.35
    })
    assert response.status_code == 201
    assert response.json["ok"] is True

def test_create_operation_invalid_weight(client):
    """Проверка валидации weight_kg"""
    client.post('/api/login', json={"username": "operator1", "password": "op1pass"})
    response = client.post('/api/operations', json={
        "pvz_id": 1,
        "type": "in",
        "ts": "2026-05-13 10:00:00",
        "weight_kg": -1.0
    })
    assert response.status_code == 400

def test_create_operation_product_too_long(client):
    """Проверка валидации product_name"""
    client.post('/api/login', json={"username": "operator1", "password": "op1pass"})
    response = client.post('/api/operations', json={
        "pvz_id": 1,
        "type": "in",
        "ts": "2026-05-13 10:00:00",
        "product_name": "А" * 201
    })
    assert response.status_code == 400

def test_operations_return_product_fields(client):
    """Проверка, что GET /operations возвращает product_name и weight_kg"""
    client.post('/api/login', json={"username": "analyst1", "password": "anapass"})
    response = client.get('/api/operations?limit=1')
    assert response.status_code == 200
    data = response.json["data"]
    if data:
        assert "product_name" in data[0]
        assert "weight_kg" in data[0]
