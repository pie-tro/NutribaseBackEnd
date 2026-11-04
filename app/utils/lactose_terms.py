import re
import unicodedata


TERMOS_LACTOSE = [
    "leite",
    "leite em po",
    "leite integral",
    "leite desnatado",
    "leite semidesnatado",
    "leite condensado",
    "leite evaporado",
    "leite fermentado",
    "leite de vaca",
    "leite de cabra",
    "leite de ovelha",
    "leite de bufala",
    "doce de leite",
    "soro de leite",
    "soro do leite",
    "solidos de leite",
    "solidos lacteos",
    "derivados do leite",
    "derivados lacteos",
    "proteina do leite",
    "proteinas do leite",
    "proteina lactea",
    "albumina do leite",
    "gordura de leite",
    "gordura do leite",
    "gordura lactea",
    "gordura butirica",
    "contem leite",
    "pode conter leite",
    "extrato lacteo",
    "composto lacteo",
    "bebida lactea",
    "mistura lactea",
    "lactose",
    "lactoglobulina",
    "lactoalbumina",
    "lactalbumina",
    "lactoferrina",
    "caseina",
    "caseinato",
    "caseinato de calcio",
    "caseinato de sodio",
    "manteiga",
    "ghee",
    "creme de leite",
    "nata",
    "chantilly",
    "requeijao",
    "cream cheese",
    "queijo",
    "mussarela",
    "muçarela",
    "mozarela",
    "mozzarella",
    "parmesao",
    "cheddar",
    "provolone",
    "gorgonzola",
    "ricota",
    "coalhada",
    "iogurte",
    "kefir",
    "coalho",
    "buttermilk",
    "lacteo",
    "lacteos",
    "lactea",
    "lacteas",
    "whey",
    "whey protein",
    "milk",
    "butter",
]


_VEGETAIS = (
    r"coco|amendoas?|amendoim|aveia|soja|arroz|castanhas?(?: de caju| do para)?|"
    r"macadamia|babacu|gergelim|quinoa|avela|nozes|pistache|cevada|milho|"
    r"cupuacu|cacau|karite|murumuru|tahine"
)
EXCLUSOES = [
    rf"leite de (?:{_VEGETAIS})",
    rf"manteiga de (?:{_VEGETAIS})",
    r"creme de (?:coco|castanhas?|aveia|arroz|amendoas?|soja)",
    rf"iogurte (?:de )?(?:{_VEGETAIS}|vegetal|vegano)",
    rf"queijo (?:de )?(?:{_VEGETAIS}|vegetal|vegano)",
    r"(?:leite|iogurte|queijo|manteiga|nata|requeijao|creme) (?:vegetal|vegano|vegana)",
    r"bebida (?:vegetal|de soja)",
]


DECLARACOES_LACTOSE = [
    r"(?:nao contem|sem|zero|livre de|isento de|isenta de|0%?) (?:de )?lactose",
    r"lactose (?:zero|0%?|free)",
    r"(?:zero|sem|no|free of) ?-?lactose",
    r"lactose-free",
]
NEGACOES = DECLARACOES_LACTOSE + [
    r"(?:nao contem|sem|livre de|isento de|isenta de) leite",
]

_EXCLUSOES_RE = [re.compile(r"\b" + p + r"\b") for p in EXCLUSOES]
_NEGACOES_RE = [re.compile(r"\b" + p + r"(?!\w)") for p in NEGACOES]
_DECLARACOES_RE = [re.compile(r"\b" + p + r"(?!\w)") for p in DECLARACOES_LACTOSE]


def _normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def analisar_texto(texto_ocr: str) -> dict:
    texto = _normalizar(texto_ocr or "")


    ignorados = []
    for padrao in _EXCLUSOES_RE + _NEGACOES_RE:
        for m in padrao.finditer(texto):
            ignorados.append(m.group(0))
        texto = padrao.sub(" ", texto)


    declarou = any(p.search(_normalizar(texto_ocr or "")) for p in _DECLARACOES_RE)
    if declarou and not re.search(r"\blactose\b", texto):
        return {
            "resultado": "seguro",
            "termos_encontrados": [],
            "termos_ignorados": sorted(set(ignorados)),
            "declarou_sem_lactose": True,
        }

    termos_encontrados = []
    for termo in TERMOS_LACTOSE:
        termo_normalizado = _normalizar(termo)
        padrao = r"\b" + re.escape(termo_normalizado) + r"s?\b"
        if re.search(padrao, texto):
            termos_encontrados.append(termo)

    contem_lactose = len(termos_encontrados) > 0

    return {
        "resultado": "prejudicial" if contem_lactose else "seguro",
        "termos_encontrados": termos_encontrados,
        "termos_ignorados": sorted(set(ignorados)),
    }