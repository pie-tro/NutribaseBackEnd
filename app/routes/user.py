import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.extensions import db, jwt_blocklist, limiter
from app.models import User
from app.utils.validators import (
    NOME_MAX,
    detectar_tipo_imagem,
    extensao_permitida,
    remover_foto_antiga,
    senha_dentro_do_limite,
)

user_bp = Blueprint("user", __name__, url_prefix="/user")


def _senha_confere(usuario: User, senha: str) -> bool:
    return senha_dentro_do_limite(senha) and usuario.checar_senha(senha)



@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    usuario = User.query.get_or_404(int(get_jwt_identity()))
    return jsonify(usuario.to_dict()), 200



@user_bp.route("/profile", methods=["PUT"])
@jwt_required()
@limiter.limit("20 per hour", key_func=lambda: "uid:" + str(get_jwt_identity()))
def update_profile():
    usuario = User.query.get_or_404(int(get_jwt_identity()))


    senha_atual = request.form.get("senha_atual") or ""
    if not _senha_confere(usuario, senha_atual):
        return jsonify({"erro": "Senha inválida para confirmação."}), 401

    nome = request.form.get("nome")
    if nome and nome.strip():
        nome = nome.strip()
        if len(nome) > NOME_MAX:
            return jsonify({"erro": f"O nome deve ter no máximo {NOME_MAX} caracteres."}), 400
        usuario.nome = nome

    foto_antiga = None
    foto = request.files.get("foto")
    if foto and foto.filename:
        if not extensao_permitida(foto.filename, current_app.config["ALLOWED_IMAGE_EXTENSIONS"]):
            return jsonify({"erro": "Formato de imagem não suportado."}), 400


        extensao = detectar_tipo_imagem(foto.stream)
        if extensao is None:
            return jsonify({"erro": "O arquivo enviado não é uma imagem válida (PNG, JPG ou WEBP)."}), 400

        nome_arquivo = f"{usuario.id}_{uuid.uuid4().hex}.{extensao}"
        caminho_completo = os.path.join(current_app.config["UPLOAD_FOLDER"], nome_arquivo)
        os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
        foto.save(caminho_completo)

        foto_antiga = usuario.foto_perfil
        usuario.foto_perfil = f"/uploads/profile_photos/{nome_arquivo}"

    db.session.commit()


    if foto_antiga:
        remover_foto_antiga(foto_antiga, current_app.config["UPLOAD_FOLDER"])

    return jsonify({"mensagem": "Perfil atualizado com sucesso.", "usuario": usuario.to_dict()}), 200



@user_bp.route("/account", methods=["DELETE"])
@jwt_required()
@limiter.limit("5 per hour", key_func=lambda: "uid:" + str(get_jwt_identity()))
def delete_account():
    usuario = User.query.get_or_404(int(get_jwt_identity()))

    dados = request.get_json(silent=True) or {}
    senha = dados.get("senha") or ""

    if not _senha_confere(usuario, senha):
        return jsonify({"erro": "Senha inválida para confirmação."}), 401


    jti = get_jwt()["jti"]
    jwt_blocklist.add(jti)

    foto = usuario.foto_perfil

    db.session.delete(usuario)
    db.session.commit()


    remover_foto_antiga(foto, current_app.config["UPLOAD_FOLDER"])

    return jsonify({"mensagem": "Conta excluída com sucesso."}), 200
