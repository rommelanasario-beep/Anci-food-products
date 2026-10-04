ANCI FOOD PRODUCTS - STOCK MANAGEMENT SYSTEM

Features: login/logout, dashboard, product catalog, stock in/out, sales recording,
automatic stock deduction, low-stock alerts, sales and movement history, SQLite database.

RUN:
1. Install Python 3.10+.
2. Open terminal in this folder.
3. Run: python -m pip install -r requirements.txt
4. Run: python app.py
5. Open http://127.0.0.1:5000

Demo login:
Username: admin
Password: admin123

The database stock.db is created automatically. Change the demo password and
SECRET_KEY before using this system for real business data. For public deployment,
use a production WSGI server, HTTPS, backups, and stronger user management.
