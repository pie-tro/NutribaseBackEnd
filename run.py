import os

from app import create_app

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    # host 0.0.0.0 é necessário para o celular acessar a API pela rede local.
    # O modo debug (depurador interativo do Werkzeug) NÃO deve ficar ligado
    # quando a API está exposta na rede: só ative com FLASK_DEBUG=1.
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug)
