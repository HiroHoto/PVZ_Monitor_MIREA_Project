"""
Модуль: app
Назначение: Application Factory для Flask приложения
Зависимости: from flask import Flask, render_template, from config import SECRET_KEY, from db import init_db, from routes.auth import bp as auth_bp, from routes.pvz import bp as pvz_bp, from routes.operations import bp as ops_bp, from routes.reports import bp as report_bp
Экспортирует: create_app()
Безопасность: Инициализирует приложение и регистрирует все компоненты; содержит секретный ключ
"""

from flask import Flask, render_template
from config import SECRET_KEY
from db import init_db
from routes.auth import bp as auth_bp
from routes.pvz import bp as pvz_bp
from routes.operations import bp as ops_bp
from routes.reports import bp as report_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.register_blueprint(auth_bp)
    app.register_blueprint(pvz_bp)
    app.register_blueprint(ops_bp)
    app.register_blueprint(report_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app

if __name__ == "__main__":
    init_db()
    create_app().run(debug=True, port=5000)
