
import io
import os
import shutil
import tempfile
import unittest

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from app import create_app
from app.config import config_by_name
from app.extensions import db, jwt_blocklist, limiter
from app.models import PasswordResetToken, User


@compiles(JSONB, "sqlite")
def _jsonb_no_sqlite(_type, _compiler, **_kw): 
    return "JSON"


PNG_MINIMO = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
SENHA = "Senha@123"


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pasta_uploads = tempfile.mkdtemp()
        cfg = config_by_name["testing"]
        cfg.SQLALCHEMY_DATABASE_URI = "sqlite://"
        cfg.SQLALCHEMY_ENGINE_OPTIONS = {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        }
        cfg.UPLOAD_FOLDER = cls.pasta_uploads
        cfg.MAIL_SIMULATION = True
        cfg.RATELIMIT_ENABLED = True 
        cls.app = create_app("testing")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.pasta_uploads, ignore_errors=True)

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        jwt_blocklist.clear()
        limiter.enabled = False
        self.c = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        for f in os.listdir(self.pasta_uploads):
            os.remove(os.path.join(self.pasta_uploads, f))

    # -------- helpers --------
    def registrar(self, email="a@teste.com", senha=SENHA, nome="Ana"):
        return self.c.post("/auth/register", json={
            "nome": nome, "email": email, "senha": senha, "confirmar_senha": senha})

    def logar(self, email="a@teste.com", senha=SENHA):
        r = self.c.post("/auth/login", json={"email": email, "senha": senha})
        return r

    def auth(self, email="a@teste.com"):
        self.registrar(email)
        token = self.logar(email).get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


class TestCadastroLogin(ApiTestCase):
    def test_fluxo_basico(self):
        self.assertEqual(self.registrar().status_code, 201)
        self.assertEqual(self.registrar().status_code, 409)
        self.assertEqual(self.logar().status_code, 200)
        self.assertEqual(self.logar(senha="errada1").status_code, 401)
        self.assertEqual(self.logar(email="x@x.com").status_code, 401)

    def test_regra_de_senha_no_cadastro(self):
        for fraca in ["abc@1", "senhasenha", "senha1234", "senha@@@@", "12345678!", "Senha 1234"]:
            with self.subTest(senha=fraca):
                r = self.registrar(senha=fraca)
                self.assertEqual(r.status_code, 400)
                self.assertIn("8 caracteres", r.get_json()["erro"])
        for forte in ["Senha@123", "abcdef1!", "Maçã#2026x"]:
            with self.subTest(senha=forte):
                self.assertEqual(self.registrar(email=f"{forte[:3]}@teste.com", senha=forte).status_code, 201)

    def test_conta_antiga_com_senha_fraca_ainda_consegue_logar(self):
        u = User(nome="Antigo", email="antigo@teste.com")
        u.set_senha("123456")  # criada antes da regra nova
        db.session.add(u)
        db.session.commit()
        self.assertEqual(self.logar("antigo@teste.com", "123456").status_code, 200)

    def test_senha_longa_demais_nao_gera_500(self):
        longa = "Aa1!" * 19  # 76 bytes
        self.assertEqual(self.registrar(senha=longa).status_code, 400)
        self.registrar()
        self.assertEqual(self.logar(senha=longa).status_code, 401)

    def test_limites_de_tamanho(self):
        self.assertEqual(self.registrar(nome="n" * 121).status_code, 400)
        self.assertEqual(self.registrar(email=("a" * 150) + "@teste.com").status_code, 400)

    def test_cabecalhos_de_seguranca(self):
        r = self.c.get("/health")
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r.headers["Cache-Control"], "no-store")

    def test_erros_em_json(self):
        r = self.c.get("/auth/login")  
        self.assertEqual(r.status_code, 405)
        self.assertIn("erro", r.get_json())


