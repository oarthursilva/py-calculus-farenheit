from apifairy import APIFairy
from cfenv import AppEnv
from flask import Flask, request, abort, g
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

    app.register_blueprint(fahrenheit, url_prefix="/to")

    @app.before_request
    def before_request():
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            abort(401)

        service = env.get_service(name="py-uaa")

        if service is None:
            abort(403)  # keep the local-dev switch you already have if needed

        creds = service.credentials

        try:
            ctx = xssec.create_security_context(auth[7:], creds)
        except Exception:
            abort(401)

        if not ctx.check_scope(f"{creds['xsappname']}.Calculate"):
            abort(403)

        g.security_context = ctx

    @app.route("/")
    def index():
        return "Conversao Fahrenheit"

    @app.after_request
    def after_request(res):
        request.get_data()
        return res

    return app
