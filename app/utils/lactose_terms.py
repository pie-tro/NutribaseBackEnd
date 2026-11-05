import re
import unicodedata

# Termos e sinônimos técnicos associados a derivados do leite / lactose,
# citados na fundamentação do TG (RDC 727/2022, ANVISA) e na literatura sobre
# rotulagem. Lista inicial — pode e deve crescer conforme testes com rótulos
# reais (ver Sprint 3 do planejamento SCRUM: "lógica Python de varredura por
# termos lácteos").
TERMOS_LACTOSE = [
    # leite e formas do leite
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
    "extrato lacteo",
    "composto lacteo",
    "bebida lactea",
    "mistura lactea",
    # lactose e proteínas do leite
    "lactose",
    "lactoglobulina",
    "lactoalbumina",
    "lactalbumina",
    "lactoferrina",
    "caseina",
    "caseinato",
    "caseinato de calcio",
    "caseinato de sodio",
    # laticínios
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
    # termos genéricos e em inglês que aparecem em rótulos
    "lacteo",
    "lacteos",
    "lactea",
    "lacteas",
    "whey",
    "whey protein",
    "milk",
    "butter",
    "cheese",
    "yogurt",
    "yoghurt",
    "dairy",
    "casein",
    "caseinate",
]

# Expressões que NÃO indicam lactose, mesmo contendo um termo da lista
# (alimentos de origem vegetal que apenas usam o nome "leite", "manteiga" etc.).
# São removidas do texto antes da busca, para evitar falso positivo.
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
    # equivalentes em inglês
    r"(?:coconut|almond|soy|soya|oat|rice|cashew|hazelnut|pea|hemp|macadamia|plant|plant-based|vegetable|vegan) (?:milk|cheese|butter|yogurt|yoghurt)",
    r"(?:cocoa|cacao|shea|peanut|almond|nut|cashew|sunflower|seed|mango|kokum) butter",
]

# Declarações de ausência ("sem lactose", "zero lactose"...). Removidas do
# texto antes da busca: a frase deixa de contar como menção a lactose, mas
# qualquer OUTRO termo lácteo no rótulo continua sendo detectado.
# As duas primeiras (declarações sobre a LACTOSE) valem para o rótulo inteiro:
# se o fabricante declara "zero lactose" e não sobra "lactose" como ingrediente,
# o produto é tratado como seguro (ex.: whey isolado ou leite "zero lactose").
DECLARACOES_LACTOSE = [
    r"(?:nao contem|sem|zero|livre de|isento de|isenta de|0%?) (?:de )?lactose",
    r"lactose (?:zero|0%?|free)",
    r"(?:zero|sem|no|free of) ?-?lactose",
    r"lactose-free",
]
NEGACOES = DECLARACOES_LACTOSE + [
    r"(?:nao contem|sem|livre de|isento de|isenta de) leite",
    r"(?:dairy|milk)[- ]free",
    r"(?:no|without) (?:dairy|milk)",
]

# Advertências de contaminação cruzada, exigidas pela RDC 727/2022 da ANVISA:
# "pode conter leite", "contém traços de leite", "fabricado em equipamento que
# também processa leite". NÃO são ingredientes: o leite não foi adicionado ao
# produto, existe apenas o risco de traços vindos da linha de produção.
# Para INTOLERÂNCIA À LACTOSE essa quantidade costuma ser tolerada, por isso o
# resultado é "atencao" (e não "prejudicial"): o aplicativo avisa e deixa a
# decisão com o usuário. Para ALERGIA à proteína do leite (APLV) esses produtos
# devem ser evitados — por isso o alerta não é escondido.
GATILHOS_TRACOS = [
    r"pode[m]? conter",
    r"podera conter",
    r"contem tracos",
    r"tracos de",
    r"(?:fabricado|produzido|processado|elaborado|manipulado|embalado) (?:em|no|na|num|numa)",
    r"(?:em|numa?) (?:equipamento|linha|local|industria|fabrica|ambiente)s? que",
    # Avisos em inglês (comuns em suplementos e produtos importados).
    # "processed cheese" é ingrediente, por isso "processes" sozinho NÃO é gatilho:
    # o aviso é reconhecido pelo começo ("made in a facility", "may contain"...).
    r"may contain",
    r"traces of",
    r"(?:made|manufactured|produced|processed|packed|packaged) (?:in|on) (?:a|an|the|shared)\b",
    r"(?:in|on) (?:a|an|the) (?:shared )?(?:facility|facilities|equipment|line|plant)\b",
    r"(?:facility|facilities|equipment|line|plant) (?:that|which|where)\b",
    r"shared (?:facility|facilities|equipment|line)",
]

# O trecho da advertência termina na primeira pontuação forte, no começo de uma
# nova lista de ingredientes, ou depois de 110 caracteres.
_FIM_ADVERTENCIA = re.compile(
    r"[.;|]|\bingredientes?\b|\bingredients?\b|\bcontem:|\bcontains:|\balergicos: contem\b"
)
_LIMITE_ADVERTENCIA = 110

