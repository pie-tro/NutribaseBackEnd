# Nutribase — Back-end

API em **Python + Flask** com banco **PostgreSQL**, desenvolvida para o app Nutribase
(TG - Faculdade de Tecnologia de Itu "Dom Amaury Castanho").

O front-end (React Native) faz o OCR do rótulo com Google ML Kit e manda **apenas o
texto extraído** para esta API, que verifica a presença de termos relacionados à
lactose e devolve o resultado.

## 1. Pré-requisitos

- Python 3.10+
- Docker (recomendado, para subir o PostgreSQL sem precisar instalar nada na máquina)

## 2. Subindo o banco de dados (PostgreSQL via Docker)

Como você ainda não tem o PostgreSQL configurado, o jeito mais rápido é usar o
`docker-compose.yml` incluído no projeto:

```bash
docker compose up -d
```

Isso sobe um PostgreSQL em `localhost:5432` com:
- usuário: `nutribase`
- senha: `nutribase`
- banco: `nutribase_db`

(Esses valores já batem com o `.env.example`. Se preferir instalar o PostgreSQL
direto na máquina em vez de Docker, só ajuste a `DATABASE_URL` no `.env`.)

## 3. Configurando o ambiente Python

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env          # ajuste se necessário
```

## 4. Criando as tabelas no banco

```bash
flask db init        # só na primeira vez
flask db migrate -m "estrutura inicial"
flask db upgrade
```

## 5. Rodando a API

```bash
python run.py
```

A API sobe em `http://localhost:5000`. Teste com:

```bash
curl http://localhost:5000/health
```

## 6. Endpoints disponíveis

| Rota | Método | Auth | RF |
|---|---|---|---|
| `/auth/register` | POST | não | RF01 |
| `/auth/login` | POST | não | RF02 |
| `/auth/forgot-password` | POST | não | RF03 |
| `/auth/reset-password` | POST | não | RF03 |
| `/auth/logout` | POST | sim | Logoff |
| `/user/profile` | GET | sim | — |
| `/user/profile` | PUT | sim | RF04 |
| `/user/account` | DELETE | sim | RF05 |
| `/scan/analyze` | POST | sim | RF06/RF07/RF08 |
| `/scan/history` | GET | sim | RF09 |
| `/scan/history/<id>` | GET | sim | RF09 |

Rotas com "Auth: sim" exigem o header:
```
Authorization: Bearer <access_token>
```
(token recebido no login)

### Exemplos rápidos

**Cadastro**
```json
POST /auth/register
{
  "nome": "Artur Silva",
  "email": "artur@exemplo.com",
  "senha": "minhasenha123",
  "confirmar_senha": "minhasenha123"
}
```

**Login**
```json
POST /auth/login
{ "email": "artur@exemplo.com", "senha": "minhasenha123" }
```
Retorna `access_token` — usar nas próximas chamadas.

**Analisar escaneamento** (o front manda o texto do OCR, não a imagem)
```json
POST /scan/analyze
{
  "texto_ocr": "INGREDIENTES: leite integral, açúcar, cacau em pó",
  "nome_produto": "Achocolatado XYZ"
}
```
Resposta:
```json
{
  "resultado": "prejudicial",
  "termos_encontrados": ["leite", "leite integral"],
  "registro": { "...": "..." }
}
```

## 7. O que ainda falta decidir/ajustar com o front-end

- Confirmar o **formato exato do JSON** que o React Native vai mandar em cada
  chamada (nomes dos campos podem ser ajustados para bater com o que já está
  implementado no front).
- Confirmar como o front vai enviar a **foto de perfil** (a rota `PUT /user/profile`
  já está pronta para receber `multipart/form-data` com um campo `foto`).
- E-mail de recuperação de senha está **simulado** (o código aparece no console/log
  do back-end, não é enviado de verdade). Trocar isso é uma alteração pontual em
  `app/utils/email_service.py` quando vocês decidirem o provedor.

## 8. Estrutura do projeto

```
nutribase-backend/
├── app/
│   ├── __init__.py          # app factory
│   ├── config.py            # configurações via .env
│   ├── extensions.py        # db, jwt, bcrypt, cors
│   ├── models/
│   │   ├── user.py          # User, PasswordResetToken
│   │   └── scan_history.py  # ScanHistory (histórico em JSONB)
│   ├── routes/
│   │   ├── auth.py          # cadastro, login, esqueci senha, logoff
│   │   ├── user.py          # perfil, editar, excluir conta
│   │   └── scan.py          # análise de lactose + histórico
│   └── utils/
│       ├── lactose_terms.py # lógica de detecção de lactose (RF07)
│       ├── email_service.py # envio de e-mail (simulado por enquanto)
│       └── validators.py
├── uploads/profile_photos/  # fotos de perfil salvas localmente (RF04)
├── docker-compose.yml       # sobe o PostgreSQL
├── requirements.txt
├── .env.example
└── run.py
```
