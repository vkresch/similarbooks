import graphene
from functools import wraps
from pathlib import Path
from app.similarbooks.main.common import cache
from similarbooks.config import Config
from app.similarbooks.main.constants import DEBUG
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    send_from_directory,
    redirect,
)
from graphql_server.flask import GraphQLView
from collections import UserDict
from flask_mongoengine import MongoEngine
from flask_simple_captcha import CAPTCHA
from spiders.bookspider.bookspider.schema import Book, Query

db = MongoEngine()

simple_captcha = CAPTCHA(config=Config.CAPTCHA_CONFIG)


def graphql_view():
    schema = graphene.Schema(query=Query, types=[Book], auto_camelcase=False)
    # NOTE: This can be used for exporting the schema into a json file
    # import json
    # introspection_dict = schema.introspect()
    # with open('/tmp/schema.json', 'w') as fp:
    #     json.dump(introspection_dict, fp)
    view = GraphQLView.as_view(
        "graphql", schema=schema, graphiql=DEBUG, context=UserDict()
    )
    return view


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

    app.add_url_rule(
        "/graphql",
        view_func=graphql_view(),
    )

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("not_found.html"), 404

    # Route to serve robots.txt
    @app.route("/robots.txt")
    def serve_robots_txt():
        return send_from_directory(app.static_folder, "robots.txt")

    @app.route("/sitemap.xml")
    def serve_sitemap():
        return redirect("/sitemap_index.xml", code=301)

    @app.route("/sitemap_index.xml")
    def sitemap_index():
        # Serve the sitemap_index.xml file from the SITEMAP_DIR
        return send_from_directory(app.static_folder, "sitemap_index.xml")

    @app.route("/<filename>")
    def serve_sitemaps(filename):
        # Serve the individual sitemap files (e.g., sitemap_books_1.xml, sitemap_books_2.xml)
        return send_from_directory(app.static_folder, filename)

    from similarbooks.main.routes import main

    app.register_blueprint(main)

    return app
