import uuid
from datetime import datetime, timedelta

from app.extensions import bcrypt, db


class User(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    foto_perfil = db.Column(db.String(255), nullable=True)  # caminho do arquivo salvo
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Restrições alimentares do usuário (RF: gerenciamento personalizado de restrições)
    restricoes = db.Column(db.JSON, default=list)  # ex: ["lactose"]

    historico = db.relationship(
        "ScanHistory", backref="usuario", cascade="all, delete-orphan", lazy=True
    )
    reset_tokens = db.relationship(
        "PasswordResetToken", backref="usuario", cascade="all, delete-orphan", lazy=True
    )

    # --- Senha ---
    def set_senha(self, senha_texto_puro: str) -> None:
        self.senha_hash = bcrypt.generate_password_hash(senha_texto_puro).decode("utf-8")

    def checar_senha(self, senha_texto_puro: str) -> bool:
        return bcrypt.check_password_hash(self.senha_hash, senha_texto_puro)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "foto_perfil": self.foto_perfil,
            "restricoes": self.restricoes or [],
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class PasswordResetToken(db.Model):
    """Código de uso único para o fluxo 'Esqueci Minha Senha' (RF03)."""

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    codigo = db.Column(db.String(6), nullable=False)
    token = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True)
    expira_em = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, default=False)

    def esta_valido(self) -> bool:
        return not self.usado and datetime.utcnow() < self.expira_em

    @staticmethod
    def gerar_expiracao(minutos: int) -> datetime:
        return datetime.utcnow() + timedelta(minutes=minutos)
