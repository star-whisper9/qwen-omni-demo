import logging
import time
from typing import Dict, Any, List


class SessionManager:
    def __init__(self):
        # Active sessions and their configurations
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Message history for each session
        self.message_history: Dict[str, List[Dict[str, Any]]] = {}

        # Session expiration (2 hours)
        self.session_timeout = 7200  # seconds

    def create_or_update_session(self, client_id: str, config: Dict[str, Any]):
        """Create or update a session with the given configuration"""
        self.sessions[client_id] = {
            **config,
            'created_at': time.time(),
            'last_activity': time.time()
        }

        # Initialize message history if it doesn't exist
        if client_id not in self.message_history:
            self.message_history[client_id] = []

        logging.info(f"Session created/updated for client {client_id}: {config}")

    def session_exists(self, client_id: str) -> bool:
        """Check if a session exists"""
        return client_id in self.sessions

    def get_session(self, client_id: str) -> Dict[str, Any]:
        """Get session configuration"""
        if client_id in self.sessions:
            # Update last activity time
            self.sessions[client_id]['last_activity'] = time.time()
            return self.sessions[client_id]
        return {}

    def delete_session(self, client_id: str):
        """Delete a session"""
        if client_id in self.sessions:
            del self.sessions[client_id]
        if client_id in self.message_history:
            del self.message_history[client_id]
        logging.info(f"Session deleted for client {client_id}")

    def is_processing(self, client_id: str) -> bool:
        """Check if a session is currently processing audio"""
        if client_id in self.sessions:
            return self.sessions[client_id].get('isProcessing', False)
        return False

    def set_processing(self, client_id: str, processing: bool):
        """Set the processing state of a session"""
        if client_id in self.sessions:
            self.sessions[client_id]['isProcessing'] = processing
            self.sessions[client_id]['last_activity'] = time.time()

    def is_session_paused(self, client_id: str) -> bool:
        """Check if a session is paused"""
        if client_id in self.sessions:
            return self.sessions[client_id].get('isPaused', False)
        return False

    def set_pause_state(self, client_id: str, paused: bool):
        """Set the pause state of a session"""
        if client_id in self.sessions:
            self.sessions[client_id]['isPaused'] = paused
            self.sessions[client_id]['last_activity'] = time.time()

    def get_voice_type(self, client_id: str) -> str:
        """Get the voice type configured for a session"""
        from config import settings
        if client_id in self.sessions:
            voice_type = self.sessions[client_id].get('voiceType')
            if voice_type in settings.AVAILABLE_VOICES:
                return voice_type
        return settings.DEFAULT_VOICE

    def add_message_to_history(self, client_id: str, message: str, is_user: bool):
        """Add a message to the session history"""
        if client_id not in self.message_history:
            self.message_history[client_id] = []

        self.message_history[client_id].append({
            'text': message,
            'isUser': is_user,
            'timestamp': time.time()
        })

        # Update last activity
        if client_id in self.sessions:
            self.sessions[client_id]['last_activity'] = time.time()

    def get_message_history(self, client_id: str) -> List[Dict[str, Any]]:
        """Get message history for a session"""
        return self.message_history.get(client_id, [])

    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        expired_clients = []

        for client_id, session in self.sessions.items():
            if current_time - session.get('last_activity', 0) > self.session_timeout:
                expired_clients.append(client_id)

        for client_id in expired_clients:
            self.delete_session(client_id)

        if expired_clients:
            logging.info(f"Cleaned up {len(expired_clients)} expired sessions")


# Create singleton instance
session_manager = SessionManager()