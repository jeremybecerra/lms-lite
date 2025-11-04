from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from .. import db
from ..models import Curso, Leccion, EstadoCurso, Inscripcion, Progreso
from ..utils.authz import require_role

bp = Blueprint("courses", __name__)


@bp.get("/")
def list_public():
    cursos = Curso.query.filter_by(estado=EstadoCurso.PUBLICADO).all()
    return {"items": [{"id": c.id, "titulo": c.titulo, "docente_id": c.docente_id} for c in cursos]}


@bp.get("/<int:curso_id>")
def get_course(curso_id):
    c = Curso.query.get_or_404(curso_id)
    return {"id": c.id, "titulo": c.titulo, "descripcion": c.descripcion, "estado": c.estado.value, "docente_id": c.docente_id}


@bp.get("/<int:curso_id>/lessons")
def list_lessons(curso_id):
    les = Leccion.query.filter_by(curso_id=curso_id).order_by(Leccion.orden.asc()).all()
    return {"items": [{"id": leccion.id, "titulo": leccion.titulo, "orden": leccion.orden} for leccion in les]}


@bp.post("/")
@jwt_required()
@require_role("DOCENTE")
def create_course():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    c = Curso(titulo=data["titulo"], descripcion=data.get("descripcion", ""),
              estado=EstadoCurso(data.get("estado", "BORRADOR")),
              docente_id=user_id)
    db.session.add(c)
    db.session.commit()
    return {"id": c.id, "titulo": c.titulo}, 201


@bp.post("/<int:curso_id>/lessons")
@jwt_required()
@require_role("DOCENTE")
def add_lesson(curso_id):
    data = request.get_json() or {}
    le = Leccion(curso_id=curso_id, titulo=data["titulo"],
                 contenido=data.get("contenido", ""), video_url=data.get("video_url"),
                 orden=data.get("orden", 1))
    db.session.add(le)
    db.session.commit()
    return {"id": le.id, "titulo": le.titulo}, 201


@bp.post("/<int:curso_id>/publish")
@jwt_required()
@require_role("DOCENTE")
def publish_course(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    curso.estado = EstadoCurso.PUBLICADO
    db.session.commit()
    return {"ok": True}


@bp.post("/<int:curso_id>/enroll")
@jwt_required()
def enroll(curso_id):
    user_id = int(get_jwt_identity())
    ins = Inscripcion(estudiante_id=user_id, curso_id=curso_id)
    db.session.add(ins)
    db.session.commit()
    pr = Progreso(estudiante_id=user_id, curso_id=curso_id, porcentaje=0.0)
    db.session.add(pr)
    db.session.commit()
    return {"ok": True, "inscripcion_id": ins.id}
# --- Extensiones: validaciÃ³n, bÃºsqueda/paginaciÃ³n y endpoints extra ---


from flask import request
from werkzeug.exceptions import BadRequest
from app.utils.authz import docente_required


def _json_ok(data=None, status=200):
    return (data or {"ok": True}, status)


def _json_err(msg, status=400):
    return ({"error": msg}, status)


def _parse_int(name, default, min_value=None, max_value=None):
    raw = request.args.get(name, default)
    try:
        v = int(raw)
    except Exception:
        raise BadRequest(f"param '{name}' debe ser entero")
    if min_value is not None and v < min_value:
        raise BadRequest(f"param '{name}' < {min_value}")
    if max_value is not None and v > {max_value}:
        raise BadRequest(f"param '{name}' > {max_value}")
    return v


@bp.get("/")
def list_public_courses():
    """Lista cursos PUBLICADOS con paginaciÃ³n, bÃºsqueda y orden."""
    from app.models import Curso, EstadoCurso
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "titulo")
    order = request.args.get("order", "asc").lower()
    page = _parse_int("page", 1, 1)
    size = _parse_int("size", 10, 1, 100)

    query = Curso.query.filter(Curso.estado == EstadoCurso.PUBLICADO)
    if q:
        like = f"%{q}%"
        query = query.filter(Curso.titulo.ilike(like) | Curso.descripcion.ilike(like))

    valid_sorts = {"titulo": Curso.titulo, "id": Curso.id}
    col = valid_sorts.get(sort, Curso.titulo)
    if order == "desc":
        col = col.desc()
    query = query.order_by(col)

    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    data = {
        "page": page, "size": size, "total": total,
        "items": [{"id": c.id, "titulo": c.titulo, "docente_id": c.docente_id} for c in items],
    }
    return _json_ok(data)


@bp.post("/validate")
@docente_required
def validate_course_payload():
    """Valida que el payload de curso tenga titulo/descripcion correctos."""
    body = request.get_json(silent=True) or {}
    titulo = (body.get("titulo") or "").strip()
    descripcion = (body.get("descripcion") or "").strip()
    if not titulo or len(titulo) < 3:
        return _json_err("titulo requerido (>=3)")
    if len(descripcion) > 500:
        return _json_err("descripcion muy larga (<=500)")
    return _json_ok({"ok": True})


