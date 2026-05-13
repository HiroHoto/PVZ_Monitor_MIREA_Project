def test_login_success(client):
    """Проверка успешного входа оператора"""
    response = client.post('/api/login', json={
        "username": "operator1",
        "password": "op1pass"
    })
    assert response.status_code == 200
    assert response.json['role'] == 'operator'

def test_access_denied_without_login(client):
    """Проверка защиты эндпоинтов"""
    response = client.get('/api/me')
    assert response.status_code == 401
