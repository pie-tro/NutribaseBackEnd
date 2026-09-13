import re
import unicodedata

# Termos e sinônimos técnicos associados a derivados do leite / lactose,
# citados na fundamentação do TG (RDC 727/2022, ANVISA) e na literatura sobre
# rotulagem. Lista inicial — pode e deve crescer conforme testes com rótulos
# reais (ver Sprint 3 do planejamento SCRUM: "lógica Python de varredura por
# termos lácteos").
TERMOS_LACTOSE = [
    "leite",
    "leite em po",
    "leite integral",
    "leite desnatado",
    "leite condensado",
    "soro de leite",
    "soro do leite",
    "lactose",
    "lactoglobulina",
    "lactoalbumina",
    "caseina",
    "caseinato",
    "manteiga",
    "gordura de leite",
    "gordura lactea",
    "creme de leite",
    "nata",
    "queijo",
    "iogurte",
    "coalho",
    "whey",
    "whey protein",
    "proteina do leite",
    "solidos lacteos",
    "derivados do leite",
    "contem leite",
]


def _normalizar(texto: str) -> str:
    """Remove acentos e caixa alta/baixa para comparação mais robusta com o
    texto bruto que sai do OCR (que costuma vir sem formatação limpa)."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def analisar_texto(texto_ocr: str) -> dict:
    """
    Recebe o texto já extraído pelo OCR (Google ML Kit, feito no front-end)
    e retorna se há risco de lactose, junto dos termos encontrados.
    """
    texto_normalizado = _normalizar(texto_ocr or "")

    termos_encontrados = []
    for termo in TERMOS_LACTOSE:
        termo_normalizado = _normalizar(termo)
        # \b para evitar falso positivo em substrings soltas
        padrao = r"\b" + re.escape(termo_normalizado) + r"\b"
        if re.search(padrao, texto_normalizado):
            termos_encontrados.append(termo)

    contem_lactose = len(termos_encontrados) > 0

    return {
        "resultado": "prejudicial" if contem_lactose else "seguro",
        "termos_encontrados": termos_encontrados,
    }
