from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def require_role(*roles):
    """
    Uso:
      @jwt_required()
      @require_role("DOCENTE")
      def create_course(): ...
    """
    def wrapper(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt() or {}
            rol = claims.get("rol")
            if rol not in roles:
                return {"error": "forbidden", "needed": list(roles), "got": rol}, 403
            return fn(*args, **kwargs)
        return inner
    return wrapper