@bp.get("/mine")
@docente_required
def list_my_courses():
    """Lista cursos del docente autenticado (incluye borradores)."""
    from flask_jwt_extended import get_jwt_identity
    from app.models import Curso
    uid = int(get_jwt_identity())
    courses = Curso.query.filter_by(docente_id=uid).order_by(Curso.id.desc()).all()
    return _json_ok({
        "items": [{"id": c.id, "titulo": c.titulo, "estado": c.estado.value} for c in courses]
    })
# --- Extensiones adicionales de cursos: detalle, update, estados y reordenar lecciones ---


from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import NotFound
from sqlalchemy import func


@bp.get("/<int:course_id>")
def get_course_detail(course_id: int):
    """Detalle pÃºblico de un curso (id, titulo, estado, #lecciones)."""
    from app.models import Curso, Leccion
    c = Curso.query.get(course_id)
    if not c:
        return _json_err("curso no encontrado", 404)
    lessons = Leccion.query.filter_by(curso_id=c.id).order_by(Leccion.orden.asc()).all()
    return _json_ok({
        "id": c.id,
        "titulo": c.titulo,
        "estado": c.estado.value,
        "lecciones": [{"id": leccion.id, "titulo": leccion.titulo, "orden": leccion.orden} for leccion in lessons]
    })


@bp.patch("/<int:course_id>")
@docente_required
def update_course(course_id: int):
    """Actualiza tÃ­tulo/descripcion; verifica ownership del docente."""
    from app.models import Curso, db
    uid = int(get_jwt_identity())
    c = Curso.query.get(course_id)
    if not c:
        return _json_err("curso no encontrado", 404)
    if c.docente_id != uid:
        return _json_err("no autorizado (owner requerido)", 403)

    body = request.get_json(silent=True) or {}
    titulo = (body.get("titulo") or "").strip()
    descripcion = (body.get("descripcion") or "").strip()
    if titulo and len(titulo) < 3:
        return _json_err("titulo muy corto (>=3)")

    if titulo:
        c.titulo = titulo
    if descripcion:
        c.descripcion = descripcion

    db.session.add(c)
    db.session.commit()
    return _json_ok({"id": c.id, "titulo": c.titulo})


@bp.post("/<int:course_id>/unpublish")
@docente_required
def unpublish_course(course_id: int):
    """Pasa el curso a BORRADOR (deja de ser pÃºblico)."""
    from app.models import Curso, EstadoCurso, db
    uid = int(get_jwt_identity())
    c = Curso.query.get(course_id)
    if not c:
        return _json_err("curso no encontrado", 404)
    if c.docente_id != uid:
        return _json_err("no autorizado", 403)
    c.estado = EstadoCurso.BORRADOR
    db.session.add(c)
    db.session.commit()
    return _json_ok({"ok": True, "estado": c.estado.value})


@bp.post("/<int:course_id>/hide")
@docente_required
def hide_course(course_id: int):
    """Oculta el curso (OCULTO)."""
    from app.models import Curso, EstadoCurso, db
    uid = int(get_jwt_identity())
    c = Curso.query.get(course_id)
    if not c:
        return _json_err("curso no encontrado", 404)
    if c.docente_id != uid:
        return _json_err("no autorizado", 403)
    c.estado = EstadoCurso.OCULTO
    db.session.add(c)
    db.session.commit()
    return _json_ok({"ok": True, "estado": c.estado.value})


@bp.post("/<int:course_id>/lessons/reorder")
@docente_required
def reorder_lessons(course_id: int):
    """Reordena lecciones: body = [{"id":1,"orden":1},...]."""
    from app.models import Curso, Leccion, db
    uid = int(get_jwt_identity())
    c = Curso.query.get(course_id)
    if not c:
        return _json_err("curso no encontrado", 404)
    if c.docente_id != uid:
        return _json_err("no autorizado", 403)

    body = request.get_json(silent=True) or []
    if not isinstance(body, list):
        return _json_err("formato invÃ¡lido (se espera lista)")

    # Mapear {leccion_id -> orden}
    desired = {}
    for item in body:
        try:
            lid = int(item.get("id"))
            orden = int(item.get("orden"))
        except Exception:
            return _json_err("id/orden invÃ¡lidos (enteros)")
        desired[lid] = orden

    lessons = Leccion.query.filter_by(curso_id=c.id).all()
    for leccion in lessons:
        if leccion.id in desired:
            leccion.orden = desired[leccion.id]
            db.session.add(leccion)
    db.session.commit()

    out = [{"id": leccion.id, "titulo": leccion.titulo, "orden": leccion.orden} for leccion in
           Leccion.query.filter_by(curso_id=c.id).order_by(Leccion.orden.asc()).all()]
    return _json_ok({"items": out})


@bp.get("/<int:course_id>/metrics")
@docente_required
def course_metrics(course_id: int):
    """MÃ©tricas simples: inscritos, lecciones totales."""
    from app.models import Curso, Leccion, Inscripcion
    c = Curso.query.get(course_id)
    if not c:
        return _json_err("curso no encontrado", 404)
    total_lec = Leccion.query.filter_by(curso_id=course_id).count()
    total_ins = Inscripcion.query.filter_by(curso_id=course_id).count()
    return _json_ok({"inscritos": total_ins, "lecciones": total_lec})
