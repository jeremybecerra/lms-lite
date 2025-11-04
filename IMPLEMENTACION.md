# Implementación
- Flask + Blueprints (auth, courses, quizzes, me), SQLite, JWT, CORS.
- Modelos: Usuario, Curso, Lección, Inscripción, Quiz, Pregunta, Opción, Intento.
- Decisiones: passlib[bcrypt], seed reproducible, validación simple y manejo de errores HTTP.
- CI: GitHub Actions con flake8 + pytest.
