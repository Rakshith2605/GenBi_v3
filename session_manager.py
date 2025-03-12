# In-memory session storage.
# (For production use consider a persistent store like Redis or a database.)
sessions = {}

def get_session(user_id: str):
    """
    Retrieve (or create) a session for a given user.
    Session stores the dataset (df), query history, and answers.
    """
    if user_id not in sessions:
        sessions[user_id] = {"df": None, "queries": [], "answers": []}
    return sessions[user_id]

def update_session(user_id: str, key: str, value):
    """
    Update a specific key in the user's session.
    """
    session = get_session(user_id)
    session[key] = value
