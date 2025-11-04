from flask import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from .. import db
from ..models import Usuario, Inscripcion, Curso, Progreso

bp = Blueprint("me", __name__)

@bp.get("/profile")
@jwt_required()
def profile():
    uid = int(get_jwt_identity())
    claims = get_jwt()
    u = Usuario.query.get_or_404(uid)
    return {"id": u.id, "email": u.email, "rol": claims.get("rol")}

@bp.get("/enrollments")
@jwt_required()
def my_enrollments():
    uid = int(get_jwt_identity())
    ins = (db.session.query(Inscripcion, Curso)
           .join(Curso, Curso.id == Inscripcion.curso_id)
           .filter(Inscripcion.estudiante_id == uid)
           .all())
    items = [{"inscripcion_id": i.id, "curso_id": c.id, "curso_titulo": c.titulo} for i, c in ins]
    return {"items": items}
