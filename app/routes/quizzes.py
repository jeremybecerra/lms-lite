from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from .. import db
from ..models import Quiz, Pregunta, Opcion, IntentoQuiz

bp = Blueprint("quizzes", __name__)

@bp.get("/<int:quiz_id>")
def get_quiz(quiz_id):
    q = Quiz.query.get_or_404(quiz_id)
    total_p = Pregunta.query.filter_by(quiz_id=q.id).count()
    return {"id": q.id, "curso_id": q.curso_id, "titulo": q.titulo,
            "tiempo_limite_min": q.tiempo_limite_min, "intentos_max": q.intentos_max,
            "preguntas": total_p}

@bp.get("/<int:quiz_id>/questions")
@jwt_required()
def list_questions(quiz_id):
    preguntas = Pregunta.query.filter_by(quiz_id=quiz_id).all()
    payload = []
    for p in preguntas:
        opciones = Opcion.query.filter_by(pregunta_id=p.id).all()
        payload.append({
            "id": p.id,
            "enunciado": p.enunciado,
            "opciones": [{"id": o.id, "texto": o.texto, "correcta": o.correcta} for o in opciones]
        })
    return payload

@bp.post("/")
@jwt_required()
def create_quiz():
    data = request.get_json() or {}
    q = Quiz(curso_id=data["curso_id"], titulo=data["titulo"],
             tiempo_limite_min=data.get("tiempo_limite_min", 20),
             intentos_max=data.get("intentos_max", 2))
    db.session.add(q); db.session.commit()
    return {"id": q.id, "titulo": q.titulo}, 201

@bp.post("/<int:quiz_id>/questions")
@jwt_required()
def add_question(quiz_id):
    data = request.get_json() or {}
    p = Pregunta(quiz_id=quiz_id, enunciado=data["enunciado"], tipo=data.get("tipo", "MULTIPLE"))
    db.session.add(p); db.session.flush()
    opts = []
    for opt in data.get("opciones", []):
        obj = Opcion(pregunta_id=p.id, texto=opt["texto"], correcta=opt.get("correcta", False))
        db.session.add(obj); db.session.flush()
        opts.append({"id": obj.id, "texto": obj.texto, "correcta": obj.correcta})
    db.session.commit()
    return {"id": p.id, "enunciado": p.enunciado, "opciones": opts}, 201

@bp.post("/<int:quiz_id>/attempts")
@jwt_required()
def start_attempt(quiz_id):
    user_id = int(get_jwt_identity())
    it = IntentoQuiz(quiz_id=quiz_id, estudiante_id=user_id)
    db.session.add(it); db.session.commit()
    return {"intento_id": it.id}

@bp.post("/attempts/<int:intento_id>/submit")
@jwt_required()
def submit_attempt(intento_id):
    data = request.get_json() or {}
    respuestas = data.get("respuestas", {})
    total = 0; correctas = 0
    for pid, oid in respuestas.items():
        total += 1
        op = Opcion.query.get(oid)
        if op and op.correcta:
            correctas += 1
    puntaje = round((correctas/total)*100, 2) if total else 0.0
    intento = IntentoQuiz.query.get_or_404(intento_id)
    intento.puntaje = puntaje; intento.entregado = True
    db.session.commit()
    return {"puntaje": puntaje, "correctas": correctas, "total": total}
# --- Entrega detallada: control de tiempo y feedback por pregunta ---

from datetime import datetime, timedelta
from flask import request
from flask_jwt_extended import jwt_required

def _now_utc():
    return datetime.utcnow()

def _json_ok(data=None, status=200):
    return (data or {"ok": True}, status)

def _json_err(msg, status=400):
    return ({"error": msg}, status)

@bp.post("/attempts/<int:intento_id>/submit-detailed")
@jwt_required()
def submit_detailed(intento_id: int):
    """Entrega con feedback de cada pregunta y control de tiempo."""
    from app.models import IntentoQuiz, Quiz, Opcion, Pregunta, db
    body = request.get_json(silent=True) or {}
    respuestas = body.get("respuestas") or {}
    intento = IntentoQuiz.query.get_or_404(intento_id)
    quiz = Quiz.query.get_or_404(intento.quiz_id)

    if quiz.tiempo_limite_min:
        limite = intento.fecha + timedelta(minutes=quiz.tiempo_limite_min)
        if _now_utc() > limite:
            return _json_err("tiempo agotado", 409)

    correctas = 0
    total = 0
    detalle = []

    for pid_str, oid in respuestas.items():
        try:
            pid = int(pid_str)
        except Exception:
            return _json_err(f"pregunta id inválida: {pid_str}")
        total += 1
        preg = Pregunta.query.get(pid)
        if not preg or preg.quiz_id != quiz.id:
            return _json_err(f"pregunta no pertenece al quiz: {pid}")

        opc = Opcion.query.get(oid)
        if not opc or opc.pregunta_id != preg.id:
            detalle.append({"pregunta_id": pid, "ok": False, "motivo": "opción inválida"})
            continue

        is_ok = bool(opc.correcta)
        if is_ok:
            correctas += 1
        detalle.append({"pregunta_id": pid, "ok": is_ok, "respuesta_id": oid})

    puntaje = round((correctas / total) * 100, 2) if total else 0.0
    intento.puntaje = puntaje
    db.session.add(intento); db.session.commit()

    return _json_ok({"correctas": correctas, "total": total, "puntaje": puntaje, "detalle": detalle})
