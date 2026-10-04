from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","change-this-secret-key")
DB=os.path.join(os.path.dirname(__file__),"stock.db")

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT NOT NULL, sku TEXT UNIQUE, category TEXT, price REAL DEFAULT 0, stock INTEGER DEFAULT 0, reorder_level INTEGER DEFAULT 5);
        CREATE TABLE IF NOT EXISTS movements(id INTEGER PRIMARY KEY, product_id INTEGER, kind TEXT, quantity INTEGER, note TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(product_id) REFERENCES products(id));
        CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY, product_id INTEGER, quantity INTEGER, total REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        """)
        if not c.execute("SELECT id FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password) VALUES(?,?)",("admin",generate_password_hash("admin123")))
        if c.execute("SELECT COUNT(*) n FROM products").fetchone()["n"]==0:
            c.executemany("INSERT INTO products(name,sku,category,price,stock,reorder_level) VALUES(?,?,?,?,?,?)",[
             ("Rising Sun Pancit Canton","RS-001","Noodles",85,40,10),("Golden Crab Pancit Canton","GC-001","Noodles",90,25,8),("Special Pancit Canton","SP-001","Noodles",80,18,5)])
init_db()
def login_required(f):
    @wraps(f)
    def w(*a,**kw):
        if not session.get("user"): return redirect(url_for("login"))
        return f(*a,**kw)
    return w
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        with db() as c: u=c.execute("SELECT * FROM users WHERE username=?",(request.form["username"],)).fetchone()
        if u and check_password_hash(u["password"],request.form["password"]):
            session["user"]=u["username"]; return redirect(url_for("dashboard"))
        flash("Invalid username or password")
    return render_template("login.html")
@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("login"))
@app.route("/")
@login_required
def dashboard():
    with db() as c:
        stats={"products":c.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "units":c.execute("SELECT COALESCE(SUM(stock),0) FROM products").fetchone()[0],
        "low":c.execute("SELECT COUNT(*) FROM products WHERE stock<=reorder_level").fetchone()[0],
        "sales":c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(created_at)=date('now','localtime')").fetchone()[0]}
        low=c.execute("SELECT * FROM products WHERE stock<=reorder_level ORDER BY stock").fetchall()
        recent=c.execute("SELECT s.*,p.name FROM sales s JOIN products p ON p.id=s.product_id ORDER BY s.id DESC LIMIT 6").fetchall()
    return render_template("dashboard.html",stats=stats,low=low,recent=recent)
@app.route("/products",methods=["GET","POST"])
@login_required
def products():
    if request.method=="POST":
        try:
            with db() as c: c.execute("INSERT INTO products(name,sku,category,price,stock,reorder_level) VALUES(?,?,?,?,?,?)",(request.form["name"],request.form["sku"],request.form["category"],float(request.form["price"]),int(request.form["stock"]),int(request.form["reorder_level"])))
            flash("Product added.")
        except sqlite3.IntegrityError: flash("SKU already exists.")
        return redirect(url_for("products"))
    q=request.args.get("q","")
    with db() as c: rows=c.execute("SELECT * FROM products WHERE name LIKE ? OR sku LIKE ? ORDER BY name",('%'+q+'%','%'+q+'%')).fetchall()
    return render_template("products.html",products=rows,q=q)
@app.route("/stock",methods=["GET","POST"])
@login_required
def stock():
    with db() as c:
        if request.method=="POST":
            pid=int(request.form["product_id"]); qty=int(request.form["quantity"]); kind=request.form["kind"]
            p=c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
            if not p or qty<1: flash("Enter a valid quantity.")
            elif kind=="OUT" and qty>p["stock"]: flash("Not enough stock.")
            else:
                new=p["stock"]+(qty if kind=="IN" else -qty)
                c.execute("UPDATE products SET stock=? WHERE id=?",(new,pid))
                c.execute("INSERT INTO movements(product_id,kind,quantity,note) VALUES(?,?,?,?)",(pid,kind,qty,request.form.get("note","")))
                flash("Stock updated.")
            return redirect(url_for("stock"))
        products=c.execute("SELECT * FROM products ORDER BY name").fetchall()
        movements=c.execute("SELECT m.*,p.name FROM movements m JOIN products p ON p.id=m.product_id ORDER BY m.id DESC LIMIT 30").fetchall()
    return render_template("stock.html",products=products,movements=movements)
@app.route("/sales",methods=["GET","POST"])
@login_required
def sales():
    with db() as c:
        if request.method=="POST":
            pid=int(request.form["product_id"]); qty=int(request.form["quantity"])
            p=c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
            if not p or qty<1 or qty>p["stock"]: flash("Invalid quantity or insufficient stock.")
            else:
                total=qty*p["price"]; c.execute("UPDATE products SET stock=stock-? WHERE id=?",(qty,pid))
                c.execute("INSERT INTO sales(product_id,quantity,total) VALUES(?,?,?)",(pid,qty,total))
                c.execute("INSERT INTO movements(product_id,kind,quantity,note) VALUES(?,?,?,?)",(pid,"OUT",qty,"Sale"))
                flash(f"Sale recorded: ₱{total:,.2f}")
            return redirect(url_for("sales"))
        products=c.execute("SELECT * FROM products WHERE stock>0 ORDER BY name").fetchall()
        rows=c.execute("SELECT s.*,p.name FROM sales s JOIN products p ON p.id=s.product_id ORDER BY s.id DESC LIMIT 100").fetchall()
    return render_template("sales.html",products=products,sales=rows)
@app.route("/delete/<int:pid>",methods=["POST"])
@login_required
def delete_product(pid):
    with db() as c:
        c.execute("DELETE FROM products WHERE id=?",(pid,))
    flash("Product deleted."); return redirect(url_for("products"))
if __name__=="__main__": app.run(host="0.0.0.0",port=5000,debug=True)
