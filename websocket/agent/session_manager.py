from typing_extensions import Dict
import uuid
import threading
import datetime

class Conversation:
    id: str = ""
    context: dict = {}

    def __init__(self, id: str = ""):
        self.id = id
        self.context = {}
        self.create_time = datetime.datetime.now()

class Session:
    id: str = ""
    conversations: Dict[str, Conversation] = {}

    def __init__(self, session_id: str):
        self.id = session_id
        self.create_time = datetime.datetime.now()

    def newConversation(self) -> Conversation:
        conversation_id = str(uuid.uuid4())
        self.conversations[conversation_id] = Conversation(conversation_id)
        return self.conversations[conversation_id]

class SessionManager:
    sessions: Dict[str, Session] = {}

    def __init__(self):
        self.sessions = {}
        self.lock = threading.Lock()

    def new_session(self) -> Session:
        with self.lock:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = Session(session_id)
            return self.sessions[session_id]

    def get_session(self, session_id: str) -> Session:
        with self.lock:
            return self.sessions[session_id]

    def delete_session(self, session_id: str, physical: bool = True) -> None:
        with self.lock:
            if physical:
                del self.sessions[session_id]
            else:
                self.sessions[session_id].deleted = True

    async def run_clean_task(self):
        # TODO: add session timeout, use a timer to delete session
        pass

