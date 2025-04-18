from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database initialization
def init_db():
    conn = sqlite3.connect('employee.db')
    cursor = conn.cursor()
    
    # Create admin table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    
    # Insert default admin if not exists
    cursor.execute("SELECT * FROM admin WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ('admin', 'admin123'))
    
    # Create employees table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        position TEXT,
        hire_date TEXT,
        salary REAL
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('employee.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password))
        admin = cursor.fetchone()
        conn.close()
        
        if admin:
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# API Routes for Employee Management
@app.route('/api/employees', methods=['GET'])
@login_required
def get_employees():
    conn = sqlite3.connect('employee.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees")
    employees = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(employees)

@app.route('/api/employees', methods=['POST'])
@login_required
def add_employee():
    employee_data = request.json
    
    conn = sqlite3.connect('employee.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO employees (name, email, phone, position, hire_date, salary) VALUES (?, ?, ?, ?, ?, ?)",
            (
                employee_data['name'],
                employee_data['email'],
                employee_data.get('phone', ''),
                employee_data.get('position', ''),
                employee_data.get('hire_date', ''),
                employee_data.get('salary', 0)
            )
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'id': new_id, 'message': 'Employee added successfully'}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'message': 'Email already exists'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'message': str(e)}), 400

@app.route('/api/employees/<int:employee_id>', methods=['GET'])
@login_required
def get_employee(employee_id):
    conn = sqlite3.connect('employee.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
    employee = cursor.fetchone()
    conn.close()
    
    if employee:
        return jsonify(dict(employee))
    return jsonify({'message': 'Employee not found'}), 404

@app.route('/api/employees/<int:employee_id>', methods=['PUT'])
@login_required
def update_employee(employee_id):
    employee_data = request.json
    
    conn = sqlite3.connect('employee.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE employees SET name=?, email=?, phone=?, position=?, hire_date=?, salary=? WHERE id=?",
            (
                employee_data['name'],
                employee_data['email'],
                employee_data.get('phone', ''),
                employee_data.get('position', ''),
                employee_data.get('hire_date', ''),
                employee_data.get('salary', 0),
                employee_id
            )
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'message': 'Employee not found'}), 404
            
        conn.close()
        return jsonify({'message': 'Employee updated successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'message': str(e)}), 400

@app.route('/api/employees/<int:employee_id>', methods=['DELETE'])
@login_required
def delete_employee(employee_id):
    conn = sqlite3.connect('employee.db')
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM employees WHERE id=?", (employee_id,))
    conn.commit()
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'message': 'Employee not found'}), 404
        
    conn.close()
    return jsonify({'message': 'Employee deleted successfully'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)