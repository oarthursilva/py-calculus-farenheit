from apifairy import APIFairy
from cfenv import AppEnv
from flask import Flask, request, abort
from sap import xssec

from config import Config

apifairy = APIFairy()
env = AppEnv()


def create_app(config_class=Config):
    app = Flask(__name__)

    app.config.from_object(config_class)
    apifairy.init_app(app)

    # blueprints
    from controllers import fahrenheit
    app.register_blueprint(fahrenheit, url_prefix='/to')

    @app.before_request
    def before_request():
        if 'authorization' not in request.headers:
            abort(403)

        service = env.get_service(name='py-uaa')

        if service is not None:
            uaa_service = service.credentials
            access_token = request.headers.get('authorization')[7:]
            security_context = xssec.create_security_context(access_token, uaa_service)
            isAuthorized = security_context.check_scope('uaa.resource')
        else:
            # Ambiente local sem instância `py-uaa`: descomenta a linha seguinte
            # (`isAuthorized = True`) para aceitar pedidos só com cabeçalho
            # Authorization presente, sem validar JWT. Mantém `False` em CF
            # se o binding falhar (API fechada). Não comites `True` para produção.
            # isAuthorized = True
            isAuthorized = False

        if not isAuthorized:
            abort(403)

    @app.route('/')
    def index():
        return 'Conversao Fahrenheit'

    @app.after_request
    def after_request(res):
        request.get_data()
        return res

    return app
