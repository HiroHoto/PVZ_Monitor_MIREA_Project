# Развёртывание

## Требования
- OS: Ubuntu 22.04 и выше
- Зависимости: Python 3.10, Flask 3.x, SQLite

## Переменные окружения
- `DB_URL=sqlite:///pvz.db`
- `SECRET_KEY=your_secret_key`

## Запуск
```bash
git clone https://github.com/username/pvz-monitor.git
cd pvz-monitor
pip install -r requirements.txt
python app.py
```

## Продакшн (nginx + pm2)
### Настройка nginx
```nginx
server {
    listen 80;
    server_name pvz-monitor.example.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Настройка PM2
```bash
# Установка PM2
npm install -g pm2

# Запуск приложения через PM2
pm2 start app.py --name "pvz-monitor"

# Сохранение конфигурации PM2
pm2 save

# Настройка автозапуска PM2
pm2 startup
```