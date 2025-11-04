from datetime import datetime
from enum import Enum
from . import db

class Rol(str, Enum):
    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"
    ADMIN = "ADMIN"

class EstadoCurso(str, Enum):
    BORRADOR = "BORRADOR"
    PUBLICADO = "PUBLICADO"
    OCULTO = "OCULTO"

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.Enum(Rol), nullable=False, default=Rol.ESTUDIANTE)

class Curso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    estado = db.Column(db.Enum(EstadoCurso), default=EstadoCurso.BORRADOR, nullable=False)
    docente_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)

class Leccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("curso.id"), nullable=False)
    titulo = db.Column(db.String(120), nullable=False)
    contenido = db.Column(db.Text)
    video_url = db.Column(db.String(255))
    orden = db.Column(db.Integer, default=1)

class Inscripcion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey("curso.id"), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Progreso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey("curso.id"), nullable=False)
    ultima_leccion_id = db.Column(db.Integer, db.ForeignKey("leccion.id"))
    porcentaje = db.Column(db.Float, default=0.0)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("curso.id"), nullable=False)
    titulo = db.Column(db.String(120), nullable=False)
    tiempo_limite_min = db.Column(db.Integer, default=20)
    intentos_max = db.Column(db.Integer, default=2)

class Pregunta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    enunciado = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(10), default="MULTIPLE")  # MULTIPLE o VF

class Opcion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pregunta_id = db.Column(db.Integer, db.ForeignKey("pregunta.id"), nullable=False)
    texto = db.Column(db.String(255), nullable=False)
    correcta = db.Column(db.Boolean, default=False)

class IntentoQuiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    estudiante_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    puntaje = db.Column(db.Float)
    entregado = db.Column(db.Boolean, default=False)
