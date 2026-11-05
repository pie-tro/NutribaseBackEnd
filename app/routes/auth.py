import secrets

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    jwt_required,
)

from app.extensions import bcrypt, db, jwt_blocklist, limiter
from app.models import PasswordResetToken, User
from app.utils.email_service import enviar_email_recuperacao, gerar_codigo_recuperacao
from app.utils.validators import (
    NOME_MAX,
    email_valido,
    senha_dentro_do_limite,
    senha_valida,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


_HASH_FALSO = None


def _hash_falso() -> str:
    global _HASH_FALSO
    if _HASH_FALSO is None:
        _HASH_FALSO = bcrypt.generate_password_hash("senha-falsa-para-igualar-tempo").decode("utf-8")
    return _HASH_FALSO


def _chave_email() -> str:
    dados = request.get_json(silent=True) or {}
    return "email:" + (dados.get("email") or "").strip().lower()



@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""
    confirmar_senha = dados.get("confirmar_senha") or ""

    if not nome or not email or not senha:
        return jsonify({"erro": "Nome, e-mail e senha são obrigatórios."}), 400

    if len(nome) > NOME_MAX:
        return jsonify({"erro": f"O nome deve ter no máximo {NOME_MAX} caracteres."}), 400

    if not email_valido(email):
        return jsonify({"erro": "E-mail inválido."}), 400

    if senha != confirmar_senha:
        return jsonify({"erro": "As senhas não coincidem."}), 400

    erro_senha = senha_valida(senha)
    if erro_senha:
        return jsonify({"erro": erro_senha}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"erro": "Já existe uma conta cadastrada com este e-mail."}), 409

    novo_usuario = User(nome=nome, email=email)
    novo_usuario.set_senha(senha)

    db.session.add(novo_usuario)
    db.session.commit()

    return jsonify({"mensagem": "Cadastro realizado com sucesso.", "usuario": novo_usuario.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute; 100 per hour")
@limiter.limit("10 per minute", key_func=_chave_email)
def login():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    usuario = User.query.filter_by(email=email).first()

    if not senha_dentro_do_limite(senha):

        return jsonify({"erro": "E-mail ou senha inválidos."}), 401

    if not usuario:
        bcrypt.check_password_hash(_hash_falso(), senha)
        return jsonify({"erro": "E-mail ou senha inválidos."}), 401

    if not usuario.checar_senha(senha):
        return jsonify({"erro": "E-mail ou senha inválidos."}), 401


    token_acesso = create_access_token(identity=str(usuario.id))

    return jsonify(
        {
            "mensagem": "Login realizado com sucesso.",
            "access_token": token_acesso,
            "usuario": usuario.to_dict(),
        }
    ), 200


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("3 per minute; 10 per hour")
@limiter.limit("5 per hour", key_func=_chave_email)
def forgot_password():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()

    usuario = User.query.filter_by(email=email).first()

  
    if not usuario:
        return jsonify({"erro": "E-mail não cadastrado."}), 404


    PasswordResetToken.query.filter_by(usuario_id=usuario.id, usado=False).update({"usado": True})

    codigo = gerar_codigo_recuperacao()
    expira_em = PasswordResetToken.gerar_expiracao(
        current_app.config["PASSWORD_RESET_CODE_EXPIRES_MINUTES"]
    )

    reset_token = PasswordResetToken(usuario_id=usuario.id, codigo=codigo, expira_em=expira_em)
    db.session.add(reset_token)
    db.session.commit()

    try:
        enviar_email_recuperacao(usuario.email, codigo)
    except Exception:

        return jsonify({"erro": "Não foi possível enviar o e-mail agora. Tente novamente mais tarde."}), 502

    return jsonify({"mensagem": "Código de recuperação enviado para o e-mail cadastrado."}), 200



@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("5 per minute; 20 per hour")
@limiter.limit("10 per hour", key_func=_chave_email)
def reset_password():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()
    codigo = (dados.get("codigo") or "").strip()
    nova_senha = dados.get("nova_senha") or ""

    erro_generico = jsonify({"erro": "Código inválido ou expirado."}), 400

    usuario = User.query.filter_by(email=email).first()
    if not usuario:

        return erro_generico


    reset_token = (
        PasswordResetToken.query.filter_by(usuario_id=usuario.id, usado=False)
        .order_by(PasswordResetToken.id.desc())
        .first()
    )

    if not reset_token or not reset_token.esta_valido():
        return erro_generico


    maximo = current_app.config["PASSWORD_RESET_MAX_ATTEMPTS"]
    if reset_token.tentativas >= maximo:
        reset_token.usado = True
        db.session.commit()
        return erro_generico

    if not secrets.compare_digest(reset_token.codigo, codigo):
        reset_token.tentativas += 1
        if reset_token.tentativas >= maximo:
            reset_token.usado = True
        db.session.commit()
        return erro_generico

    erro_senha = senha_valida(nova_senha)
    if erro_senha:
        return jsonify({"erro": erro_senha}), 400

    usuario.set_senha(nova_senha)
    reset_token.usado = True
    db.session.commit()

    return jsonify({"mensagem": "Senha redefinida com sucesso."}), 200



@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    jwt_blocklist.add(jti)
    return jsonify({"mensagem": "Sessão encerrada com sucesso."}), 200
