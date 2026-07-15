from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Needed for session/login
DATABASE = 'attendance.db'

# --- Database Setup ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Create Students Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_number TEXT UNIQUE NOT NULL
            )
        ''')
        # Create Attendance Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        ''')
        db.commit()

# --- Routes ---

# 1. Login Page
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Simple Admin Login
        if username == 'admin' and password == '1234':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid Credentials. Please try again."
    return render_template('login.html', error=error)

# 2. Dashboard
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    db = get_db()
    student_count = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    return render_template('dashboard.html', student_count=student_count)

# 3. Manage Students
@app.route('/students', methods=['GET', 'POST'])
def students():
    if not session.get('logged_in'): return redirect(url_for('login'))
    db = get_db()
    
    if request.method == 'POST':
        name = request.form['name']
        roll = request.form['roll_number']
        try:
            db.execute("INSERT INTO students (name, roll_number) VALUES (?, ?)", (name, roll))
            db.commit()
        except sqlite3.IntegrityError:
            pass # Ignore if roll number already exists for simplicity

    all_students = db.execute("SELECT * FROM students").fetchall()
    return render_template('students.html', students=all_students)

# 4. Mark & View Attendance
@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if not session.get('logged_in'): return redirect(url_for('login'))
    db = get_db()
    today = date.today().strftime("%Y-%m-%d")

    if request.method == 'POST':
        student_id = request.form['student_id']
        status = request.form['status']
        record_date = request.form.get('date', today)
        
        # Check if already marked today
        existing = db.execute("SELECT * FROM attendance WHERE student_id=? AND date=?", (student_id, record_date)).fetchone()
        if existing:
            db.execute("UPDATE attendance SET status=? WHERE id=?", (status, existing['id']))
        else:
            db.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)", (student_id, record_date, status))
        db.commit()

    all_students = db.execute("SELECT * FROM students").fetchall()
    records = db.execute('''
        SELECT students.name, students.roll_number, attendance.date, attendance.status 
        FROM attendance 
        JOIN students ON attendance.student_id = students.id 
        ORDER BY attendance.date DESC
    ''').fetchall()
    
    return render_template('attendance.html', students=all_students, records=records, today=today)

# Logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db() # Create tables if they don't exist
    app.run(debug=True)