import os

from flask import Flask, jsonify, send_from_directory

from app.config import config_by_name
from app.extensions import bcrypt, cors, db, jwt, migrate
from app.routes import register_routes


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Extensões
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)  
    # Garante que a pasta de uploads exista
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Rotas da API
    register_routes(app)

    # Serve as fotos de perfil salvas localmente (RF04)
    @app.route("/uploads/profile_photos/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # Rota simples de verificação de saúde da API
    @app.route("/health")
    def health_check():
        return jsonify({"status": "ok", "servico": "Nutribase API"}), 200

    # Tratamento padrão de erros JSON (evita páginas HTML de erro do Flask)
    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"erro": "Recurso não encontrado."}), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"erro": "Erro interno no servidor."}), 500

    return app