# --- Extensiones de quizzes: estadísticas, edición de preguntas y opciones, ver intento ---

from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

@bp.get("/<int:quiz_id>/stats")
@jwt_required()
def quiz_stats(quiz_id: int):
    """Estadísticas básicas del quiz: intentos, promedio, máximo."""
    from app.models import Quiz, IntentoQuiz, db
    q = Quiz.query.get(quiz_id)
    if not q:
        return _json_err("quiz no encontrado", 404)

    cnt = db.session.query(func.count(IntentoQuiz.id)).filter(IntentoQuiz.quiz_id == quiz_id).scalar() or 0
    avg = db.session.query(func.avg(IntentoQuiz.puntaje)).filter(IntentoQuiz.quiz_id == quiz_id).scalar()
    best = db.session.query(func.max(IntentoQuiz.puntaje)).filter(IntentoQuiz.quiz_id == quiz_id).scalar()
    return _json_ok({"intentos": int(cnt), "promedio": float(avg or 0.0), "mejor": float(best or 0.0)})

@bp.patch("/questions/<int:pregunta_id>")
@jwt_required()
def update_question(pregunta_id: int):
    """Editar texto/tipo de una pregunta."""
    from app.models import Pregunta, TipoPregunta, db
    body = request.get_json(silent=True) or {}
    p = Pregunta.query.get(pregunta_id)
    if not p:
        return _json_err("pregunta no encontrada", 404)

    enun = (body.get("enunciado") or "").strip()
    tipo = (body.get("tipo") or "").strip().upper()
    if enun:
        p.enunciado = enun
    if tipo:
        try:
            p.tipo = TipoPregunta(tipo)
        except Exception:
            return _json_err("tipo inválido (MULTIPLE|VF)")

    db.session.add(p); db.session.commit()
    return _json_ok({"id": p.id, "enunciado": p.enunciado, "tipo": p.tipo.value})

@bp.post("/questions/<int:pregunta_id>/options")
@jwt_required()
def add_option(pregunta_id: int):
    """Agregar opción a una pregunta (MULTIPLE)."""
    from app.models import Pregunta, Opcion, db
    body = request.get_json(silent=True) or {}
    p = Pregunta.query.get(pregunta_id)
    if not p:
        return _json_err("pregunta no encontrada", 404)
    t = (body.get("texto") or "").strip()
    if not t:
        return _json_err("texto requerido")
    correcta = bool(body.get("correcta", False))
    op = Opcion(pregunta_id=p.id, texto=t, correcta=correcta)
    db.session.add(op); db.session.commit()
    return _json_ok({"id": op.id, "texto": op.texto, "correcta": op.correcta}, 201)

@bp.delete("/questions/<int:pregunta_id>/options/<int:opcion_id>")
@jwt_required()
def delete_option(pregunta_id: int, opcion_id: int):
    """Eliminar opción de una pregunta."""
    from app.models import Opcion, Pregunta, db
    p = Pregunta.query.get(pregunta_id)
    if not p:
        return _json_err("pregunta no encontrada", 404)
    op = Opcion.query.get(opcion_id)
    if not op or op.pregunta_id != p.id:
        return _json_err("opción no encontrada", 404)
    db.session.delete(op); db.session.commit()
    return _json_ok({"ok": True})

@bp.get("/attempts/<int:intento_id>")
@jwt_required()
def get_attempt(intento_id: int):
    """Ver detalle del intento (puntaje y timestamp)."""
    from app.models import IntentoQuiz
    it = IntentoQuiz.query.get(intento_id)
    if not it:
        return _json_err("intento no encontrado", 404)
    return _json_ok({"id": it.id, "quiz_id": it.quiz_id, "fecha": it.fecha.isoformat(), "puntaje": it.puntaje or 0.0})
