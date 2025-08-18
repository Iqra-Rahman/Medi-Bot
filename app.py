from flask import Flask, request, jsonify, render_template
import sqlite3
import traceback
from workflow import chat_agent
from datetime import datetime
import os

app = Flask(__name__)
app.static_folder = 'static'

# Base directory for database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "healthcare_bot.db")

# Database connection
def get_db_connection():
    conn = sqlite3.connect('healthcare_bot.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Database schema with patient detail fields
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT NOT NULL,
        patient_age INTEGER,
        patient_gender TEXT,
        patient_contact TEXT,
        appointment_date TEXT NOT NULL,
        appointment_time TEXT NOT NULL,
        department TEXT NOT NULL,
        status TEXT DEFAULT 'Scheduled'
    )
    ''')
    conn.commit()
    # conn.close()

    # Insert demo data if table is empty ++
    existing = conn.execute("SELECT COUNT(*) as count FROM appointments").fetchone()
    if existing["count"] == 0:
        cursor.execute('''
        INSERT INTO appointments 
        (patient_name, patient_age, patient_gender, patient_contact, appointment_date, appointment_time, department)
        VALUES ("John Doe", 30, "Male", "1234567890", "2025-08-20", "10:00", "Cardiology")
        ''')
        cursor.execute('''
        INSERT INTO appointments 
        (patient_name, patient_age, patient_gender, patient_contact, appointment_date, appointment_time, department)
        VALUES ("Jane Smith", 25, "Female", "9876543210", "2025-08-21", "15:00", "Dermatology")
        ''')
        conn.commit()

    conn.close()

# Homepage with the two-column layout
@app.route('/')
def index():
    conn = get_db_connection()
    appointments = conn.execute('SELECT * FROM appointments ORDER BY appointment_date, appointment_time').fetchall()
    conn.close()
    return render_template('chat.html', appointments=appointments)

# Route to fetch appointment list items for AJAX updates
@app.route('/appointments')
def view_appointments():
    conn = get_db_connection()
    appointments = conn.execute('SELECT * FROM appointments ORDER BY appointment_date, appointment_time').fetchall()
    conn.close()
    # ## UPDATED to render the list partial ##
    return render_template('_appointments_list.html', appointments=appointments)

# API endpoint to get details of a single appointment
@app.route('/api/appointment/<int:appointment_id>', methods=['GET'])
def get_appointment_details(appointment_id):
    conn = get_db_connection()
    appointment = conn.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,)).fetchone()
    conn.close()
    if appointment is None:
        return jsonify({"error": "Appointment not found"}), 404
    return jsonify(dict(appointment))


# Chat endpoint
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    try:
        response = chat_agent.invoke(message)
        return jsonify({"response": response})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"response": "I apologize, but an error occurred."}), 500

# Book an appointment
@app.route('/book', methods=['POST'])
def book_appointment():
    data = request.json
    appointment_date_str = data.get('appointment_date')
    appointment_time_str = data.get('appointment_time')

    try:
        if datetime.strptime(f"{appointment_date_str} {appointment_time_str}", "%Y-%m-%d %H:%M") < datetime.now():
            return jsonify({"status": "error", "message": "Cannot book an appointment in the past."}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid date or time format."}), 400

    patient_name = data.get('patient_name')
    patient_age = data.get('patient_age')
    patient_gender = data.get('patient_gender')
    patient_contact = data.get('patient_contact')
    department = data.get('department')

    if not all([patient_name, patient_age, patient_gender, patient_contact, department, appointment_date_str, appointment_time_str]):
        return jsonify({"status": "error", "message": "All fields are required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO appointments (patient_name, patient_age, patient_gender, patient_contact, department, appointment_date, appointment_time) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (patient_name, patient_age, patient_gender, patient_contact, department, appointment_date_str, appointment_time_str))
    appointment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Appointment booked successfully!", "appointment_id": appointment_id})

# Cancel an appointment
@app.route('/cancel/<int:appointment_id>', methods=['GET'])
def cancel_appointment(appointment_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE appointments SET status = "Cancelled" WHERE id = ?', (appointment_id,))
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"status": "error", "message": "Appointment ID not found."}), 404
    conn.close()
    return jsonify({"status": "success", "message": "Appointment cancelled successfully!"})

# Reschedule an appointment
@app.route('/reschedule/<int:appointment_id>', methods=['POST'])
def reschedule_appointment(appointment_id):
    data = request.json
    new_date_str = data.get('new_date')
    new_time_str = data.get('new_time')

    try:
        if datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M") < datetime.now():
            return jsonify({"status": "error", "message": "Cannot reschedule to a past date/time."}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid date or time format."}), 400

    patient_name = data.get('patient_name')
    patient_age = data.get('patient_age')
    patient_gender = data.get('patient_gender')
    patient_contact = data.get('patient_contact')

    if not all([new_date_str, new_time_str, patient_name, patient_age, patient_gender, patient_contact]):
        return jsonify({"status": "error", "message": "All fields are required for rescheduling."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE appointments SET appointment_date = ?, appointment_time = ?, status = "Rescheduled", patient_name = ?, patient_age = ?, patient_gender = ?, patient_contact = ? WHERE id = ?',
                   (new_date_str, new_time_str, patient_name, patient_age, patient_gender, patient_contact, appointment_id))
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"status": "error", "message": "Appointment ID not found."}), 404
    conn.close()
    return jsonify({"status": "success", "message": "Appointment rescheduled successfully!"})

# Run the Flask app
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
else:
    # This runs when deployed (via gunicorn)
    init_db()   