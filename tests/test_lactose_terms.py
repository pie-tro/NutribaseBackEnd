import unittest

from app.utils.lactose_terms import analisar_texto


def resultado(texto):
    return analisar_texto(texto)["resultado"]


class TestFalsosPositivos(unittest.TestCase):


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

        self.assertEqual(resultado("natalino, mantegal, filmes"), "seguro")


class TestContinuaDetectando(unittest.TestCase):


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
 
        r = analisar_texto("leite de coco, leite em pó, açúcar")
        self.assertEqual(r["resultado"], "prejudicial")
        self.assertIn("leite em po", r["termos_encontrados"])

    def test_sem_lactose_mas_com_leite(self):
   
        self.assertEqual(resultado("sem lactose. Ingredientes: soro de leite"), "seguro")
        self.assertEqual(resultado("Whey Protein Isolado Zero Lactose. proteína do soro do leite"), "seguro")
        self.assertEqual(resultado("leite desnatado lactose free"), "seguro")

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

        self.assertEqual(
            resultado("Ingredientes: leite em pó, açúcar. ALÉRGICOS: CONTÉM LEITE."), "prejudicial"
        )
        self.assertEqual(
            resultado("ALÉRGICOS: CONTÉM LEITE E DERIVADOS. PODE CONTER SOJA."), "prejudicial"
        )

        self.assertEqual(
            resultado("Ingredientes: farinha, manteiga. Pode conter leite."), "prejudicial"
        )

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
