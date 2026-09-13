from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()
cors = CORS()

# Conjunto simples em memória para tokens invalidados no logoff (RF: Fazer Logoff).
# Como o projeto roda em um único processo/worker durante o desenvolvimento e o TG,
# isso é suficiente. Se subir para produção com múltiplos workers, trocar por uma
# tabela no banco (ex: TokenBlocklist) ou Redis.
jwt_blocklist = set()


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return jwt_payload["jti"] in jwt_blocklist
