import unittest

from app.utils.lactose_terms import analisar_texto


def resultado(texto):
    return analisar_texto(texto)["resultado"]


class TestFalsosPositivos(unittest.TestCase):
    """Rótulos SEM lactose que não podem ser marcados como prejudiciais."""

    def test_leites_vegetais(self):
        for texto in [
            "INGREDIENTES: água, leite de coco, açúcar",
            "Ingredientes: amêndoas, leite de amêndoas",
            "Bebida de aveia: água, aveia, leite de aveia",
            "leite de soja em pó",
            "leite de arroz, sal",
            "leite de castanha de caju",
            "leite de castanhas",
            "Leite vegetal à base de amendoim",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(resultado(texto), "seguro")

    def test_manteigas_vegetais(self):
        for texto in [
            "chocolate: massa de cacau, manteiga de cacau, açúcar",
            "manteiga de karité, manteiga de amendoim",
            "manteiga de cupuaçu",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(resultado(texto), "seguro")

    def test_queijo_e_iogurte_vegetais(self):
        self.assertEqual(resultado("queijo vegano de castanha, sal"), "seguro")
        self.assertEqual(resultado("iogurte de soja, açúcar"), "seguro")
        self.assertEqual(resultado("creme de coco, água"), "seguro")

    def test_declaracao_sem_lactose(self):
        for texto in [
            "ZERO LACTOSE. Ingredientes: água, açúcar",
            "Produto sem lactose. Ingredientes: farinha de trigo",
            "NÃO CONTÉM LACTOSE. farinha, sal",
            "isento de lactose, sal",
            "Livre de lactose",
            "0% lactose",
            "lactose zero",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(resultado(texto), "seguro")

    def test_palavras_parecidas(self):
        # \b impede casar dentro de outras palavras
        self.assertEqual(resultado("natalino, mantegal, filmes"), "seguro")


class TestContinuaDetectando(unittest.TestCase):
    """Nada disso pode virar falso negativo (é o erro perigoso)."""

    def test_termos_basicos(self):
        for texto in [
            "INGREDIENTES: leite integral, açúcar, cacau",
            "contém lactose",
            "soro de leite em pó",
            "caseinato de sódio",
            "queijo mussarela",
            "Requeijão cremoso",
            "ricota, parmesão",
            "chantilly",
            "creme de leite",
            "doce de leite",
            "Whey protein isolado",
            "composto lácteo",
            "bebida láctea",
            "leites e derivados",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(resultado(texto), "prejudicial")

    def test_quebra_de_linha_do_ocr(self):
        self.assertEqual(resultado("soro de\nleite em\npó"), "prejudicial")
        self.assertEqual(resultado("lac-\ntose"), "prejudicial")
        self.assertEqual(resultado("LEITE   \n  INTEGRAL"), "prejudicial")

    def test_vegetal_junto_com_leite_de_verdade(self):
        # exclui só a frase vegetal; o leite real continua sendo detectado
        r = analisar_texto("leite de coco, leite em pó, açúcar")
        self.assertEqual(r["resultado"], "prejudicial")
        self.assertIn("leite em po", r["termos_encontrados"])

    def test_sem_lactose_mas_com_leite(self):
        # declaração "zero/sem lactose" vale para o rótulo todo
        self.assertEqual(resultado("sem lactose. Ingredientes: soro de leite"), "seguro")
        self.assertEqual(resultado("Whey Protein Isolado Zero Lactose. proteína do soro do leite"), "seguro")
        self.assertEqual(resultado("leite desnatado lactose free"), "seguro")
        # ...mas "lactose" como ingrediente ou aviso continua valendo
        self.assertEqual(resultado("zero lactose. Ingredientes: lactose, açúcar"), "prejudicial")
        self.assertEqual(resultado("whey protein concentrado"), "prejudicial")

    def test_lactose_como_ingrediente_apesar_de_zero_na_frase(self):
        self.assertEqual(resultado("ingredientes: lactose, açúcar. 0% gordura"), "prejudicial")

    def test_retorna_ignorados_para_transparencia(self):
        r = analisar_texto("leite de coco")
        self.assertEqual(r["resultado"], "seguro")
        self.assertEqual(r["termos_ignorados"], ["leite de coco"])


class TestEntradasVazias(unittest.TestCase):
    def test_vazio_e_none(self):
        self.assertEqual(resultado(""), "seguro")
        self.assertEqual(resultado(None), "seguro")


if __name__ == "__main__":
    unittest.main()


class TestContaminacaoCruzada(unittest.TestCase):
    """Advertência de traços (RDC 727/2022) não é ingrediente: vira "atencao"."""

    def test_pode_conter_leite_vira_atencao(self):
        for texto in [
            "Ingredientes: farinha de trigo, açúcar. ALÉRGICOS: PODE CONTER LEITE.",
            "Ingredientes: farinha, açúcar. Alérgicos: pode conter leite, soja e ovo.",
            "Ingredientes: cacau, açúcar. Contém traços de leite.",
            "Ingredientes: água, açúcar. Pode conter traços de leite e castanhas.",
            "Ingredientes: arroz. Fabricado em equipamento que também processa leite.",
            "Ingredientes: milho. Produzido em linha que processa derivados do leite.",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(resultado(texto), "atencao")

    def test_ingrediente_real_continua_prejudicial(self):
        # "contém leite" é declaração de ingrediente, não de traços
        self.assertEqual(
            resultado("Ingredientes: leite em pó, açúcar. ALÉRGICOS: CONTÉM LEITE."), "prejudicial"
        )
        self.assertEqual(
            resultado("ALÉRGICOS: CONTÉM LEITE E DERIVADOS. PODE CONTER SOJA."), "prejudicial"
        )
        # ingrediente lácteo + aviso de traços continua prejudicial
        self.assertEqual(
            resultado("Ingredientes: farinha, manteiga. Pode conter leite."), "prejudicial"
        )
        # OCR sem pontuação: o trecho da advertência para em "ingredientes"
        self.assertEqual(
            resultado("pode conter leite ingredientes: leite em po, acucar"), "prejudicial"
        )

    def test_advertencia_de_outro_alergeno_nao_muda_nada(self):
        self.assertEqual(resultado("Ingredientes: amendoim, sal. Pode conter soja."), "seguro")
        self.assertEqual(resultado("Fabricado em São Paulo. Ingredientes: arroz, sal."), "seguro")

    def test_advertencia_fica_registrada(self):
        r = analisar_texto("Ingredientes: farinha. Alérgicos: pode conter leite.")
        self.assertEqual(r["resultado"], "atencao")
        self.assertEqual(r["advertencias"], ["pode conter leite"])
        self.assertEqual(r["termos_encontrados"], [])

    def test_declaracao_sem_lactose_tem_prioridade(self):
        r = analisar_texto("Zero lactose. Pode conter leite.")
        self.assertEqual(r["resultado"], "seguro")
        self.assertEqual(r["advertencias"], ["pode conter leite"])


class TestRotulosEmIngles(unittest.TestCase):
    """Suplementos e produtos importados trazem avisos e ingredientes em inglês."""

    def test_aviso_de_instalacao_compartilhada_vira_atencao(self):
        for texto in [
            "ALLERGEN WARNING: This product was made in a facility that also processes milk, egg, peanuts and soy.",
            "May contain milk and soy.",
            "Contains traces of milk.",
            "Manufactured in a facility that processes peanuts, tree nuts and milk.",
            "Produced on shared equipment with milk products.",
            "made in a facility that also\nprocesses milk, egg, peanuts and soy.",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(resultado(texto), "atencao")

    def test_rotulo_de_creatina_em_dois_idiomas(self):
        texto = (
            "INGREDIENTS: Creatine Monohydrate. GLUTEN FREE. ALLERGEN WARNING: This product was made in a "
            "facility that also processes milk, egg, peanuts and soy. INGREDIENTES: Creatina Monohidratada. "
            "NÃO CONTÉM GLÚTEN. ALÉRGICOS: PODE CONTER AMENDOIM, LEITE, SOJA E OVO."
        )
        r = analisar_texto(texto)
        self.assertEqual(r["resultado"], "atencao")
        self.assertEqual(r["termos_encontrados"], [])
        self.assertEqual(len(r["advertencias"]), 2)

    def test_ingrediente_em_ingles_continua_prejudicial(self):
        for texto in [
            "Ingredients: milk powder, sugar. Made in a facility that also processes soy.",
            "Ingredients: processed cheese, sugar. May contain soy.",
            "CONTAINS: MILK, SOY",
            "Ingredients: whey protein, cocoa. Made in a facility that also processes soy.",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(resultado(texto), "prejudicial")

    def test_made_in_pais_nao_e_aviso(self):
        self.assertEqual(resultado("Made in Brazil. Ingredients: creatine monohydrate."), "seguro")
        self.assertEqual(resultado("Made in Italy with fresh milk and butter"), "prejudicial")

    def test_vegetais_e_livres_de_leite_em_ingles(self):
        for texto in [
            "Ingredients: coconut milk, water",
            "almond milk, sugar",
            "Ingredients: cocoa butter, sugar",
            "peanut butter, salt",
            "Dairy free. Ingredients: oat milk, water",
            "Milk-free formula",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(resultado(texto), "seguro")
