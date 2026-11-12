# Nutribase (Back End)

API em **Python + Flask** com banco **PostgreSQL** do aplicativo Nutribase, voltado a pessoas com intolerância à lactose.

O app (React Native, repositório [NutribaseFrontEnd](https://github.com/ClairDeLunezz/NutribaseFrontEnd)) faz o OCR do rótulo no próprio celular com o Google ML Kit e envia para esta API **apenas o texto extraído**. A API procura termos lácteos, classifica o produto em **seguro**, **atenção** ou **prejudicial**, e guarda o resultado no histórico do usuário.

Projeto de Trabalho de Graduação (TCC) da Fatec Itu "Dom Amaury Castanho".

## Sumário

- [Funcionalidades](#funcionalidades)
- [Como a análise de lactose funciona](#como-a-análise-de-lactose-funciona)
- [Tecnologias](#tecnologias)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Executando o projeto](#executando-o-projeto)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Endpoints](#endpoints)
- [Banco de dados](#banco-de-dados)
- [Segurança](#segurança)
- [Testes](#testes)
- [Produção](#produção)
- [Autores](#autores)

## Funcionalidades

- Cadastro com validação de e-mail, regras de senha e aceite da Política de Privacidade (LGPD)
- Login com token JWT e logout que invalida o token
- Recuperação de senha por código de 6 dígitos enviado por e-mail (SMTP)
- Perfil: consulta, edição de nome, upload de foto e exclusão de conta
- Análise do texto do rótulo e histórico de consultas por usuário
- Limite de requisições por rota, cabeçalhos de segurança e CORS configurável

## Como a análise de lactose funciona

A lógica fica em `app/utils/lactose_terms.py` (função `analisar_texto`) e roda sobre o texto do OCR, normalizado (minúsculas, sem acentos, sem quebras de linha, hifenização de fim de linha desfeita).

| Resultado | Quando |
| --------- | ------ |
| `prejudicial` | Há ingrediente lácteo no texto (leite, soro de leite, caseína, queijo, manteiga, *whey* etc.) |
| `atencao` | Só há aviso de contaminação cruzada, como "pode conter leite" ou "fabricado em equipamento que também processa leite" |
| `seguro` | Nada encontrado, ou o rótulo declara "sem lactose"/"zero lactose" e "lactose" não aparece como ingrediente |

Etapas da análise:

1. **Exclusões vegetais.** "Leite de coco", "manteiga de cacau", "queijo vegano", *"almond milk"* e similares são removidos antes da busca, para não gerar falso positivo.
2. **Negações.** "Sem leite", "livre de lactose", *"dairy free"* também são removidos do texto.
3. **Advertências de traços.** Frases como "pode conter", "traços de" ou *"made in a facility"* só viram advertência quando contêm termo lácteo (assim "pode conter amendoim" é ignorado). Elas saem do texto e são devolvidas à parte, e o resultado fica em `atencao`. Seguem a lógica da RDC 727/2022 da ANVISA.
4. **Declaração de ausência de lactose.** Vale para o rótulo todo (útil para leite "zero lactose" ou *whey* isolado).
5. **Busca de termos.** A lista `TERMOS_LACTOSE` (português e inglês) é procurada com fronteira de palavra e aceita plural.

Para intolerância à lactose, traços costumam ser tolerados, por isso o aviso é `atencao` e não `prejudicial`. Quem tem alergia à proteína do leite (APLV) deve evitar esses produtos, então o alerta é sempre mostrado.

## Tecnologias

| Pacote | Uso |
| ------ | --- |
| Flask 3.0 | Framework web |
| Flask-SQLAlchemy / Flask-Migrate | ORM e migrações (Alembic) |
| PostgreSQL 16 (`psycopg2-binary`) | Banco de dados, com `JSONB` no histórico |
| Flask-JWT-Extended | Autenticação por token |
| Flask-Bcrypt | Hash de senhas |
| Flask-Limiter | Limite de requisições |
| Flask-CORS | CORS |
| email-validator | Validação de e-mails |
| python-dotenv | Leitura do `.env` |

## Estrutura do projeto

```
run.py                       Ponto de entrada
app/
├── __init__.py              Fábrica da aplicação (create_app), erros e cabeçalhos de segurança
├── config.py                Configurações (Development, Production, Testing)
├── extensions.py            db, migrate, bcrypt, jwt, cors, limiter e lista de tokens revogados
├── models/
│   ├── user.py              User e PasswordResetToken
│   └── scan_history.py      ScanHistory (detalhes em JSONB)
├── routes/
│   ├── auth.py              Cadastro, login, recuperação de senha e logout
│   ├── user.py              Perfil e exclusão de conta
│   └── scan.py              Análise e histórico
└── utils/
    ├── lactose_terms.py     Detecção de lactose
    ├── email_service.py     Envio do código de recuperação (SMTP ou simulado)
    └── validators.py        E-mail, senha, imagem e limites de tamanho
migrations/                  Migrações do banco (Alembic)
tests/                       Testes da API e da análise de lactose
uploads/profile_photos/      Fotos de perfil
docker-compose.yml           PostgreSQL para desenvolvimento
.env.example                 Modelo de variáveis de ambiente
```

## Executando o projeto

### Pré-requisitos

- Python 3.10 ou superior
- Docker (recomendado, para subir o PostgreSQL) ou um PostgreSQL instalado

### Passo a passo

1. Suba o banco:

   ```bash
   docker compose up -d
   ```

   Cria um PostgreSQL em `localhost:5432` (usuário `nutribase`, senha `nutribase`, banco `nutribase_db`). Esses valores já batem com o `.env.example` e servem **só para desenvolvimento**.

2. Crie o ambiente virtual e instale as dependências:

   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Crie o `.env`:

   ```bash
   cp .env.example .env
   ```

   Gere chaves próprias para `SECRET_KEY` e `JWT_SECRET_KEY`:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. Aplique as migrações (já existem no repositório, **não** rode `flask db init` nem `flask db migrate`):

   ```bash
   flask db upgrade
   ```

5. Rode a API:

   ```bash
   python run.py
   ```

   Sobe em `http://localhost:5000`, aceitando conexões da rede local (necessário para o celular acessar). Teste:

   ```bash
   curl http://localhost:5000/health
   ```

   O celular precisa estar na mesma rede e usar o IP da máquina em `API_BASE_URL`, no front end.

### E-mail de recuperação de senha

- Com `MAIL_SIMULATION=true` (padrão no `.env.example`) nenhum e-mail é enviado: o código aparece no console da API, no formato `[E-MAIL SIMULADO] Para: ... | Código: ...`.
- Para enviar de verdade, use `MAIL_SIMULATION=false` e preencha os dados SMTP. O projeto foi configurado para o [Brevo](https://www.brevo.com) (`smtp-relay.brevo.com`, porta 587), mas qualquer SMTP serve. Na porta 465 a conexão usa SSL direto; nas demais, STARTTLS.
- Se o envio falhar, a rota responde 502 e registra o erro no log.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
| -------- | ------ | --------- |
| `FLASK_ENV` | `development` | `development`, `production` ou `testing` |
| `FLASK_DEBUG` | `0` | `1` ativa o modo debug. Use só na sua máquina, nunca com a API exposta na rede |
| `SECRET_KEY` | — | Chave do Flask. Obrigatória em produção |
| `JWT_SECRET_KEY` | — | Chave dos tokens. Obrigatória em produção |
| `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` | `60` | Validade do token |
| `DATABASE_URL` | PostgreSQL local | URL de conexão |
| `UPLOAD_FOLDER` | `uploads/profile_photos` | Pasta das fotos de perfil |
| `MAX_CONTENT_LENGTH_MB` | `5` | Tamanho máximo de requisição/upload |
| `MAIL_SIMULATION` | `true` | Se `true`, não envia e-mail (mostra o código no console) |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS` | Brevo, `587`, `true` | Servidor SMTP |
| `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM` | vazios | Credenciais e remetente |
| `PASSWORD_RESET_CODE_EXPIRES_MINUTES` | `15` | Validade do código de recuperação |
| `PASSWORD_RESET_MAX_ATTEMPTS` | `5` | Tentativas erradas antes de invalidar o código |
| `RATELIMIT_ENABLED` | `true` | Liga o limite de requisições |
| `RATELIMIT_STORAGE_URI` | `memory://` | Armazenamento dos contadores do limite |
| `CORS_ORIGINS` | `*` | Origens permitidas, separadas por vírgula (o app mobile não depende disso) |

> Nunca commite o `.env`. Ele guarda chaves e a senha do SMTP.

## Endpoints

Rotas marcadas com **Auth: sim** exigem o cabeçalho `Authorization: Bearer <access_token>` (token recebido no login). Erros vêm sempre como `{ "erro": "mensagem" }`.

| Método | Rota | Auth | Descrição |
| ------ | ---- | :--: | --------- |
| GET | `/health` | não | Verifica se a API está no ar |
| POST | `/auth/register` | não | Cadastro (RF01) |
| POST | `/auth/login` | não | Login (RF02) |
| POST | `/auth/forgot-password` | não | Envia o código de recuperação (RF03) |
| POST | `/auth/reset-password` | não | Redefine a senha com o código (RF03) |
| POST | `/auth/logout` | sim | Encerra a sessão |
| GET | `/user/profile` | sim | Dados do usuário |
| PUT | `/user/profile` | sim | Edita nome e foto (RF04) |
| DELETE | `/user/account` | sim | Exclui a conta (RF05) |
| POST | `/scan/analyze` | sim | Analisa o texto do rótulo e salva no histórico (RF06, RF07, RF08) |
| GET | `/scan/history` | sim | Lista o histórico, do mais recente ao mais antigo (RF09) |
| GET | `/scan/history/<id>` | sim | Detalhe de um item do histórico (RF09) |
| GET | `/uploads/profile_photos/<arquivo>` | não | Foto de perfil |

### Exemplos

**Cadastro** `POST /auth/register`

```json
{
  "nome": "Artur Silva",
  "email": "artur@exemplo.com",
  "senha": "Senha@123",
  "confirmar_senha": "Senha@123",
  "aceite_politica": true
}
```

Resposta `201`. `aceite_politica` precisa ser exatamente `true`. E-mail repetido retorna `409`.

**Login** `POST /auth/login`

```json
{ "email": "artur@exemplo.com", "senha": "Senha@123" }
```

Resposta `200` com `access_token` e `usuario`. Credenciais erradas retornam sempre a mesma mensagem ("E-mail ou senha inválidos."), com `401`.

**Recuperação de senha**

```json
POST /auth/forgot-password
{ "email": "artur@exemplo.com" }

POST /auth/reset-password
{ "email": "artur@exemplo.com", "codigo": "123456", "nova_senha": "NovaSenha@456" }
```

O código vale 15 minutos, é de uso único e é invalidado após 5 tentativas erradas.

**Editar perfil** `PUT /user/profile` (`multipart/form-data`)

| Campo | Obrigatório | Descrição |
| ----- | :---------: | --------- |
| `senha_atual` | sim | Confirma a identidade |
| `nome` | não | Novo nome |
| `foto` | não | Imagem PNG, JPG ou WEBP (até 5 MB) |

**Excluir conta** `DELETE /user/account`

```json
{ "senha": "Senha@123" }
```

Apaga o usuário, o histórico, os códigos de recuperação e a foto.

**Analisar escaneamento** `POST /scan/analyze` (o app manda o texto do OCR, não a imagem)

```json
{
  "texto_ocr": "INGREDIENTES: leite integral, açúcar, cacau em pó. PODE CONTER TRAÇOS DE SOJA.",
  "nome_produto": "Achocolatado XYZ"
}
```

Resposta `201`:

```json
{
  "resultado": "prejudicial",
  "termos_encontrados": ["leite", "leite integral"],
  "advertencias": [],
  "registro": {
    "id": 1,
    "nome_produto": "Achocolatado XYZ",
    "resultado": "prejudicial",
    "detalhes": {
      "texto_analisado": "...",
      "termos_encontrados": ["leite", "leite integral"],
      "termos_ignorados": [],
      "advertencias": []
    },
    "criado_em": "2026-11-12T03:00:00"
  }
}
```

Limites: texto de até 20.000 caracteres (senão `413`) e nome do produto de até 150.

### Regras de validação

- **Senha:** mínimo de 8 caracteres, com letra, número e caractere especial; máximo de 72 bytes (limite do bcrypt).
- **Nome:** até 120 caracteres. **E-mail:** até 150, validado pelo `email-validator`.
- **Foto:** extensão permitida e conteúdo conferido pelos primeiros bytes do arquivo (PNG, JPEG ou WEBP), não só pelo nome.

## Banco de dados

| Tabela | Conteúdo |
| ------ | -------- |
| `usuarios` | Nome, e-mail único, hash da senha, foto, datas e data do aceite da política |
| `historico_consultas` | Usuário, nome do produto, resultado e `detalhes` (JSONB com o texto analisado, termos, termos ignorados e advertências) |
| `password_reset_tokens` | Código de 6 dígitos, validade, se já foi usado e número de tentativas |

Excluir um usuário apaga em cascata o histórico e os códigos de recuperação. As migrações ficam em `migrations/versions/`.

Para criar uma nova migração depois de mudar um modelo:

```bash
flask db migrate -m "descrição da mudança"
flask db upgrade
```

## Segurança

- Senhas com **bcrypt**; nunca guardadas em texto puro.
- **JWT** com validade configurável. O logout e a exclusão de conta colocam o token em uma lista de revogados.
- O login não revela se o e-mail existe e gasta o mesmo tempo de verificação nos dois casos, o que dificulta enumerar contas.
- **Limite de requisições** (Flask-Limiter), por IP e, em rotas sensíveis, também por e-mail ou usuário. Exemplos: login, 10 por minuto; esqueci a senha, 3 por minuto e 5 por hora por e-mail; cadastro, 10 por hora; análise, 60 por minuto.
- Código de recuperação gerado com `secrets`, comparado em tempo constante, com validade, uso único e limite de tentativas.
- Editar perfil e excluir conta exigem a senha atual.
- Upload validado por extensão e por assinatura do arquivo, com nome aleatório e tamanho limitado.
- Cabeçalhos `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` e `Cache-Control: no-store` nas respostas JSON.
- As fotos dos rótulos nunca chegam à API: o OCR é feito no aparelho.

Limitações conhecidas:

- A lista de tokens revogados e os contadores do limite ficam **em memória**. Ao reiniciar a API, tokens de logout voltam a valer até expirarem. Com mais de um processo, cada um tem a sua lista. Para isso, use Redis (`RATELIMIT_STORAGE_URI`) e uma tabela de tokens revogados.
- `/forgot-password` informa quando o e-mail não está cadastrado (404), o que permite descobrir quais e-mails têm conta. O limite de requisições reduz esse risco, mas não o elimina.

## Testes

Os testes usam **SQLite em memória**, então não precisam do PostgreSQL:

```bash
python -m unittest discover -s tests -v
```

- `tests/test_api.py`: cadastro, login, logout, recuperação de senha, perfil, upload e histórico
- `tests/test_lactose_terms.py`: casos da análise (exclusões vegetais, negações, advertências, inglês etc.)

## Produção

Com `FLASK_ENV=production`:

- A API **recusa iniciar** se `SECRET_KEY` ou `JWT_SECRET_KEY` estiverem vazias, com o valor padrão ou começando com `troque`.
- O e-mail é sempre enviado de verdade (`MAIL_SIMULATION` é forçado para `false`).
- Não use `python run.py` (servidor de desenvolvimento). Use um servidor WSGI, como `gunicorn "run:app"`, atrás de um proxy com **HTTPS**.
- Troque a senha do banco, restrinja `CORS_ORIGINS` e use armazenamento persistente (ou de objetos) para `uploads/`.
- Faça backup do PostgreSQL.

## Autores

- Artur Cruz
- Pietro 


Orientador: Prof. Fabrício Tonetto Londero, Fatec Itu, 2026.
