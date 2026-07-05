import os
import sqlite3
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from src.utils.crypto_helper import encrypt_string, decrypt_string

# Ensure environment variables are loaded
load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_URL", "data/legal_advisor.db")

def _get_connection():
    # Ensure parent directory exists
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _hash_value(value: str) -> str:
    """Generates a SHA-256 hash for deterministic lookups (like username lookup)"""
    if not value:
        return ""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()

def initialize_database():
    """Create schema tables if they do not exist"""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username_hash TEXT UNIQUE NOT NULL,
            enc_username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'User'
        )
    """)
    
    # 2. Documents Table (Metadata)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enc_filename TEXT NOT NULL,
            enc_file_path TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            upload_timestamp TEXT NOT NULL,
            document_type TEXT NOT NULL,
            FOREIGN KEY(uploaded_by) REFERENCES users(id)
        )
    """)
    
    # 3. Audit Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            enc_username TEXT NOT NULL,
            user_role TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            action TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            status TEXT NOT NULL,
            processing_time REAL NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize on import
initialize_database()

class DBManager:
    @staticmethod
    def register_user(username: str, password_hash: str, role: str = "User") -> bool:
        """
        Register a new user.
        """
        username_hash = _hash_value(username)
        enc_username = encrypt_string(username)
        
        conn = _get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username_hash, enc_username, password_hash, role) VALUES (?, ?, ?, ?)",
                (username_hash, enc_username, password_hash, role)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Username already exists
        finally:
            conn.close()

    @staticmethod
    def get_user_by_username(username: str) -> dict:
        """
        Retrieve user by username.
        """
        username_hash = _hash_value(username)
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, enc_username, password_hash, role FROM users WHERE username_hash = ?",
            (username_hash,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                decrypted_name = decrypt_string(row["enc_username"])
            except Exception:
                decrypted_name = username
            return {
                "id": row["id"],
                "username": decrypted_name,
                "password_hash": row["password_hash"],
                "role": row["role"]
            }
        return None

    @staticmethod
    def get_user_by_id(user_id: int) -> dict:
        """
        Retrieve user by ID.
        """
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, enc_username, role FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                decrypted_name = decrypt_string(row["enc_username"])
            except Exception:
                decrypted_name = "Unknown"
            return {
                "id": row["id"],
                "username": decrypted_name,
                "role": row["role"]
            }
        return None

    @staticmethod
    def get_all_users() -> list:
        """
        Retrieve all users (decrypted). Restricted to Admins.
        """
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, enc_username, role FROM users")
        rows = cursor.fetchall()
        conn.close()
        
        users_list = []
        for r in rows:
            try:
                decrypted_name = decrypt_string(r["enc_username"])
            except Exception:
                decrypted_name = "Decryption Error"
            users_list.append({
                "id": r["id"],
                "username": decrypted_name,
                "role": r["role"]
            })
        return users_list

    @staticmethod
    def update_user_role(user_id: int, new_role: str) -> bool:
        """
        Update user role. Restricted to Admins.
        """
        if new_role not in ["User", "Admin"]:
            return False
            
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (new_role, user_id)
        )
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    @staticmethod
    def delete_user(user_id: int) -> bool:
        """
        Delete a user. Restricted to Admins.
        """
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    @staticmethod
    def add_document(filename: str, file_path: str, uploaded_by: int, document_type: str) -> int:
        """
        Store encrypted document metadata.
        """
        enc_filename = encrypt_string(filename)
        enc_file_path = encrypt_string(file_path)
        timestamp = datetime.utcnow().isoformat()
        
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (enc_filename, enc_file_path, uploaded_by, upload_timestamp, document_type) VALUES (?, ?, ?, ?, ?)",
            (enc_filename, enc_file_path, uploaded_by, timestamp, document_type)
        )
        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return doc_id

    @staticmethod
    def get_documents_by_user(user_id: int) -> list:
        """
        Get all documents uploaded by a specific user.
        """
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, enc_filename, enc_file_path, upload_timestamp, document_type FROM documents WHERE uploaded_by = ?",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        docs = []
        for r in rows:
            try:
                filename = decrypt_string(r["enc_filename"])
                file_path = decrypt_string(r["enc_file_path"])
            except Exception:
                filename = "Decryption Error"
                file_path = "Decryption Error"
            docs.append({
                "id": r["id"],
                "filename": filename,
                "file_path": file_path,
                "upload_timestamp": r["upload_timestamp"],
                "document_type": r["document_type"]
            })
        return docs

    @staticmethod
    def get_all_documents() -> list:
        """
        Get all uploaded documents (restricted to Admin).
        """
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT d.id, d.enc_filename, d.enc_file_path, d.upload_timestamp, d.document_type, u.enc_username "
            "FROM documents d JOIN users u ON d.uploaded_by = u.id"
        )
        rows = cursor.fetchall()
        conn.close()
        
        docs = []
        for r in rows:
            try:
                filename = decrypt_string(r["enc_filename"])
                file_path = decrypt_string(r["enc_file_path"])
                username = decrypt_string(r["enc_username"])
            except Exception:
                filename = "Decryption Error"
                file_path = "Decryption Error"
                username = "Decryption Error"
            docs.append({
                "id": r["id"],
                "filename": filename,
                "file_path": file_path,
                "upload_timestamp": r["upload_timestamp"],
                "document_type": r["document_type"],
                "uploaded_by": username
            })
        return docs

    @staticmethod
    def log_audit_event(username: str, role: str, ip_address: str, action: str, endpoint: str, status: str, processing_time: float):
        """
        Log an audit event with encrypted username.
        """
        enc_username = encrypt_string(username)
        timestamp = datetime.utcnow().isoformat()
        
        conn = _get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO audit_logs (timestamp, enc_username, user_role, ip_address, action, endpoint, status, processing_time) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (timestamp, enc_username, role, ip_address, action, endpoint, status, processing_time)
            )
            conn.commit()
        except Exception as e:
            print(f"[DB_ERROR] Failed to log audit event: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_audit_logs() -> list:
        """
        Retrieve all audit logs (restricted to Admin).
        """
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, enc_username, user_role, ip_address, action, endpoint, status, processing_time FROM audit_logs ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for r in rows:
            try:
                username = decrypt_string(r["enc_username"])
            except Exception:
                username = "Decryption Error"
            logs.append({
                "id": r["id"],
                "timestamp": r["timestamp"],
                "username": username,
                "user_role": r["user_role"],
                "ip_address": r["ip_address"],
                "action": r["action"],
                "endpoint": r["endpoint"],
                "status": r["status"],
                "processing_time": r["processing_time"]
            })
        return logs
