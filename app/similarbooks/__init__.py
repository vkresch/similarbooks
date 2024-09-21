import graphene
from functools import wraps
from pathlib import Path
from app.similarbooks.main.common import cache
from similarbooks.config import Config
from app.similarbooks.main.constants import DEBUG
from flask import Flask, request, jsonify, render_template, send_from_directory
from graphql_server.flask import GraphQLView
from collections import UserDict
from flask_mongoengine import MongoEngine
from flask_simple_captcha import CAPTCHA

# from spiders.immospider.immospider.schema import Appartment, House, Query

db = MongoEngine()

simple_captcha = CAPTCHA(config=Config.CAPTCHA_CONFIG)


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("X-RapidAPI-Proxy-Secret")
        if not token:
            return (
                jsonify(
                    {
                        "message": "API key is missing! Please register one for similarbooks.net on RapidAPI!"
                    }
                ),
                403,
            )
        if token != Config.SECRET_KEY:
            return jsonify({"message": "Invalid API key!"}), 403
        return f(*args, **kwargs)

    return decorated_function


# def graphql_view():
#     schema = graphene.Schema(
#         query=Query, types=[Appartment, House], auto_camelcase=False
#     )
#     # NOTE: This can be used for exporting the schema into a json file
#     # import json
#     # introspection_dict = schema.introspect()
#     # with open('/tmp/schema.json', 'w') as fp:
#     #     json.dump(introspection_dict, fp)
#     view = GraphQLView.as_view(
#         "graphql", schema=schema, graphiql=DEBUG, context=UserDict()
#     )
#     return token_required(view) if not DEBUG else view


# Custom filter to extract year from date string
def extract_year(date_string):
    if date_string:
        return date_string[:4]
    return None


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register the custom filter with the Flask application
    app.jinja_env.filters["extract_year"] = extract_year

    cache.init_app(
        app=app,
        config={"CACHE_TYPE": "filesystem", "CACHE_DIR": Path("/tmp/similarbooks")},
    )

    with app.app_context():
        cache.clear()

    db.init_app(app)
    simple_captcha.init_app(app)

    # app.add_url_rule(
    #     "/graphql",
    #     view_func=graphql_view(),
    # )

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("not_found.html"), 404

    # Route to serve robots.txt
    @app.route("/robots.txt")
    def serve_robots_txt():
        return send_from_directory(app.static_folder, "robots.txt")

    @app.route("/sitemap.xml")
    def serve_sitemap():
        return send_from_directory(app.static_folder, "sitemap.xml")

    from similarbooks.main.routes import main

    app.register_blueprint(main)

    return app
