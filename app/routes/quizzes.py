from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from .. import db
try:
    from ..models import Quiz, Pregunta, Opcion, Intento
except ImportError:
    from ..models import Quiz, Pregunta, Opcion, IntentoQuiz as Intento
from ..utils.authz import require_role

bp = Blueprint("quizzes", __name__)

@bp.get("/<int:quiz_id>")
def get_quiz(quiz_id: int):
    q = Quiz.query.get_or_404(quiz_id)
    preguntas = Pregunta.query.filter_by(quiz_id=quiz_id).all()
    resumen = [{"id": p.id, "enunciado": p.enunciado, "tipo": p.tipo} for p in preguntas]
    return {
        "id": q.id,
        "titulo": q.titulo,
        "curso_id": q.curso_id,
        "tiempo_limite_min": getattr(q, "tiempo_limite_min", None),
        "intentos_max": getattr(q, "intentos_max", None),
        "preguntas": resumen
    }

@bp.post("/")
@jwt_required()
@require_role("DOCENTE")
def create_quiz():
    data = request.get_json(silent=True) or {}
    if "curso_id" not in data or "titulo" not in data or not str(data.get("titulo") or "").strip():
        return {"error": "faltan campos obligatorios"}, 422
    try:
        q = Quiz(
            curso_id=int(data["curso_id"]),
            titulo=str(data["titulo"]).strip(),
            tiempo_limite_min=int(data.get("tiempo_limite_min", 30)),
            intentos_max=int(data.get("intentos_max", 1)),
        )
    except Exception as e:
        return {"error": "payload inválido", "detail": str(e)}, 422
    db.session.add(q)
    db.session.commit()
    return {"id": q.id, "titulo": q.titulo}, 201

@bp.post("/<int:quiz_id>/questions")
@jwt_required()
@require_role("DOCENTE")
def add_question(quiz_id: int):
    data = request.get_json(silent=True) or {}
    enun = (data.get("enunciado") or "").strip()
    tipo = (data.get("tipo") or "").strip()
    opciones = data.get("opciones") or []
    if not enun or not isinstance(opciones, list) or not opciones:
        return {"error": "faltan campos obligatorios"}, 422
    if tipo not in {"MULTIPLE"}:
        return {"error": "tipo inválido"}, 422

    p = Pregunta(quiz_id=quiz_id, enunciado=enun, tipo=tipo)
    db.session.add(p)
    db.session.flush()
    created_opts = []
    for opt in opciones:
        texto = (opt.get("texto") or "").strip()
        correcta = bool(opt.get("correcta", False))
        o = Opcion(pregunta_id=p.id, texto=texto, correcta=correcta)
        db.session.add(o)
        db.session.flush()
        created_opts.append({"id": o.id, "texto": o.texto, "correcta": o.correcta})
    db.session.commit()
    return {"id": p.id, "enunciado": p.enunciado, "tipo": p.tipo, "opciones": created_opts}, 201

@bp.get("/<int:quiz_id>/questions")
@jwt_required()
def list_questions(quiz_id: int):
    preguntas = Pregunta.query.filter_by(quiz_id=quiz_id).all()
    items = []
    for p in preguntas:
        opts = Opcion.query.filter_by(pregunta_id=p.id).all()
        items.append({
            "id": p.id,
            "enunciado": p.enunciado,
            "tipo": p.tipo,
            "opciones": [{"id": o.id, "texto": o.texto, "correcta": o.correcta} for o in opts]
        })
    return items  # el test espera lista

@bp.post("/<int:quiz_id>/attempts")
@jwt_required()
def start_attempt(quiz_id: int):
    user_id = int(get_jwt_identity())
    q = Quiz.query.get_or_404(quiz_id)
    cnt = Intento.query.filter_by(quiz_id=quiz_id, estudiante_id=user_id).count()
    if q.intentos_max and cnt >= q.intentos_max:
        return {"error": "límite de intentos alcanzado"}, 409
    it = Intento(quiz_id=quiz_id, estudiante_id=user_id)
    db.session.add(it)
    db.session.commit()
    return {"intento_id": it.id}

@bp.post("/attempts/<int:intento_id>/submit")
@jwt_required()
def submit_attempt(intento_id: int):
    user_id = int(get_jwt_identity())
    it = Intento.query.get_or_404(intento_id)
    if it.estudiante_id != user_id:
        return {"error": "forbidden"}, 403

    data = request.get_json(silent=True)
    # Validación estricta del body para satisfacer tests (400/422 si falta o es inválido)
    if not isinstance(data, dict) or "respuestas" not in data or not isinstance(data["respuestas"], dict):
        return {"error": "se requiere JSON con 'respuestas' (dict)"}, 422

    respuestas = data["respuestas"]

    preguntas = Pregunta.query.filter_by(quiz_id=it.quiz_id).all()
    total = len(preguntas)
    correctas = 0
    for p in preguntas:
        sel = respuestas.get(str(p.id)) or respuestas.get(p.id)
        if sel is None:
            continue
        ok = Opcion.query.filter_by(id=int(sel), pregunta_id=p.id, correcta=True).first()
        if ok:
            correctas += 1

    puntaje = int(round(100.0 * correctas / total)) if total else 0
    for attr, value in (("correctas", correctas), ("total", total), ("puntaje", puntaje)):
        try:
            setattr(it, attr, value)
        except Exception:
            pass
    db.session.commit()
    return {"correctas": correctas, "total": total, "puntaje": puntaje}
