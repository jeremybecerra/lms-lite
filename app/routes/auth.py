from flask import Blueprint, request
from flask_jwt_extended import create_access_token
from .. import db
from ..models import Usuario, Rol
from ..utils.security import hash_password, verify_password

bp = Blueprint("auth", __name__)


@bp.post("/register")
def register():
    data = request.get_json() or {}
    email = data.get("email")
    pwd = data.get("password")
    rol = data.get("rol", "ESTUDIANTE")
    if not email or not pwd:
        return {"error": "email y password son obligatorios"}, 400
    if Usuario.query.filter_by(email=email).first():
        return {"error": "email ya registrado"}, 409
    user = Usuario(email=email, password_hash=hash_password(pwd), rol=Rol(rol))
    db.session.add(user)
    db.session.commit()
    return {"id": user.id, "email": user.email, "rol": user.rol.value}, 201


@bp.post("/login")
def login():
    data = request.get_json() or {}
    email = data.get("email")
    pwd = data.get("password")
    user = Usuario.query.filter_by(email=email).first()
    if not user or not verify_password(pwd, user.password_hash):
        return {"error": "credenciales inválidas"}, 401
    # identidad como STRING; rol en claims adicionales
    token = create_access_token(identity=str(user.id),
                                additional_claims={"rol": user.rol.value})
    return {"access_token": token}
