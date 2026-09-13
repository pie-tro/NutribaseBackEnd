import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.extensions import db, jwt_blocklist
from app.models import User
from app.utils.validators import extensao_permitida

user_bp = Blueprint("user", __name__, url_prefix="/user")


# Consulta os dados do perfil autenticado
@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    usuario = User.query.get_or_404(get_jwt_identity())
    return jsonify(usuario.to_dict()), 200


# RF04 - Usuário consegue editar seu perfil com foto e nome
# Segue o caso de uso: exige a senha atual para confirmar a alteração.
@user_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    usuario = User.query.get_or_404(get_jwt_identity())

    # multipart/form-data por causa do upload de foto (arquivo + campos de texto)
    senha_atual = request.form.get("senha_atual") or ""
    if not usuario.checar_senha(senha_atual):
        return jsonify({"erro": "Senha inválida para confirmação."}), 401

    nome = request.form.get("nome")
    if nome:
        usuario.nome = nome.strip()

    restricoes = request.form.get("restricoes")  # ex: "lactose,gluten" (opcional)
    if restricoes is not None:
        usuario.restricoes = [r.strip() for r in restricoes.split(",") if r.strip()]

    foto = request.files.get("foto")
    if foto and foto.filename:
        if not extensao_permitida(foto.filename, current_app.config["ALLOWED_IMAGE_EXTENSIONS"]):
            return jsonify({"erro": "Formato de imagem não suportado."}), 400

        extensao = foto.filename.rsplit(".", 1)[1].lower()
        nome_arquivo = f"{usuario.id}_{uuid.uuid4().hex}.{extensao}"
        caminho_completo = os.path.join(current_app.config["UPLOAD_FOLDER"], nome_arquivo)
        os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
        foto.save(caminho_completo)

        usuario.foto_perfil = f"/uploads/profile_photos/{nome_arquivo}"

    db.session.commit()

    return jsonify({"mensagem": "Perfil atualizado com sucesso.", "usuario": usuario.to_dict()}), 200


# RF05 - Usuário pode excluir a própria conta
@user_bp.route("/account", methods=["DELETE"])
@jwt_required()
def delete_account():
    usuario = User.query.get_or_404(get_jwt_identity())

    dados = request.get_json(silent=True) or {}
    senha = dados.get("senha") or ""

    if not usuario.checar_senha(senha):
        return jsonify({"erro": "Senha inválida para confirmação."}), 401

    # Invalida a sessão atual junto com a exclusão
    jti = get_jwt()["jti"]
    jwt_blocklist.add(jti)

    db.session.delete(usuario)  # cascade remove o histórico vinculado (ver model User)
    db.session.commit()

    return jsonify({"mensagem": "Conta excluída com sucesso."}), 200
