import os
import sqlite3
import base64
import secrets
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, send_from_directory, flash
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from crypto.signature import (
    sha256_bytes, generate_keypair, sign_hash, verify_hash,
    b64, unb64, ALGORITHM, HASH_ALGORITHM
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SIGNATURE_DIR = os.path.join(BASE_DIR, "signatures")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SIGNATURE_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SAFE_SIGN_SECRET", "change-this-for-production")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        student_id TEXT
    );

    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id TEXT UNIQUE NOT NULL,
        student_name TEXT NOT NULL,
        student_id TEXT NOT NULL,
        parent_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        stored_filename TEXT NOT NULL,
        original_hash TEXT NOT NULL,
        signature TEXT NOT NULL,
        public_key TEXT NOT NULL,
        algorithm TEXT NOT NULL,
        hash_algorithm TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        created_at TEXT NOT NULL,
        verified_at TEXT,
        verification_message TEXT,
        FOREIGN KEY(parent_id) REFERENCES users(id)
    );
    """)

    parent = conn.execute(
        "SELECT id FROM users WHERE username = ?", ("parent01",)
    ).fetchone()
    if not parent:
        conn.execute(
            "INSERT INTO users(name, username, password_hash, role, student_id) VALUES (?, ?, ?, ?, ?)",
            ("Demo Parent", "parent01", generate_password_hash("parent123"),
             "PARENT", "MMCOE-B-001")
        )

    college = conn.execute(
        "SELECT id FROM users WHERE username = ?", ("college01",)
    ).fetchone()
    if not college:
        conn.execute(
            "INSERT INTO users(name, username, password_hash, role, student_id) VALUES (?, ?, ?, ?, ?)",
            ("College Authority", "college01", generate_password_hash("college123"),
             "COLLEGE", None)
        )

    conn.commit()
    conn.close()


def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("index"))
            if role and session.get("role") != role:
                return redirect(url_for("index"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/parent/login", methods=["GET", "POST"])
def parent_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND role = 'PARENT'",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = "PARENT"
            session["name"] = user["name"]
            session["student_id"] = user["student_id"]
            return redirect(url_for("parent_dashboard"))

        flash("Invalid parent username or password.", "error")

    return render_template("parent_login.html")


@app.route("/college/login", methods=["GET", "POST"])
def college_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND role = 'COLLEGE'",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = "COLLEGE"
            session["name"] = user["name"]
            return redirect(url_for("college_dashboard"))

        flash("Invalid college username or password.", "error")

    return render_template("college_login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/parent/dashboard")
@login_required("PARENT")
def parent_dashboard():
    conn = db()
    docs = conn.execute(
        "SELECT * FROM documents WHERE parent_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("parent_dashboard.html", docs=docs)


@app.route("/parent/upload", methods=["GET", "POST"])
@login_required("PARENT")
def upload_document():
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        student_id = request.form.get("student_id", "").strip()
        file = request.files.get("document")

        if not student_name or not student_id or not file or not file.filename:
            flash("Please enter student details and select a document.", "error")
            return redirect(url_for("upload_document"))

        if student_id != session.get("student_id"):
            flash("Student ID does not match the registered parent association.", "error")
            return redirect(url_for("upload_document"))

        safe_name = secure_filename(file.filename)
        if not safe_name:
            flash("Invalid filename.", "error")
            return redirect(url_for("upload_document"))

        raw = file.read()
        document_hash = sha256_bytes(raw)

        public_key, secret_key = generate_keypair()
        signature = sign_hash(secret_key, document_hash)

        # The secret key is kept server-side for this prototype only.
        # In a real deployment it should be stored in a protected key store.
        key_file = os.path.join(SIGNATURE_DIR, secrets.token_hex(16) + ".key")
        with open(key_file, "wb") as f:
            f.write(secret_key)

        document_id = "DOC-" + datetime.now().strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()
        stored_filename = document_id + "_" + safe_name
        file_path = os.path.join(UPLOAD_DIR, stored_filename)

        with open(file_path, "wb") as f:
            f.write(raw)

        conn = db()
        conn.execute(
            """INSERT INTO documents
            (document_id, student_name, student_id, parent_id, filename, stored_filename,
             original_hash, signature, public_key, algorithm, hash_algorithm, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)""",
            (
                document_id, student_name, student_id, session["user_id"],
                safe_name, stored_filename, document_hash,
                b64(signature), b64(public_key), ALGORITHM, HASH_ALGORITHM,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        conn.commit()
        conn.close()

        return redirect(url_for("parent_success", document_id=document_id))

    return render_template(
        "upload.html",
        parent_name=session.get("name"),
        student_id=session.get("student_id")
    )


@app.route("/parent/success/<document_id>")
@login_required("PARENT")
def parent_success(document_id):
    conn = db()
    doc = conn.execute(
        "SELECT * FROM documents WHERE document_id = ? AND parent_id = ?",
        (document_id, session["user_id"])
    ).fetchone()
    conn.close()

    if not doc:
        return redirect(url_for("parent_dashboard"))

    return render_template("success.html", doc=doc)


def verify_document_record(doc):
    file_path = os.path.join(UPLOAD_DIR, doc["stored_filename"])
    if not os.path.exists(file_path):
        return False, "Document file is missing."

    with open(file_path, "rb") as f:
        current_bytes = f.read()

    current_hash = sha256_bytes(current_bytes)
    hash_ok = current_hash == doc["original_hash"]

    try:
        signature_ok = verify_hash(
            unb64(doc["public_key"]),
            current_hash,
            unb64(doc["signature"])
        )
    except Exception:
        signature_ok = False

    parent_ok = doc["student_id"] == (
        db().execute("SELECT student_id FROM users WHERE id = ?", (doc["parent_id"],)).fetchone()["student_id"]
    )

    if hash_ok and signature_ok and parent_ok:
        return True, "Hash, signature, document integrity and parent-student association verified."

    reasons = []
    if not hash_ok:
        reasons.append("SHA-256 hash mismatch")
    if not signature_ok:
        reasons.append("ML-DSA-65 signature invalid")
    if not parent_ok:
        reasons.append("Parent-student association failed")
    return False, "; ".join(reasons)


@app.route("/college/dashboard")
@login_required("COLLEGE")
def college_dashboard():
    return render_template("college_dashboard.html")


@app.route("/api/college/documents")
@login_required("COLLEGE")
def api_college_documents():
    conn = db()
    rows = conn.execute(
        """SELECT d.*, u.name AS parent_name
           FROM documents d
           JOIN users u ON u.id = d.parent_id
           ORDER BY d.id DESC"""
    ).fetchall()
    conn.close()

    docs = []
    for row in rows:
        docs.append(dict(row))
    return jsonify({"documents": docs})

@app.route("/api/parent/document/<document_id>")
@login_required("PARENT")
def parent_document_status(document_id):
    conn = db()

    doc = conn.execute(
        """SELECT * FROM documents
           WHERE document_id = ? AND parent_id = ?""",
        (document_id, session["user_id"])
    ).fetchone()

    conn.close()

    if not doc:
        return jsonify({"ok": False, "message": "Document not found."}), 404

    return jsonify({
        "ok": True,
        "document_id": doc["document_id"],
        "status": doc["status"],
        "verified_at": doc["verified_at"],
        "message": doc["verification_message"]
    })



@app.route("/api/college/verify/<document_id>", methods=["POST"])
@login_required("COLLEGE")
def api_verify(document_id):
    conn = db()
    doc = conn.execute(
        "SELECT * FROM documents WHERE document_id = ?", (document_id,)
    ).fetchone()

    if not doc:
        conn.close()
        return jsonify({"ok": False, "message": "Document not found."}), 404

    ok, message = verify_document_record(doc)

    status = "VERIFIED" if ok else "FAILED"
    verified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if ok else None

    conn.execute(
        "UPDATE documents SET status = ?, verified_at = ?, verification_message = ? WHERE document_id = ?",
        (status, verified_at, message, document_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": ok, "status": status, "message": message})


@app.route("/api/college/recheck/<document_id>", methods=["POST"])
@login_required("COLLEGE")
def api_recheck(document_id):
    # Re-run verification so tampering is detectable after the file changes.
    return api_verify(document_id)


@app.route("/documents/<document_id>/file")
@login_required()
def document_file(document_id):
    conn = db()
    doc = conn.execute(
        "SELECT * FROM documents WHERE document_id = ?", (document_id,)
    ).fetchone()
    conn.close()
    if not doc:
        return "Document not found", 404
    return send_from_directory(UPLOAD_DIR, doc["stored_filename"], as_attachment=False)


@app.route("/api/health")
def health():
    return jsonify({"status": "running", "algorithm": ALGORITHM, "hash": HASH_ALGORITHM})


if __name__ == "__main__":
    init_db()
    print("\nSafeSign running on all network interfaces.")
    print("Parent:  http://127.0.0.1:5000")
    print("College:  http://<SERVER-IP>:5000/college/login")
    app.run(host="0.0.0.0", port=5000, debug=True)
