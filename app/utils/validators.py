import os

from email_validator import EmailNotValidError, validate_email

SENHA_MIN = 8

SENHA_MAX_BYTES = 72
NOME_MAX = 120
EMAIL_MAX = 150
PRODUTO_MAX = 150
TEXTO_OCR_MAX = 20000


def email_valido(email: str) -> bool:
    if not email or len(email) > EMAIL_MAX:
        return False
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def senha_valida(senha: str):

    if len(senha.encode("utf-8")) > SENHA_MAX_BYTES:
        return "A senha é longa demais (máximo de 72 bytes)."
    tem_letra = any(c.isalpha() for c in senha)
    tem_numero = any("0" <= c <= "9" for c in senha)
    tem_especial = any(not c.isalnum() and not c.isspace() for c in senha)
    if len(senha) < SENHA_MIN or not (tem_letra and tem_numero and tem_especial):
        return (
            f"A senha deve ter ao menos {SENHA_MIN} caracteres, "
            "com letra, número e caractere especial."
        )
    return None


def senha_dentro_do_limite(senha: str) -> bool:
    return len(senha.encode("utf-8")) <= SENHA_MAX_BYTES


def extensao_permitida(nome_arquivo: str, extensoes_permitidas: set) -> bool:
    return (
        "." in nome_arquivo
        and nome_arquivo.rsplit(".", 1)[1].lower() in extensoes_permitidas
    )


def detectar_tipo_imagem(arquivo):

    cabecalho = arquivo.read(12)
    arquivo.seek(0)
    if cabecalho.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if cabecalho.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if cabecalho[:4] == b"RIFF" and cabecalho[8:12] == b"WEBP":
        return "webp"
    return None


def remover_foto_antiga(caminho_relativo, pasta_uploads):

    if not caminho_relativo:
        return
    nome = os.path.basename(caminho_relativo)
    if not nome:
        return
    caminho = os.path.join(pasta_uploads, nome)
    try:
        if os.path.isfile(caminho):
            os.remove(caminho)
    except OSError:
        pass  