_EXCLUSOES_RE = [re.compile(r"\b" + p + r"\b") for p in EXCLUSOES]
_NEGACOES_RE = [re.compile(r"\b" + p + r"(?!\w)") for p in NEGACOES]
_DECLARACOES_RE = [re.compile(r"\b" + p + r"(?!\w)") for p in DECLARACOES_LACTOSE]
_TRACOS_RE = [re.compile(r"\b" + g) for g in GATILHOS_TRACOS]


def _normalizar(texto: str) -> str:
    """Remove acentos, caixa alta/baixa e espaçamento irregular, para comparar
    com o texto bruto do OCR (quebras de linha no meio de expressões, hifens de
    fim de linha, espaços duplos etc.)."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    # hífen de quebra de linha ("lac-\ntose" -> "lactose")
    texto = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)
    # qualquer espaço em branco (inclui \n e \t) vira um único espaço
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _tem_termo_lacteo(trecho: str) -> bool:
    for termo in TERMOS_LACTOSE:
        if re.search(r"\b" + re.escape(_normalizar(termo)) + r"s?\b", trecho):
            return True
    return False


def _extrair_advertencias(texto: str):
    """Separa do texto as advertências de contaminação cruzada que citam leite.

    Devolve (texto_sem_advertencias, lista_de_advertencias). Um trecho só é
    tratado como advertência se houver termo lácteo dentro dele: assim
    "pode conter amendoim" ou "fabricado em São Paulo" não mexem na análise.
    """
    trechos = []
    for padrao in _TRACOS_RE:
        for m in padrao.finditer(texto):
            bruto = texto[m.start() : m.start() + _LIMITE_ADVERTENCIA]
            fim = _FIM_ADVERTENCIA.search(bruto, 1)
            if fim:
                bruto = bruto[: fim.start()]
            if _tem_termo_lacteo(bruto):
                trechos.append((m.start(), m.start() + len(bruto)))

    # Junta trechos sobrepostos ("pode conter traços de leite" dispara mais de
    # um gatilho) para que a remoção não corte o texto errado.
    unidos = []
    for ini, fim in sorted(trechos):
        if unidos and ini <= unidos[-1][1]:
            unidos[-1] = (unidos[-1][0], max(unidos[-1][1], fim))
        else:
            unidos.append((ini, fim))

    advertencias = [texto[i:f].strip() for i, f in unidos]
    for ini, fim in reversed(unidos):  # de trás para frente: índices não mudam
        texto = texto[:ini] + " " + texto[fim:]
    return texto, advertencias


def analisar_texto(texto_ocr: str) -> dict:
    """
    Recebe o texto já extraído pelo OCR (Google ML Kit, feito no front-end)
    e retorna o risco de lactose, junto dos termos encontrados.

    resultado:
      "prejudicial" - há ingrediente lácteo na composição
      "atencao"     - só há advertência de traços/contaminação cruzada
      "seguro"      - nada encontrado, ou o rótulo declara ausência de lactose
    """
    texto = _normalizar(texto_ocr or "")

    # Registra e remove o que NÃO deve contar como lactose
    ignorados = []
    for padrao in _EXCLUSOES_RE + _NEGACOES_RE:
        for m in padrao.finditer(texto):
            ignorados.append(m.group(0))
        texto = padrao.sub(" ", texto)

    # Advertências de contaminação cruzada ("pode conter leite"): saem do texto
    # para não virarem falso positivo, mas ficam registradas.
    texto, advertencias = _extrair_advertencias(texto)

    # Declaração de ausência de lactose ("zero lactose", "sem lactose"...):
    # vale para o rótulo todo, a menos que "lactose" ainda apareça como
    # ingrediente/aviso depois de removida a declaração.
    declarou = any(p.search(_normalizar(texto_ocr or "")) for p in _DECLARACOES_RE)
    if declarou and not re.search(r"\blactose\b", texto):
        return {
            "resultado": "seguro",
            "termos_encontrados": [],
            "termos_ignorados": sorted(set(ignorados)),
            "advertencias": advertencias,
            "declarou_sem_lactose": True,
        }

    termos_encontrados = []
    for termo in TERMOS_LACTOSE:
        termo_normalizado = _normalizar(termo)
        # \b evita falso positivo em substrings soltas; o "s?" aceita plural
        padrao = r"\b" + re.escape(termo_normalizado) + r"s?\b"
        if re.search(padrao, texto):
            termos_encontrados.append(termo)

    if termos_encontrados:
        resultado = "prejudicial"
    elif advertencias:
        resultado = "atencao"
    else:
        resultado = "seguro"

    return {
        "resultado": resultado,
        "termos_encontrados": termos_encontrados,
        "termos_ignorados": sorted(set(ignorados)),
        "advertencias": advertencias,
    }
