# SafeSign — Parent Digital Signature Verification System

College prototype implementing:
- Parent Portal
- College Authority Portal
- SHA-256 document hashing
- ML-DSA-65 digital signatures
- SQLite shared backend database
- JavaScript polling for near-real-time college dashboard updates
- Tamper detection

## Architecture

Frontend:
- HTML: `templates/`
- CSS: `static/css/style.css`
- JavaScript: `static/js/`

Backend:
- Flask: `app.py`
- Cryptography: `crypto/signature.py`
- Database: SQLite (`database.db` is created automatically)

## Demo credentials

Parent:
- Username: `parent01`
- Password: `parent123`

College:
- Username: `college01`
- Password: `college123`

## Run on Laptop 1 (server/parent laptop)

1. Install Python 3.10+.
2. Open terminal in this folder.
3. Create a virtual environment:
   `python -m venv venv`
4. Activate:
   Windows: `venv\Scripts\activate`
5. Install:
   `pip install -r requirements.txt`
6. Start:
   `python app.py`

The server listens on `0.0.0.0:5000`.

Parent laptop:
`http://127.0.0.1:5000`

## Run on Laptop 2 (college)

Both laptops must be on the same Wi-Fi/LAN.

Find Laptop 1 IPv4 address:
`ipconfig`

Example:
`192.168.1.105`

On Laptop 2 open:
`http://192.168.1.105:5000/college/login`

If Windows Firewall asks, allow Python on the private network.

## Demo flow

Laptop 1:
Home -> Parent Portal -> Login -> Upload document -> Preview -> Sign -> Submit

Laptop 2:
College Portal -> Login -> Dashboard

The college dashboard polls the shared backend every 2 seconds.
After the parent submits a valid signed document, the dashboard shows:
`🟢 VERIFIED`

For a tamper test, modify the stored uploaded file or use the built-in verification endpoint after changing a file. The dashboard will show:
`🔴 VERIFICATION FAILED`

## Important

The ML-DSA private key is kept on the backend and is never placed in browser JavaScript.
This is a college/research prototype, not a production identity-management system.
