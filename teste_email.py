import os
import smtplib
import ssl
import sys

from dotenv import load_dotenv

load_dotenv()

host = os.getenv("MAIL_SERVER", "smtp.gmail.com")
usuario = os.getenv("MAIL_USERNAME", "")
senha = "".join(os.getenv("MAIL_PASSWORD", "").split())  # tira qualquer tipo de espaço
usa_tls = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
porta = sys.argv[1] if len(sys.argv) > 1 else os.getenv("MAIL_PORT", "587")

print("usuário:", repr(usuario), "| parece um e-mail:", "@" in usuario)
print("senha: tamanho =", len(senha), "| só ASCII =", senha.isascii(), "(esperado: 16 e True)")
print(f"servidor: {host}:{porta}\n")


def passo(nome, funcao):
    try:
        resultado = funcao()
        print("OK     ", nome)
        return resultado
    except Exception as erro:
        print("FALHOU ", nome, "->", type(erro).__name__, ":", erro)
        sys.exit(1)


contexto = ssl.create_default_context()
if porta == "465":
    s = passo("conectar (TLS direto)", lambda: smtplib.SMTP_SSL(host, 465, timeout=15, context=contexto))
else:
    s = passo("conectar", lambda: smtplib.SMTP(host, int(porta), timeout=15))
    passo("EHLO", s.ehlo)
    if usa_tls:
        passo("STARTTLS", lambda: s.starttls(context=contexto))
        passo("EHLO depois do TLS", s.ehlo)

if usuario:
    passo("login", lambda: s.login(usuario, senha))
passo("encerrar", s.quit)
print("\nTUDO OK.")