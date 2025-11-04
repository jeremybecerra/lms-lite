# LMS Lite (Flask API + Frontend estático)

Proyecto mínimo de LMS con API en Flask y frontend estático simple para pruebas locales.

## Tecnologías
- Python 3.10+
- Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-Cors, passlib, python-dotenv
- SQLite
- Frontend: HTML + fetch (sin frameworks)

## Estructura
lms-lite/
app/
__init__.py
models.py
routes/
auth.py
courses.py
quizzes.py
me.py
utils/
security.py
authz.py
scripts/
seed_http.ps1
reset.ps1
web/
index.html
run.py
.env
.env.example
requirements.txt
README.md
lms.db (se crea al correr)

## Requisitos
- Windows + PowerShell
- Python 3.10 o superior

## Configuración inicial
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Si no tienes requirements.txt: pip freeze > requirements.txt
# Variables de entorno:
Copy-Item .env.example .env
