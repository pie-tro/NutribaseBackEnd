from datetime import datetime

from app.extensions import db


class ScanHistory(db.Model):


    __tablename__ = "historico_consultas"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    nome_produto = db.Column(db.String(150), nullable=False)
    resultado = db.Column(db.String(20), nullable=False)  # "seguro" | "prejudicial"
    detalhes = db.Column(db.JSON, nullable=False, default=dict)
  
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome_produto": self.nome_produto,
            "resultado": self.resultado,
            "detalhes": self.detalhes,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }

    def __repr__(self) -> str:
        return f"<ScanHistory {self.nome_produto} - {self.resultado}>"
