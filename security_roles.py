"""Minimal identity enforcement for the controlled October pilot.

Two unique credentials: operator and Director. Not a replacement for production
user management / MFA. All release-significant decisions derive identity from
the verified credential, never from an HTML form field.
"""
import base64
import contextvars
import os
import secrets
from fastapi import HTTPException

_actor=contextvars.ContextVar("matrix360_authenticated_actor",default=None)

def activate_actor(actor):
    return _actor.set(actor)

def clear_actor(token):
    _actor.reset(token)

def current_actor():
    return _actor.get()

def director_required():
    if current_actor()!="Director":
        raise HTTPException(status_code=403, detail="Only the authenticated Director may approve")
    return "Director"

def configured():
    operator=os.getenv("MATRIX360_API_KEY","").strip()
    director=os.getenv("MATRIX360_DIRECTOR_KEY","").strip()
    valid=(len(operator)>=32 and len(director)>=32 and
           operator!=director and operator!="REPLACE_WITH_A_LONG_RANDOM_SECRET")
    return valid

def resolve_actor(headers):
    """Return Director/operator or None, using role-bound credentials.

    HTTP Basic user MUST be 'director' or 'operator'. Legacy shared-key header
    remains operator-only. Director header is accepted for non-browser clients.
    """
    operator=os.getenv("MATRIX360_API_KEY","").strip()
    director=os.getenv("MATRIX360_DIRECTOR_KEY","").strip()
    if not configured():return None
    username=password=""
    authorization=headers.get("Authorization","")
    if authorization.startswith("Basic "):
        try:
            raw=base64.b64decode(authorization[6:],validate=True).decode("utf-8")
            username,password=raw.split(":",1)
        except (UnicodeError,ValueError):
            pass
    if username=="director" and secrets.compare_digest(password,director):
        return "Director"
    if username=="operator" and secrets.compare_digest(password,operator):
        return "operator"
    director_header=headers.get("X-Matrix360-Director-Key","")
    if director_header and secrets.compare_digest(director_header,director):
        return "Director"
    operator_header=headers.get("X-Matrix360-Key","")
    if operator_header and secrets.compare_digest(operator_header,operator):
        return "operator"
    return None
