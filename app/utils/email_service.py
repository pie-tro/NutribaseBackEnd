import logging
import random

from flask import current_app

logger = logging.getLogger("nutribase.email")
logging.basicConfig(level=logging.INFO)


def gerar_codigo_recuperacao() -> str:
    """Código numérico de 6 dígitos para o fluxo 'Esqueci Minha Senha' (RF03)."""
    return f"{random.randint(0, 999999):06d}"


def enviar_email_recuperacao(destinatario: str, codigo: str) -> None:
    """
    Por enquanto (MAIL_SIMULATION=true no .env), apenas loga o código no console
    em vez de enviar um e-mail de verdade. Quando quiser conectar um provedor
    real (SMTP, SendGrid, Mailgun etc.), troque só o corpo desta função —
    o resto do fluxo (rotas, model PasswordResetToken) não muda.
    """
    if current_app.config.get("MAIL_SIMULATION", True):
        logger.info(
            "[SIMULAÇÃO DE E-MAIL] Para: %s | Código de recuperação: %s",
            destinatario,
            codigo,
        )
        return

    # Espaço reservado para integração real futura, ex:
    # import smtplib / usar Flask-Mail / chamar API do SendGrid etc.
    raise NotImplementedError(
        "Envio real de e-mail ainda não configurado. Ajuste MAIL_SIMULATION "
        "no .env ou implemente o envio real aqui."
    )
