from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()
db = SQLAlchemy()
jwt = JWTManager()


def create_app(testing: bool = False):
    app = Flask(__name__, instance_relative_config=True)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt")
    if testing:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///lms.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from . import models  # noqa
    from .routes.auth import bp as auth_bp
    from .routes.courses import bp as courses_bp
    from .routes.quizzes import bp as quizzes_bp
    from .routes.me import bp as me_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(courses_bp, url_prefix="/api/courses")
    app.register_blueprint(quizzes_bp, url_prefix="/api/quizzes")
    app.register_blueprint(me_bp, url_prefix="/api/me")

    with app.app_context():
        db.create_all()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/_routes")
    def list_routes():
        return sorted([str(r) for r in app.url_map.iter_rules()])

    return app
