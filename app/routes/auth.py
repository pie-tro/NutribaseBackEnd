from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    jwt_required,
)

from app.extensions import db, jwt_blocklist
from app.models import PasswordResetToken, User
from app.utils.email_service import enviar_email_recuperacao, gerar_codigo_recuperacao
from app.utils.validators import email_valido

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# RF01 - Usuário realiza cadastro no sistema
@auth_bp.route("/register", methods=["POST"])
def register():
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""
    confirmar_senha = dados.get("confirmar_senha") or ""

    if not nome or not email or not senha:
        return jsonify({"erro": "Nome, e-mail e senha são obrigatórios."}), 400

    if not email_valido(email):
        return jsonify({"erro": "E-mail inválido."}), 400

    if senha != confirmar_senha:
        return jsonify({"erro": "As senhas não coincidem."}), 400

    if len(senha) < 6:
        return jsonify({"erro": "A senha deve ter ao menos 6 caracteres."}), 400

    # E-mail deve ser único (Tabela 4 - Caso de uso Fazer Cadastro)
    if User.query.filter_by(email=email).first():
        return jsonify({"erro": "Já existe uma conta cadastrada com este e-mail."}), 409

    novo_usuario = User(nome=nome, email=email)
    novo_usuario.set_senha(senha)

    db.session.add(novo_usuario)
    db.session.commit()

    return jsonify({"mensagem": "Cadastro realizado com sucesso.", "usuario": novo_usuario.to_dict()}), 201


# RF02 - Usuário efetua login com credenciais cadastradas
@auth_bp.route("/login", methods=["POST"])
def login():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    usuario = User.query.filter_by(email=email).first()

    if not usuario or not usuario.checar_senha(senha):
        return jsonify({"erro": "E-mail ou senha inválidos."}), 401

    token_acesso = create_access_token(identity=usuario.id)

    return jsonify(
        {
            "mensagem": "Login realizado com sucesso.",
            "access_token": token_acesso,
            "usuario": usuario.to_dict(),
        }
    ), 200


# RF03 (parte 1) - Solicitar recuperação de senha
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()

    usuario = User.query.filter_by(email=email).first()

    # Mensagem genérica quando o e-mail não existe, para não vazar quais
    # e-mails estão cadastrados (boa prática de segurança / LGPD - RNF01).
    # O TG especifica o retorno "E-mail não cadastrado" no fluxo alternativo,
    # então seguimos o comportamento descrito lá.
    if not usuario:
        return jsonify({"erro": "E-mail não cadastrado."}), 404

    codigo = gerar_codigo_recuperacao()
    expira_em = PasswordResetToken.gerar_expiracao(
        current_app.config["PASSWORD_RESET_CODE_EXPIRES_MINUTES"]
    )

    reset_token = PasswordResetToken(usuario_id=usuario.id, codigo=codigo, expira_em=expira_em)
    db.session.add(reset_token)
    db.session.commit()

    enviar_email_recuperacao(usuario.email, codigo)

    return jsonify({"mensagem": "Código de recuperação enviado para o e-mail cadastrado."}), 200


# RF03 (parte 2) - Confirmar código e definir nova senha
@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()
    codigo = (dados.get("codigo") or "").strip()
    nova_senha = dados.get("nova_senha") or ""

    usuario = User.query.filter_by(email=email).first()
    if not usuario:
        return jsonify({"erro": "E-mail não cadastrado."}), 404

    reset_token = (
        PasswordResetToken.query.filter_by(usuario_id=usuario.id, codigo=codigo, usado=False)
        .order_by(PasswordResetToken.id.desc())
        .first()
    )

    if not reset_token or not reset_token.esta_valido():
        return jsonify({"erro": "Código inválido ou expirado."}), 400

    if len(nova_senha) < 6:
        return jsonify({"erro": "A senha deve ter ao menos 6 caracteres."}), 400

    usuario.set_senha(nova_senha)
    reset_token.usado = True
    db.session.commit()

    return jsonify({"mensagem": "Senha redefinida com sucesso."}), 200


# RF: Fazer Logoff — invalida o token atual
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    jwt_blocklist.add(jti)
    return jsonify({"mensagem": "Sessão encerrada com sucesso."}), 200