class TestLimiteDeTentativas(ApiTestCase):
    def test_login_recebe_429_depois_de_10_tentativas(self):
        self.registrar()
        limiter.enabled = True
        limiter.reset()
        try:
            respostas = [self.logar(senha="errada1") for _ in range(12)]
        finally:
            limiter.enabled = False
        self.assertEqual([r.status_code for r in respostas[:10]], [401] * 10)
        self.assertEqual([r.status_code for r in respostas[10:]], [429, 429])
        self.assertIn("erro", respostas[10].get_json())


class TestRecuperacaoDeSenha(ApiTestCase):
    def codigo_atual(self):
        return PasswordResetToken.query.order_by(PasswordResetToken.id.desc()).first()

    def reset(self, codigo, senha="NovaSenha@1", email="a@teste.com"):
        return self.c.post("/auth/reset-password",
                           json={"email": email, "codigo": codigo, "nova_senha": senha})

    def test_fluxo_completo(self):
        self.registrar()
        r = self.c.post("/auth/forgot-password", json={"email": "a@teste.com"})
        self.assertEqual(r.status_code, 200)
        t = self.codigo_atual()
        self.assertEqual(len(t.codigo), 6)
        self.assertEqual(self.reset(t.codigo).status_code, 200)
        self.assertEqual(self.logar(senha="NovaSenha@1").status_code, 200)
        self.assertEqual(self.reset(t.codigo).status_code, 400) 

    def test_email_inexistente_no_reset_nao_revela_nada(self):
        r = self.reset("123456", email="naoexiste@teste.com")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["erro"], "Código inválido ou expirado.")

    def test_codigo_e_descartado_apos_5_erros(self):
        self.registrar()
        self.c.post("/auth/forgot-password", json={"email": "a@teste.com"})
        t = self.codigo_atual()
        certo = t.codigo
        errado = "000000" if certo != "000000" else "111111"
        for _ in range(5):
            self.assertEqual(self.reset(errado).status_code, 400)

        self.assertEqual(self.reset(certo).status_code, 400)
        self.assertEqual(self.logar(senha=SENHA).status_code, 200)  

    def test_novo_pedido_invalida_o_codigo_anterior(self):
        self.registrar()
        self.c.post("/auth/forgot-password", json={"email": "a@teste.com"})
        antigo = self.codigo_atual().codigo
        self.c.post("/auth/forgot-password", json={"email": "a@teste.com"})
        novo = self.codigo_atual().codigo
        if antigo != novo:
            self.assertEqual(self.reset(antigo).status_code, 400)
        self.assertEqual(self.reset(novo).status_code, 200)

    def test_senha_nova_curta_nao_gasta_o_codigo(self):
        self.registrar()
        self.c.post("/auth/forgot-password", json={"email": "a@teste.com"})
        codigo = self.codigo_atual().codigo
        self.assertEqual(self.reset(codigo, senha="senhafraca").status_code, 400)
        self.assertEqual(self.reset(codigo).status_code, 200)


