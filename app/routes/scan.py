from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import ScanHistory
from app.utils.lactose_terms import analisar_texto
from app.utils.validators import PRODUTO_MAX, TEXTO_OCR_MAX

scan_bp = Blueprint("scan", __name__, url_prefix="/scan")


# OCR
@scan_bp.route("/analyze", methods=["POST"])
@jwt_required()
@limiter.limit("60 per minute")
def analyze_scan():
    usuario_id = int(get_jwt_identity())
    dados = request.get_json(silent=True) or {}

    texto_ocr = dados.get("texto_ocr") or ""
    nome_produto = (dados.get("nome_produto") or "").strip()

    if not texto_ocr.strip():
        return jsonify({"erro": "Nenhum texto de OCR foi enviado para análise."}), 400

    if not nome_produto:
        return jsonify({"erro": "É necessário informar o nome do produto para salvar no histórico."}), 400

    if len(texto_ocr) > TEXTO_OCR_MAX:
        return jsonify({"erro": "O texto lido é grande demais para análise."}), 413

    if len(nome_produto) > PRODUTO_MAX:
        return jsonify({"erro": f"O nome do produto deve ter no máximo {PRODUTO_MAX} caracteres."}), 400

    analise = analisar_texto(texto_ocr)

    registro = ScanHistory(
        usuario_id=usuario_id,
        nome_produto=nome_produto,
        resultado=analise["resultado"],
        detalhes={
            "texto_analisado": texto_ocr,
            "termos_encontrados": analise["termos_encontrados"],
            "termos_ignorados": analise["termos_ignorados"],
            "advertencias": analise.get("advertencias", []),
        },
    )
    db.session.add(registro)
    db.session.commit()

    return jsonify(
        {
            "resultado": analise["resultado"],  # "seguro" | "atencao" | "prejudicial"
            "termos_encontrados": analise["termos_encontrados"],
            "advertencias": analise.get("advertencias", []),
            "registro": registro.to_dict(),
        }
    ), 201


# Histórico de produtos analisados
@scan_bp.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    usuario_id = int(get_jwt_identity())

    registros = (
        ScanHistory.query.filter_by(usuario_id=usuario_id)
        .order_by(ScanHistory.criado_em.desc())
        .all()
    )

    return jsonify([r.to_dict() for r in registros]), 200


# Detalhe de um item específico do histórico
@scan_bp.route("/history/<int:registro_id>", methods=["GET"])
@jwt_required()
def get_history_detail(registro_id):
    usuario_id = int(get_jwt_identity())

    registro = ScanHistory.query.filter_by(id=registro_id, usuario_id=usuario_id).first()
    if not registro:
        return jsonify({"erro": "Registro não encontrado."}), 404

    return jsonify(registro.to_dict()), 200
