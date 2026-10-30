import secrets
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


def gerar_codigo_recuperacao(tamanho: int = 6) -> str:
    
    return "".join(secrets.choice("0123456789") for _ in range(tamanho))


def enviar_email_recuperacao(destinatario: str, codigo: str) -> None:
    cfg = current_app.config
    minutos = cfg["PASSWORD_RESET_CODE_EXPIRES_MINUTES"]

    if cfg["MAIL_SIMULATION"]:
        print(f"[E-MAIL SIMULADO] Para: {destinatario} | Código de recuperação: {codigo}", flush=True)
        return

    remetente = cfg["MAIL_FROM"] or cfg["MAIL_USERNAME"]

    msg = EmailMessage()
    msg["Subject"] = "Nutribase - Código de recuperação de senha"
    msg["From"] = remetente
    msg["To"] = destinatario
    msg.set_content(
        f"Olá!\n\n"
        f"Seu código de recuperação de senha do Nutribase é: {codigo}\n\n"
        f"Ele expira em {minutos} minutos e só pode ser usado uma vez.\n"
        f"Se você não pediu a recuperação, ignore este e-mail.\n\n"
        f"Equipe Nutribase"
    )

    try:
        porta = int(cfg["MAIL_PORT"])
        contexto = ssl.create_default_context()

        
        if porta == 465:
            conexao = smtplib.SMTP_SSL(cfg["MAIL_SERVER"], porta, timeout=15, context=contexto)
       
        else:
            conexao = smtplib.SMTP(cfg["MAIL_SERVER"], porta, timeout=15)

        with conexao as servidor:
            servidor.ehlo()
            if porta != 465 and cfg.get("MAIL_USE_TLS", True):
                servidor.starttls(context=contexto)
                servidor.ehlo() 
            
            if cfg["MAIL_USERNAME"]:
              
                senha = cfg["MAIL_PASSWORD"].replace(" ", "")
                servidor.login(cfg["MAIL_USERNAME"], senha)
            
            servidor.send_message(msg)
    except Exception:
        current_app.logger.exception("Falha ao enviar e-mail de recuperação para %s", destinatario)
        raise