from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import ScanHistory
from app.utils.lactose_terms import analisar_texto

scan_bp = Blueprint("scan", __name__, url_prefix="/scan")


# RF06/RF07/RF08 - Recebe o texto já extraído pelo OCR (front-end/Google ML Kit),
# analisa a presença de lactose e registra o resultado no histórico.
@scan_bp.route("/analyze", methods=["POST"])
@jwt_required()
def analyze_scan():
    usuario_id = get_jwt_identity()
    dados = request.get_json(silent=True) or {}

    texto_ocr = dados.get("texto_ocr") or ""
    nome_produto = (dados.get("nome_produto") or "").strip()

    if not texto_ocr.strip():
        return jsonify({"erro": "Nenhum texto de OCR foi enviado para análise."}), 400

    if not nome_produto:
        return jsonify({"erro": "É necessário informar o nome do produto para salvar no histórico."}), 400

    analise = analisar_texto(texto_ocr)

    registro = ScanHistory(
        usuario_id=usuario_id,
        nome_produto=nome_produto,
        resultado=analise["resultado"],
        detalhes={
            "texto_analisado": texto_ocr,
            "termos_encontrados": analise["termos_encontrados"],
        },
    )
    db.session.add(registro)
    db.session.commit()

    return jsonify(
        {
            "resultado": analise["resultado"],  # "seguro" | "prejudicial"
            "termos_encontrados": analise["termos_encontrados"],
            "registro": registro.to_dict(),
        }
    ), 201


# RF09 - Sistema armazena/exibe histórico de rótulos escaneados
@scan_bp.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    usuario_id = get_jwt_identity()

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
    usuario_id = get_jwt_identity()

    registro = ScanHistory.query.filter_by(id=registro_id, usuario_id=usuario_id).first()
    if not registro:
        return jsonify({"erro": "Registro não encontrado."}), 404

    return jsonify(registro.to_dict()), 200
