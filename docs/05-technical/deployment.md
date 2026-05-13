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
(описание настройки nginx и pm2)