import time
import json
import random
import uuid
from locust import HttpUser, task, between, events
from socketio import Client as SocketIOClient 
from threading import Thread

# --- Credentials from seed_db.py ---
TEST_USER_EMAIL = "test_user@example.com"
TEST_USER_PASSWORD = "password123"

# --- Authentication Helper ---
def login_and_get_session(client):
    """
    Performs a login and stores the session cookies on the client.
    """
    login_data = {"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    # Use the correct login endpoint for Docker Compose/Nginx
    response = client.post("/login", json=login_data, name="/login")
    if response.status_code != 200:
        raise Exception(f"Login failed for test user. Status: {response.status_code}, Body: {response.text}")
    return response

# --- Socket.IO Client Implementation ---
class BaseSocketIOUser(HttpUser):
    """Base class for Socket.IO functionality."""
    abstract = True  # Base class is abstract

class SocketIOUser(BaseSocketIOUser):
    """
    A custom user class for simulating real-time interactions via Socket.IO.
    This simulates joining the battle queue.
    """
    wait_time = between(5, 15)  # Wait 5 to 15 seconds between battle attempts
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket_client = SocketIOClient()
        self.battle_pending = False
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"  # Generate unique ID using UUID
        self.session_established = False

        # --- Event Listeners ---
        @self.socket_client.event
        def connect():
            print(f"[{self.user_id}] Socket Connected.")

        @self.socket_client.event
        def battle_result(data):
            self.battle_pending = False
            # Report successful Socket.IO transaction to Locust
            events.request.fire(
                request_type="SOCKET.IO",
                name="/socket.io/battle_result",
                response_time=int((time.time() - self.start_time) * 1000),
                response_length=len(json.dumps(data)),
                exception=None,
                context=None,
            )
            self.socket_client.disconnect()

        @self.socket_client.event
        def queue_error(data):
            # Report error
            events.request.fire(
                request_type="SOCKET.IO",
                name="/socket.io/queue_error",
                response_time=int((time.time() - self.start_time) * 1000),
                response_length=len(json.dumps(data)),
                exception=Exception(data.get('message', 'Unknown Queue Error')),
                context=None,
            )
            self.battle_pending = False
            self.socket_client.disconnect()


    def on_start(self):
        """Called when a new Locust user is started."""
        # Log in via HTTP first to establish a session cookie required for SocketIO authentication
        login_response = login_and_get_session(self.client)
        
        # Extract the session cookie set by Flask-Session (e.g., 'session')
        # We need to send this cookie with the SocketIO connection request
        self.session_cookies = login_response.cookies.get_dict()
        if not self.session_cookies:
            raise Exception("Failed to get session cookie after login.")
        self.session_established = True


    @task(3)
    def join_battle_queue(self):
        """Simulates joining the battle queue via WebSocket."""
        if not self.session_established or self.battle_pending:
            return

        # Connect to the Nginx entry point (port 5000)
        socketio_url = "http://nginx" # Use the internal service name
        
        try:
            self.socket_client.connect(
                socketio_url, 
                socketio_path='/socket.io/', 
                transports=['websocket'],
                # Pass the session cookie in the HTTP handshake headers
                # Flask-SocketIO will pick up the session from this cookie
                headers={'Cookie': '; '.join([f'{k}={v}' for k, v in self.session_cookies.items()])}
            )
        except Exception as e:
            events.request.fire(
                request_type="CONNECT",
                name="/socket.io/connect",
                response_time=0,
                response_length=0,
                exception=e,
                context=None,
            )
            return

        self.start_time = time.time()
        self.battle_pending = True
        
        # Emit the event to the server
        self.socket_client.emit('join_queue')
        
        # Wait up to 30 seconds for the battle_result
        for _ in range(30):
            if not self.battle_pending:
                break
            time.sleep(1)
        
        if self.battle_pending:
            # Report timeout
            events.request.fire(
                request_type="SOCKET.IO",
                name="/socket.io/join_queue_timeout",
                response_time=int((time.time() - self.start_time) * 1000),
                response_length=0,
                exception=Exception("Battle event timed out"),
                context=None,
            )
            self.socket_client.disconnect()
            self.battle_pending = False


# --- HTTP Client Implementation ---
class HttpLoadUser(HttpUser):
    """
    A standard HTTP user simulating core API requests (login, gatcha, etc.).
    """
    wait_time = between(2, 5) # Wait 2 to 5 seconds between HTTP requests
    host = "http://nginx" # Use the internal service name


    def on_start(self):
        """Log in when the user starts."""
        login_and_get_session(self.client)
        # Verify the inventory is populated (for realistic load)
        self.client.get("/api/inventory/", name="/api/inventory_check")

    @task(5)
    def api_gatcha(self):
        """Simulates the high-load DB write request for gatcha."""
        self.client.post("/api/gatcha/", name="/api/gatcha")

    @task(1)
    def api_inventory(self):
        """Simulates a lighter DB read request."""
        self.client.get("/api/inventory/", name="/api/inventory")

# --- Combine Both User Types ---
# This is the main class Locust runs, distributing tasks among Http and SocketIO
class MixedLoadUser(HttpLoadUser, BaseSocketIOUser):
    """User class that combines both HTTP and Socket.IO functionality."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket_client = SocketIOClient()
        self.battle_pending = False
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"  # Generate unique ID using UUID
        self.session_established = False

        # --- Event Listeners ---
        @self.socket_client.event
        def connect():
            print(f"[{self.user_id}] Socket Connected.")

        @self.socket_client.event
        def battle_result(data):
            self.battle_pending = False
            # Report successful Socket.IO transaction to Locust
            events.request.fire(
                request_type="SOCKET.IO",
                name="/socket.io/battle_result",
                response_time=int((time.time() - self.start_time) * 1000),
                response_length=len(json.dumps(data)),
                exception=None,
                context=None,
            )
            self.socket_client.disconnect()

        @self.socket_client.event
        def queue_error(data):
            # Report error
            events.request.fire(
                request_type="SOCKET.IO",
                name="/socket.io/queue_error",
                response_time=int((time.time() - self.start_time) * 1000),
                response_length=len(json.dumps(data)),
                exception=Exception(data.get('message', 'Unknown Queue Error')),
                context=None,
            )
            self.battle_pending = False
            self.socket_client.disconnect()
    
    @task(3)
    def join_battle_queue(self):
        """Simulates joining the battle queue via WebSocket."""
        if not self.session_established or self.battle_pending:
            return

        # Connect to the Nginx entry point (port 5000)
        socketio_url = "http://nginx" # Use the internal service name
        
        try:
            self.socket_client.connect(
                socketio_url, 
                socketio_path='/socket.io/', 
                transports=['websocket'],
                # Pass the session cookie in the HTTP handshake headers
                headers={'Cookie': '; '.join([f'{k}={v}' for k, v in self.session_cookies.items()])}
            )
        except Exception as e:
            events.request.fire(
                request_type="CONNECT",
                name="/socket.io/connect",
                response_time=0,
                response_length=0,
                exception=e,
                context=None,
            )
            return

        self.start_time = time.time()
        self.battle_pending = True
        
        # Emit the event to the server
        self.socket_client.emit('join_queue')
        
        # Wait up to 30 seconds for the battle_result
        for _ in range(30):
            if not self.battle_pending:
                break
            time.sleep(1)
        
        if self.battle_pending:
            # Report timeout
            events.request.fire(
                request_type="SOCKET.IO",
                name="/socket.io/join_queue_timeout",
                response_time=int((time.time() - self.start_time) * 1000),
                response_length=0,
                exception=Exception("Battle event timed out"),
                context=None,
            )
            self.socket_client.disconnect()
            self.battle_pending = False
