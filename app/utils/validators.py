import os

from email_validator import EmailNotValidError, validate_email


def email_valido(email: str) -> bool:
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def extensao_permitida(nome_arquivo: str, extensoes_permitidas: set) -> bool:
    return (
        "." in nome_arquivo
        and nome_arquivo.rsplit(".", 1)[1].lower() in extensoes_permitidas
    )
