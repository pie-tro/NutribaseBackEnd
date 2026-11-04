import os

from flask import Flask, jsonify, send_from_directory

from app.config import config_by_name
from app.extensions import bcrypt, cors, db, jwt, limiter, migrate
from app.routes import register_routes


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])


    if config_name == "production":
        for chave, padrao in (("SECRET_KEY", "dev-secret-key"), ("JWT_SECRET_KEY", "dev-jwt-secret")):
            valor = app.config.get(chave) or ""
            if not valor or valor == padrao or valor.startswith("troque"):
                raise RuntimeError(f"Defina {chave} no ambiente antes de rodar em produção.")


    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})
    limiter.init_app(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


    register_routes(app)


    @app.route("/uploads/profile_photos/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


    @app.route("/health")
    def health_check():
        return jsonify({"status": "ok", "servico": "Nutribase API"}), 200


    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"erro": "Recurso não encontrado."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"erro": "Método não permitido."}), 405

    @app.errorhandler(413)
    def payload_too_large(_error):
        return jsonify({"erro": "Arquivo ou requisição grande demais."}), 413

    @app.errorhandler(429)
    def too_many_requests(_error):
        return jsonify({"erro": "Muitas tentativas. Aguarde um pouco e tente novamente."}), 429

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"erro": "Erro interno no servidor."}), 500

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        if resp.mimetype == "application/json":
            resp.headers["Cache-Control"] = "no-store"
        return resp

    return app
