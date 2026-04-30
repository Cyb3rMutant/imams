def portal_session(request):
    return {
        "session_mosque_id": request.session.get("mosque_id"),
        "session_imam_id": request.session.get("imam_id"),
    }