class TestFotoDePerfil(ApiTestCase):
    def enviar_foto(self, h, conteudo, nome="foto.png"):
        return self.c.put("/user/profile", headers=h, content_type="multipart/form-data",
                          data={"senha_atual": SENHA, "foto": (io.BytesIO(conteudo), nome)})

    def test_rejeita_arquivo_que_nao_e_imagem(self):
        h = self.auth()
        r = self.enviar_foto(h, b"<?php echo 'oi'; ?>", "foto.jpg")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(os.listdir(self.pasta_uploads), [])

    def test_aceita_png_e_troca_apaga_a_foto_antiga(self):
        h = self.auth()
        r1 = self.enviar_foto(h, PNG_MINIMO)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(len(os.listdir(self.pasta_uploads)), 1)
        r2 = self.enviar_foto(h, PNG_MINIMO)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(len(os.listdir(self.pasta_uploads)), 1) 
        self.assertNotEqual(r1.get_json()["usuario"]["foto_perfil"],
                            r2.get_json()["usuario"]["foto_perfil"])

    def test_extensao_vem_do_conteudo_nao_do_nome(self):
        h = self.auth()
        r = self.enviar_foto(h, PNG_MINIMO, "foto.jpg")  # PNG disfarçado de .jpg
        self.assertTrue(r.get_json()["usuario"]["foto_perfil"].endswith(".png"))

    def test_senha_errada_nao_altera_nada(self):
        h = self.auth()
        r = self.c.put("/user/profile", headers=h, content_type="multipart/form-data",
                       data={"senha_atual": "errada1", "nome": "Outro"})
        self.assertEqual(r.status_code, 401)

    def test_nome_longo_demais(self):
        h = self.auth()
        r = self.c.put("/user/profile", headers=h, content_type="multipart/form-data",
                       data={"senha_atual": SENHA, "nome": "n" * 121})
        self.assertEqual(r.status_code, 400)

    def test_excluir_conta_apaga_foto_e_dados(self):
        h = self.auth()
        self.enviar_foto(h, PNG_MINIMO)
        self.c.post("/scan/analyze", headers=h, json={"texto_ocr": "leite", "nome_produto": "X"})
        self.assertEqual(len(os.listdir(self.pasta_uploads)), 1)
        r = self.c.delete("/user/account", headers=h, json={"senha": SENHA})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(os.listdir(self.pasta_uploads), [])
        self.assertEqual(User.query.count(), 0)
        self.assertEqual(self.c.get("/user/profile", headers=h).status_code, 401)  # token revogado


class TestEscaneamento(ApiTestCase):
    def test_leite_vegetal_nao_e_prejudicial(self):
        h = self.auth()
        r = self.c.post("/scan/analyze", headers=h,
                        json={"texto_ocr": "Ingredientes: água, leite de coco", "nome_produto": "Bebida"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["resultado"], "seguro")
        hist = self.c.get("/scan/history", headers=h).get_json()
        self.assertEqual(hist[0]["detalhes"]["termos_ignorados"], ["leite de coco"])

    def test_leite_de_verdade_continua_prejudicial(self):
        h = self.auth()
        r = self.c.post("/scan/analyze", headers=h,
                        json={"texto_ocr": "leite integral, açúcar", "nome_produto": "Choco"})
        self.assertEqual(r.get_json()["resultado"], "prejudicial")

    def test_validacoes(self):
        h = self.auth()
        post = lambda **kw: self.c.post("/scan/analyze", headers=h, json=kw)
        self.assertEqual(post(texto_ocr="", nome_produto="X").status_code, 400)
        self.assertEqual(post(texto_ocr="leite", nome_produto="").status_code, 400)
        self.assertEqual(post(texto_ocr="leite", nome_produto="p" * 151).status_code, 400)
        self.assertEqual(post(texto_ocr="a" * 20001, nome_produto="X").status_code, 413)

    def test_historico_so_do_proprio_usuario(self):
        h1 = self.auth("a@teste.com")
        h2 = self.auth("b@teste.com")
        self.c.post("/scan/analyze", headers=h1, json={"texto_ocr": "leite", "nome_produto": "A"})
        self.assertEqual(len(self.c.get("/scan/history", headers=h1).get_json()), 1)
        self.assertEqual(len(self.c.get("/scan/history", headers=h2).get_json()), 0)
        self.assertEqual(self.c.get("/scan/history/1", headers=h2).status_code, 404)

    def test_sem_token_da_401(self):
        self.assertEqual(self.c.get("/scan/history").status_code, 401)


class TestProducao(unittest.TestCase):
    def test_producao_exige_chaves_proprias(self):
        os.environ.pop("SECRET_KEY", None)
        os.environ.pop("JWT_SECRET_KEY", None)
        with self.assertRaises(RuntimeError):
            create_app("production")


if __name__ == "__main__":
    unittest.main()
