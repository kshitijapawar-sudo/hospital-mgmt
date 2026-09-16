#!/usr/bin/env python3
"""
MediCare HMS — Backend Server
Run: python3 server.py
Requires: Python 3.8+ (uses only standard library)
"""

import json
import sqlite3
import uuid
import socket
import mimetypes
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'hospital.db')
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

# Bumped every time this process starts (e.g. after an auto-update restart).
# The frontend polls /api/version and auto-reloads itself when this changes,
# so a developer's update rolled out on the server PC reaches every browser
# (doctor's laptop, receptionist's PC) without anyone touching those machines.
SERVER_VERSION = str(int(time.time()))


# ─── DATABASE SETUP ─────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS doctors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS outpatients (
            id TEXT PRIMARY KEY,
            patient_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT DEFAULT '',
            symptoms TEXT NOT NULL,
            diagnosis TEXT DEFAULT '',
            prescription TEXT DEFAULT '',
            doctor_id TEXT NOT NULL,
            visit_date TEXT NOT NULL,
            visit_time TEXT NOT NULL,
            follow_up_date TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE IF NOT EXISTS hospital_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            hospital_name TEXT NOT NULL DEFAULT 'MediCare HMS',
            tagline TEXT DEFAULT 'Hospital Management System',
            address TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            reg_no TEXT DEFAULT '',
            logo_data TEXT DEFAULT '',
            next_opd_no INTEGER NOT NULL DEFAULT 1,
            next_ipd_no INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS bills (
            id TEXT PRIMARY KEY,
            bill_no TEXT NOT NULL UNIQUE,
            bill_type TEXT NOT NULL CHECK (bill_type IN ('OPD','IPD')),
            bill_date TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            age TEXT DEFAULT '',
            gender TEXT DEFAULT '',
            address TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            indoor_no TEXT DEFAULT '',
            admission_date TEXT DEFAULT '',
            discharge_date TEXT DEFAULT '',
            diagnostic TEXT DEFAULT '',
            doctor_id TEXT NOT NULL,
            items_json TEXT NOT NULL DEFAULT '[]',
            total REAL NOT NULL DEFAULT 0,
            payment_mode TEXT NOT NULL DEFAULT 'cash' CHECK (payment_mode IN ('cash','online')),
            utr_code TEXT DEFAULT '',
            outpatient_id TEXT DEFAULT '',
            inpatient_id TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );
        CREATE INDEX IF NOT EXISTS idx_bills_date ON bills(bill_date);
        CREATE INDEX IF NOT EXISTS idx_bills_doctor ON bills(doctor_id);
        CREATE INDEX IF NOT EXISTS idx_bills_type ON bills(bill_type);
        CREATE INDEX IF NOT EXISTS idx_bills_patient ON bills(patient_name);

        CREATE TABLE IF NOT EXISTS sonography (
            id TEXT PRIMARY KEY,
            entry_no TEXT NOT NULL UNIQUE,
            entry_date TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            age TEXT DEFAULT '',
            husband_father_name TEXT DEFAULT '',
            address TEXT DEFAULT '',
            contact TEXT DEFAULT '',
            living_sons TEXT DEFAULT '',
            living_daughters TEXT DEFAULT '',
            referred_by TEXT DEFAULT '',
            lmp TEXT DEFAULT '',
            indications TEXT DEFAULT '[]',
            procedure_done TEXT DEFAULT 'Ultrasound',
            doctor_id TEXT DEFAULT '',
            procedure_date TEXT DEFAULT '',
            result_notes TEXT DEFAULT '',
            declaration_no_sex_disclosed INTEGER DEFAULT 1,
            extra_fields_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );
        CREATE INDEX IF NOT EXISTS idx_sono_date ON sonography(entry_date);
        CREATE INDEX IF NOT EXISTS idx_sono_patient ON sonography(patient_name);

        CREATE TABLE IF NOT EXISTS inpatients (
            id TEXT PRIMARY KEY,
            patient_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT DEFAULT '',
            emergency_contact TEXT DEFAULT '',
            emergency_phone TEXT DEFAULT '',
            admission_date TEXT NOT NULL,
            admission_time TEXT NOT NULL,
            ward TEXT NOT NULL,
            bed_number TEXT NOT NULL,
            diagnosis TEXT NOT NULL,
            treatment TEXT DEFAULT '',
            doctor_id TEXT NOT NULL,
            discharge_date TEXT DEFAULT '',
            discharge_time TEXT DEFAULT '',
            status TEXT DEFAULT 'admitted',
            notes TEXT DEFAULT '',
            photo_description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('doctor', 'operator', 'receptionist')),
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)

    # Seed users
    ucnt = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if ucnt == 0:
        useed = [
            (str(uuid.uuid4()), 'doctor',       'doctor123',       'Dr. Administrator',    'doctor'),
            (str(uuid.uuid4()), 'operator',     'operator123',     'Hospital Operator',    'operator'),
            (str(uuid.uuid4()), 'receptionist', 'receptionist123', 'Hospital Receptionist','receptionist'),
        ]
        c.executemany("INSERT INTO users (id,username,password,name,role) VALUES (?,?,?,?,?)", useed)

    # Seed doctors
    cnt = c.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
    if cnt == 0:
        seed = [
            (str(uuid.uuid4()), 'Dr. Rajesh Kumar',  'General Physician',  '9876543210', 'rajesh@hospital.com'),
            (str(uuid.uuid4()), 'Dr. Priya Sharma',  'Cardiologist',       '9876543211', 'priya@hospital.com'),
            (str(uuid.uuid4()), 'Dr. Anil Mehta',    'Orthopedic Surgeon', '9876543212', 'anil@hospital.com'),
            (str(uuid.uuid4()), 'Dr. Sunita Patel',  'Neurologist',        '9876543213', 'sunita@hospital.com'),
            (str(uuid.uuid4()), 'Dr. Vikram Singh',  'Pediatrician',       '9876543214', 'vikram@hospital.com'),
        ]
        c.executemany("INSERT INTO doctors (id,name,specialization,phone,email) VALUES (?,?,?,?,?)", seed)

    # Seed hospital settings (singleton row)
    scnt = c.execute("SELECT COUNT(*) FROM hospital_settings").fetchone()[0]
    if scnt == 0:
        c.execute("""INSERT INTO hospital_settings
            (id,hospital_name,tagline,address,phone,reg_no,logo_data,next_opd_no,next_ipd_no)
            VALUES (1,'Maale Hospital','Hospital Management System','','','','',1,1)""")

    # Schema Migrations
    cols = [col[1] for col in c.execute('PRAGMA table_info(inpatients)').fetchall()]
    if 'photo_description' not in cols:
        c.execute("ALTER TABLE inpatients ADD COLUMN photo_description TEXT DEFAULT ''")
    if 'referred_by' not in cols:
        c.execute("ALTER TABLE inpatients ADD COLUMN referred_by TEXT DEFAULT ''")
    if 'advance_paid' not in cols:
        c.execute("ALTER TABLE inpatients ADD COLUMN advance_paid REAL DEFAULT 0")

    out_cols = [col[1] for col in c.execute('PRAGMA table_info(outpatients)').fetchall()]
    if 'referred_by' not in out_cols:
        c.execute("ALTER TABLE outpatients ADD COLUMN referred_by TEXT DEFAULT ''")

    sono_cols = [col[1] for col in c.execute('PRAGMA table_info(sonography)').fetchall()]
    if 'extra_fields_json' not in sono_cols:
        c.execute("ALTER TABLE sonography ADD COLUMN extra_fields_json TEXT DEFAULT '{}'")

    bill_cols = [col[1] for col in c.execute('PRAGMA table_info(bills)').fetchall()]
    if 'advance_paid' not in bill_cols:
        c.execute("ALTER TABLE bills ADD COLUMN advance_paid REAL DEFAULT 0")
    if 'net_total' not in bill_cols:
        c.execute("ALTER TABLE bills ADD COLUMN net_total REAL DEFAULT 0")

    sett_cols = [col[1] for col in c.execute('PRAGMA table_info(hospital_settings)').fetchall()]
    if 'ward_tariffs_json' not in sett_cols:
        c.execute("ALTER TABLE hospital_settings ADD COLUMN ward_tariffs_json TEXT DEFAULT '{}'")

    c.executescript("""
        CREATE TABLE IF NOT EXISTS referral_doctors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            specialization TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            hospital TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS mtp_records (
            id TEXT PRIMARY KEY,
            entry_no TEXT NOT NULL UNIQUE,
            entry_date TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            age TEXT DEFAULT '',
            husband_father_name TEXT DEFAULT '',
            address TEXT DEFAULT '',
            contact TEXT DEFAULT '',
            weeks TEXT DEFAULT '',
            doctor_id TEXT DEFAULT '',
            referred_by TEXT DEFAULT '',
            indication TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            extra_fields_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );
        CREATE INDEX IF NOT EXISTS idx_mtp_date ON mtp_records(entry_date);
        CREATE INDEX IF NOT EXISTS idx_mtp_patient ON mtp_records(patient_name);
    """)

    conn.commit()
    conn.close()

# Default item templates shown when starting a new bill (fully editable by the user)
OPD_DEFAULT_ITEMS = [
    {"description": "Registration Charges", "amount": 0},
    {"description": "Consultation", "amount": 0},
    {"description": "Pathology Charges", "amount": 0},
    {"description": "X-Ray/ECG/USG Charges", "amount": 0},
    {"description": "Medicine Charges", "amount": 0},
]
IPD_DEFAULT_ITEMS = [
    {"description": "Consultation Charges", "amount": 0, "rate": 0, "days": 1, "is_daywise": True},
    {"description": "Bed Charges", "amount": 0, "rate": 0, "days": 1, "is_daywise": True},
    {"description": "Nursing Charges", "amount": 0, "rate": 0, "days": 1, "is_daywise": True},
    {"description": "RMO Charges", "amount": 0, "rate": 0, "days": 1, "is_daywise": True},
    {"description": "Ward Charges", "amount": 0, "rate": 0, "days": 1, "is_daywise": True},
    {"description": "OT Charges", "amount": 0},
    {"description": "Surgeon Charges", "amount": 0},
    {"description": "Assistant Charges", "amount": 0},
    {"description": "Anesthetic Charges", "amount": 0},
    {"description": "Visit Charges", "amount": 0},
    {"description": "Pathology Charges", "amount": 0},
    {"description": "X-Ray/ECG/USG Charges", "amount": 0},
    {"description": "Monitor/O2 Charges", "amount": 0},
    {"description": "Dressing Charges", "amount": 0},
    {"description": "Medicine Charges", "amount": 0},
    {"description": "Registration Charges", "amount": 0},
]

def next_bill_no(c, bill_type):
    """Atomically reserve and return the next human-friendly bill number for OPD or IPD."""
    col = 'next_opd_no' if bill_type == 'OPD' else 'next_ipd_no'
    row = c.execute(f"SELECT {col} FROM hospital_settings WHERE id=1").fetchone()
    n = row[0] if row else 1
    c.execute(f"UPDATE hospital_settings SET {col}=? WHERE id=1", (n + 1,))
    return f"{bill_type}-{datetime.now().year}-{n:04d}"

# ─── HTTP HANDLER ────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default logs

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def route(self, method):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        parts = path.split('/')  # ['', 'api', 'resource', 'id?']
        conn = get_db()
        c = conn.cursor()

        try:
            # ── VERSION (used by frontend to auto-refresh after an update) ──
            if path == '/api/version':
                return self.send_json({'version': SERVER_VERSION})

            # ── AUTH & USERS ──
            if path == '/api/login':
                if method == 'POST':
                    b = self.read_body()
                    username = (b.get('username') or '').strip().lower()
                    password = (b.get('password') or '').strip()
                    if not username or not password:
                        return self.send_json({'error': 'Username and password required'}, 400)
                    row = c.execute("SELECT id, username, name, role FROM users WHERE LOWER(username)=? AND password=?",
                                    (username, password)).fetchone()
                    if not row:
                        return self.send_json({'error': 'Invalid username or password'}, 401)
                    user_data = dict(row)
                    self.send_json({'success': True, 'user': user_data})

            elif path == '/api/users':
                if method == 'GET':
                    rows = c.execute("SELECT id, username, name, role, created_at FROM users ORDER BY role, name").fetchall()
                    self.send_json([dict(r) for r in rows])
                elif method == 'POST':
                    b = self.read_body()
                    if not b.get('username') or not b.get('password') or not b.get('name') or not b.get('role'):
                        return self.send_json({'error': 'Username, password, name, and role required'}, 400)
                    if b['role'] not in ('doctor', 'operator', 'receptionist'):
                        return self.send_json({'error': 'Invalid role'}, 400)
                    rid = str(uuid.uuid4())
                    try:
                        c.execute("INSERT INTO users (id,username,password,name,role) VALUES (?,?,?,?,?)",
                                  (rid, b['username'].strip().lower(), b['password'].strip(), b['name'].strip(), b['role']))
                        conn.commit()
                        self.send_json({'id': rid, 'username': b['username'], 'name': b['name'], 'role': b['role']})
                    except sqlite3.IntegrityError:
                        self.send_json({'error': 'Username already exists'}, 400)

            elif path.startswith('/api/users/') and len(parts) == 5 and parts[4] == 'password':
                uid = parts[3]
                if method == 'PUT':
                    b = self.read_body()
                    new_password = (b.get('password') or '').strip()
                    if not new_password:
                        return self.send_json({'error': 'New password required'}, 400)
                    c.execute("UPDATE users SET password=? WHERE id=?", (new_password, uid))
                    conn.commit()
                    self.send_json({'success': True, 'message': 'Password updated successfully'})

            # ── DOCTORS ──
            elif path == '/api/doctors':
                if method == 'GET':
                    rows = c.execute("SELECT * FROM doctors ORDER BY name").fetchall()
                    self.send_json([dict(r) for r in rows])

                elif method == 'POST':
                    b = self.read_body()
                    if not b.get('name') or not b.get('specialization'):
                        return self.send_json({'error': 'Name and specialization required'}, 400)
                    rid = str(uuid.uuid4())
                    c.execute("INSERT INTO doctors (id,name,specialization,phone,email) VALUES (?,?,?,?,?)",
                              (rid, b['name'], b['specialization'], b.get('phone',''), b.get('email','')))
                    conn.commit()
                    self.send_json({'id': rid, **b})

            elif path.startswith('/api/doctors/') and len(parts) == 4 and parts[3] != 'patients':
                rid = parts[3]
                if method == 'DELETE':
                    c.execute("DELETE FROM doctors WHERE id=?", (rid,))
                    conn.commit()
                    self.send_json({'success': True})

            elif path.startswith('/api/doctors/') and len(parts) == 5 and parts[4] == 'patients':
                doc_id = parts[3]
                if method == 'GET':
                    # Doctor analytics: get all OPD and IPD visits for doctor_id
                    opd_rows = c.execute("""
                        SELECT o.id, o.patient_name, o.age, o.gender, o.phone, o.symptoms, o.diagnosis,
                               o.visit_date as visit_date, o.visit_time as visit_time, 'OPD' as type
                        FROM outpatients o WHERE o.doctor_id=?
                        ORDER BY o.visit_date DESC
                    """, (doc_id,)).fetchall()

                    ipd_rows = c.execute("""
                        SELECT i.id, i.patient_name, i.age, i.gender, i.phone, i.diagnosis,
                               i.admission_date as visit_date, i.admission_time as visit_time, 'IPD' as type,
                               i.ward, i.bed_number, i.status
                        FROM inpatients i WHERE i.doctor_id=?
                        ORDER BY i.admission_date DESC
                    """, (doc_id,)).fetchall()

                    opd_list = [dict(r) for r in opd_rows]
                    ipd_list = [dict(r) for r in ipd_rows]
                    all_patients = sorted(opd_list + ipd_list, key=lambda x: x.get('visit_date',''), reverse=True)

                    # Calculate weekly & monthly count
                    today_dt = datetime.now()
                    curr_week_start = today_dt.date() - timedelta(days=today_dt.weekday())
                    curr_month_str = today_dt.strftime('%Y-%m')

                    weekly_patients = []
                    monthly_patients = []
                    by_month = {}

                    for p in all_patients:
                        vdate_str = p.get('visit_date', '')
                        if vdate_str:
                            try:
                                vdate = datetime.strptime(vdate_str[:10], '%Y-%m-%d').date()
                                if vdate >= curr_week_start:
                                    weekly_patients.append(p)
                                mstr = vdate.strftime('%Y-%m')
                                if mstr not in by_month:
                                    by_month[mstr] = []
                                by_month[mstr].append(p)
                                if mstr == curr_month_str:
                                    monthly_patients.append(p)
                            except Exception:
                                pass

                    self.send_json({
                        'all_patients': all_patients,
                        'total_count': len(all_patients),
                        'weekly_patients': weekly_patients,
                        'weekly_count': len(weekly_patients),
                        'monthly_patients': monthly_patients,
                        'monthly_count': len(monthly_patients),
                        'by_month': by_month
                    })

            # ── REFERRAL DOCTORS ──
            elif path == '/api/referral_doctors':
                if method == 'GET':
                    rows = c.execute("SELECT * FROM referral_doctors ORDER BY name").fetchall()
                    self.send_json([dict(r) for r in rows])

                elif method == 'POST':
                    b = self.read_body()
                    if not b.get('name'):
                        return self.send_json({'error': 'Name required'}, 400)
                    rid = str(uuid.uuid4())
                    c.execute("INSERT INTO referral_doctors (id,name,specialization,phone,hospital) VALUES (?,?,?,?,?)",
                              (rid, b['name'], b.get('specialization',''), b.get('phone',''), b.get('hospital','')))
                    conn.commit()
                    self.send_json({'id': rid, **b})

            elif path.startswith('/api/referral_doctors/') and len(parts) == 4 and parts[3] != 'patients':
                rid = parts[3]
                if method == 'DELETE':
                    c.execute("DELETE FROM referral_doctors WHERE id=?", (rid,))
                    conn.commit()
                    self.send_json({'success': True})

            elif path.startswith('/api/referral_doctors/') and len(parts) == 5 and parts[4] == 'patients':
                ref_id = parts[3]
                if method == 'GET':
                    ref_doc = c.execute("SELECT * FROM referral_doctors WHERE id=?", (ref_id,)).fetchone()
                    ref_name = ref_doc['name'] if ref_doc else ''

                    opd_rows = c.execute("""
                        SELECT o.id, o.patient_name, o.age, o.gender, o.phone, o.symptoms, o.diagnosis,
                               o.visit_date as visit_date, o.visit_time as visit_time, 'OPD' as type,
                               d.name as doctor_name
                        FROM outpatients o LEFT JOIN doctors d ON o.doctor_id=d.id
                        WHERE o.referred_by=? OR o.referred_by=?
                        ORDER BY o.visit_date DESC
                    """, (ref_id, ref_name)).fetchall()

                    ipd_rows = c.execute("""
                        SELECT i.id, i.patient_name, i.age, i.gender, i.phone, i.diagnosis,
                               i.admission_date as visit_date, i.admission_time as visit_time, 'IPD' as type,
                               i.ward, i.bed_number, i.status, d.name as doctor_name
                        FROM inpatients i LEFT JOIN doctors d ON i.doctor_id=d.id
                        WHERE i.referred_by=? OR i.referred_by=?
                        ORDER BY i.admission_date DESC
                    """, (ref_id, ref_name)).fetchall()

                    opd_list = [dict(r) for r in opd_rows]
                    ipd_list = [dict(r) for r in ipd_rows]
                    all_referred = sorted(opd_list + ipd_list, key=lambda x: x.get('visit_date',''), reverse=True)

                    self.send_json({
                        'referral_doctor': dict(ref_doc) if ref_doc else {},
                        'patients': all_referred,
                        'total_count': len(all_referred)
                    })

            # ── OUTPATIENTS ──
            elif path == '/api/outpatients':
                if method == 'GET':
                    rows = c.execute("""
                        SELECT o.*, d.name as doctor_name, d.specialization
                        FROM outpatients o JOIN doctors d ON o.doctor_id=d.id
                        ORDER BY o.visit_date DESC, o.visit_time DESC
                    """).fetchall()
                    self.send_json([dict(r) for r in rows])

                elif method == 'POST':
                    b = self.read_body()
                    required = ['patient_name','age','gender','phone','symptoms','doctor_id','visit_date','visit_time']
                    if any(not b.get(k) for k in required):
                        return self.send_json({'error': 'Required fields missing'}, 400)
                    rid = str(uuid.uuid4())
                    c.execute("""INSERT INTO outpatients
                        (id,patient_name,age,gender,phone,address,symptoms,diagnosis,prescription,
                         doctor_id,visit_date,visit_time,follow_up_date,notes,referred_by)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (rid, b['patient_name'], b['age'], b['gender'], b['phone'],
                         b.get('address',''), b['symptoms'], b.get('diagnosis',''),
                         b.get('prescription',''), b['doctor_id'], b['visit_date'],
                         b['visit_time'], b.get('follow_up_date',''), b.get('notes',''), b.get('referred_by','')))
                    conn.commit()
                    self.send_json({'id': rid, **b})

            elif path.startswith('/api/outpatients/') and len(parts) == 4:
                rid = parts[3]
                if method == 'PUT':
                    b = self.read_body()
                    c.execute("""UPDATE outpatients SET
                        patient_name=?,age=?,gender=?,phone=?,address=?,symptoms=?,
                        diagnosis=?,prescription=?,doctor_id=?,visit_date=?,visit_time=?,
                        follow_up_date=?,notes=?,referred_by=? WHERE id=?""",
                        (b['patient_name'],b['age'],b['gender'],b['phone'],b.get('address',''),
                         b['symptoms'],b.get('diagnosis',''),b.get('prescription',''),
                         b['doctor_id'],b['visit_date'],b['visit_time'],
                         b.get('follow_up_date',''),b.get('notes',''),b.get('referred_by',''),rid))
                    conn.commit()
                    self.send_json({'success': True})
                elif method == 'DELETE':
                    c.execute("DELETE FROM outpatients WHERE id=?", (rid,))
                    conn.commit()
                    self.send_json({'success': True})

            # ── INPATIENTS ──
            elif path == '/api/inpatients':
                if method == 'GET':
                    rows = c.execute("""
                        SELECT i.*, d.name as doctor_name, d.specialization
                        FROM inpatients i JOIN doctors d ON i.doctor_id=d.id
                        ORDER BY i.admission_date DESC, i.admission_time DESC
                    """).fetchall()
                    self.send_json([dict(r) for r in rows])

                elif method == 'POST':
                    b = self.read_body()
                    required = ['patient_name','age','gender','phone','doctor_id','ward','bed_number','admission_date','admission_time','diagnosis']
                    if any(not b.get(k) for k in required):
                        return self.send_json({'error': 'Required fields missing'}, 400)
                    rid = str(uuid.uuid4())
                    adv_paid = float(b.get('advance_paid') or 0)
                    c.execute("""INSERT INTO inpatients
                        (id,patient_name,age,gender,phone,address,emergency_contact,emergency_phone,
                         admission_date,admission_time,ward,bed_number,diagnosis,treatment,doctor_id,
                         discharge_date,discharge_time,status,notes,photo_description,referred_by,advance_paid)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (rid,b['patient_name'],b['age'],b['gender'],b['phone'],
                         b.get('address',''),b.get('emergency_contact',''),b.get('emergency_phone',''),
                         b['admission_date'],b['admission_time'],b['ward'],b['bed_number'],
                         b['diagnosis'],b.get('treatment',''),b['doctor_id'],
                         b.get('discharge_date',''),b.get('discharge_time',''),
                         b.get('status','admitted'),b.get('notes',''),b.get('photo_description',''),b.get('referred_by',''),adv_paid))
                    conn.commit()
                    self.send_json({'id': rid, **b})

            elif path.startswith('/api/inpatients/') and len(parts) == 4:
                rid = parts[3]
                if method == 'PUT':
                    b = self.read_body()
                    adv_paid = float(b.get('advance_paid') or 0)
                    c.execute("""UPDATE inpatients SET
                        patient_name=?,age=?,gender=?,phone=?,address=?,
                        emergency_contact=?,emergency_phone=?,admission_date=?,admission_time=?,
                        ward=?,bed_number=?,diagnosis=?,treatment=?,doctor_id=?,
                        discharge_date=?,discharge_time=?,status=?,notes=?,photo_description=?,referred_by=?,advance_paid=? WHERE id=?""",
                        (b['patient_name'],b['age'],b['gender'],b['phone'],b.get('address',''),
                         b.get('emergency_contact',''),b.get('emergency_phone',''),
                         b['admission_date'],b['admission_time'],b['ward'],b['bed_number'],
                         b['diagnosis'],b.get('treatment',''),b['doctor_id'],
                         b.get('discharge_date',''),b.get('discharge_time',''),
                         b.get('status','admitted'),b.get('notes',''),b.get('photo_description',''),b.get('referred_by',''),adv_paid,rid))
                    conn.commit()
                    self.send_json({'success': True})
                elif method == 'DELETE':
                    c.execute("DELETE FROM inpatients WHERE id=?", (rid,))
                    conn.commit()
                    self.send_json({'success': True})

            # ── HOSPITAL SETTINGS ──
            elif path == '/api/settings':
                if method == 'GET':
                    row = c.execute("SELECT * FROM hospital_settings WHERE id=1").fetchone()
                    self.send_json(dict(row) if row else {})
                elif method == 'PUT':
                    b = self.read_body()
                    c.execute("""UPDATE hospital_settings SET
                        hospital_name=?, tagline=?, address=?, phone=?, reg_no=?, logo_data=?, ward_tariffs_json=?
                        WHERE id=1""",
                        (b.get('hospital_name','MediCare HMS'), b.get('tagline',''),
                         b.get('address',''), b.get('phone',''), b.get('reg_no',''),
                         b.get('logo_data',''), b.get('ward_tariffs_json','{}')))
                    conn.commit()
                    row = c.execute("SELECT * FROM hospital_settings WHERE id=1").fetchone()
                    self.send_json(dict(row))

            # ── BILL ITEM TEMPLATES ──
            elif path == '/api/bill-templates':
                self.send_json({'OPD': OPD_DEFAULT_ITEMS, 'IPD': IPD_DEFAULT_ITEMS})

            # ── BILLS ──
            elif path == '/api/bills':
                if method == 'GET':
                    q = parse_qs(parsed.query)
                    sql = """SELECT b.*, d.name as doctor_name, d.specialization
                              FROM bills b JOIN doctors d ON b.doctor_id=d.id WHERE 1=1"""
                    args = []
                    if q.get('type'):
                        sql += " AND b.bill_type=?"; args.append(q['type'][0])
                    if q.get('doctor_id'):
                        sql += " AND b.doctor_id=?"; args.append(q['doctor_id'][0])
                    if q.get('date_from'):
                        sql += " AND b.bill_date>=?"; args.append(q['date_from'][0])
                    if q.get('date_to'):
                        sql += " AND b.bill_date<=?"; args.append(q['date_to'][0])
                    if q.get('search'):
                        sql += " AND (b.patient_name LIKE ? OR b.bill_no LIKE ?)"
                        term = f"%{q['search'][0]}%"; args += [term, term]
                    sql += " ORDER BY b.bill_date DESC, b.created_at DESC"
                    rows = c.execute(sql, args).fetchall()
                    self.send_json([dict(r) for r in rows])

                elif method == 'POST':
                    b = self.read_body()
                    required = ['bill_type','bill_date','patient_name','doctor_id','items']
                    if any(not b.get(k) for k in required):
                        return self.send_json({'error': 'Required fields missing'}, 400)
                    if b['bill_type'] not in ('OPD','IPD'):
                        return self.send_json({'error': 'Invalid bill type'}, 400)
                    if b.get('payment_mode') == 'online' and not b.get('utr_code'):
                        return self.send_json({'error': 'UTR / transaction code required for online payment'}, 400)
                    items = b['items']
                    total = sum(float(it.get('amount') or 0) for it in items)
                    adv_paid = float(b.get('advance_paid') or 0)
                    net_total = float(b.get('net_total') if b.get('net_total') is not None else max(0, total - adv_paid))
                    rid = str(uuid.uuid4())
                    bill_no = next_bill_no(c, b['bill_type'])
                    c.execute("""INSERT INTO bills
                        (id,bill_no,bill_type,bill_date,patient_name,age,gender,address,phone,
                         indoor_no,admission_date,discharge_date,diagnostic,doctor_id,items_json,
                         total,payment_mode,utr_code,outpatient_id,inpatient_id,advance_paid,net_total)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (rid, bill_no, b['bill_type'], b['bill_date'], b['patient_name'],
                         str(b.get('age','')), b.get('gender',''), b.get('address',''),
                         b.get('phone',''), b.get('indoor_no',''), b.get('admission_date',''),
                         b.get('discharge_date',''), b.get('diagnostic',''), b['doctor_id'],
                         json.dumps(items), total, b.get('payment_mode','cash'),
                         b.get('utr_code',''), b.get('outpatient_id',''), b.get('inpatient_id',''),
                         adv_paid, net_total))
                    conn.commit()
                    row = c.execute("""SELECT b.*, d.name as doctor_name, d.specialization
                                        FROM bills b JOIN doctors d ON b.doctor_id=d.id
                                        WHERE b.id=?""", (rid,)).fetchone()
                    self.send_json(dict(row))

            elif path.startswith('/api/bills/') and len(parts) == 4:
                rid = parts[3]
                if method == 'GET':
                    row = c.execute("""SELECT b.*, d.name as doctor_name, d.specialization
                                        FROM bills b JOIN doctors d ON b.doctor_id=d.id
                                        WHERE b.id=?""", (rid,)).fetchone()
                    self.send_json(dict(row) if row else {'error':'Not found'}, 200 if row else 404)
                elif method == 'DELETE':
                    c.execute("DELETE FROM bills WHERE id=?", (rid,))
                    conn.commit()
                    self.send_json({'success': True})

            # ── MTP (Medical Termination of Pregnancy) ──
            elif path == '/api/mtp':
                if method == 'GET':
                    q = parse_qs(parsed.query)
                    sql = """SELECT m.*, d.name as doctor_name
                              FROM mtp_records m LEFT JOIN doctors d ON m.doctor_id=d.id WHERE 1=1"""
                    args = []
                    if q.get('date_from'):
                        sql += " AND m.entry_date>=?"; args.append(q['date_from'][0])
                    if q.get('date_to'):
                        sql += " AND m.entry_date<=?"; args.append(q['date_to'][0])
                    if q.get('search'):
                        sql += " AND (m.patient_name LIKE ? OR m.entry_no LIKE ?)"
                        term = f"%{q['search'][0]}%"; args += [term, term]
                    sql += " ORDER BY m.entry_date DESC, m.created_at DESC"
                    rows = c.execute(sql, args).fetchall()
                    self.send_json([dict(r) for r in rows])

                elif method == 'POST':
                    b = self.read_body()
                    required = ['entry_date','patient_name']
                    if any(not b.get(k) for k in required):
                        return self.send_json({'error': 'Required fields missing'}, 400)
                    rid = b.get('id') or str(uuid.uuid4())
                    entry_no_val = (b.get('entry_no') or '').strip()
                    existing = c.execute("SELECT id, entry_no FROM mtp_records WHERE id=?", (rid,)).fetchone()
                    if existing:
                        final_entry_no = entry_no_val if entry_no_val else existing['entry_no']
                        c.execute("""UPDATE mtp_records SET
                            entry_no=?, entry_date=?, patient_name=?, age=?, husband_father_name=?, address=?, contact=?,
                            weeks=?, doctor_id=?, referred_by=?, indication=?, notes=?, extra_fields_json=?
                            WHERE id=?""",
                            (final_entry_no, b['entry_date'], b['patient_name'], str(b.get('age','')),
                             b.get('husband_father_name',''), b.get('address',''), b.get('contact',''),
                             b.get('weeks',''), b.get('doctor_id',''), b.get('referred_by',''),
                             b.get('indication',''), b.get('notes',''),
                             json.dumps(b.get('extra_fields', {})), rid))
                    else:
                        seq = c.execute("SELECT COUNT(*) FROM mtp_records").fetchone()[0] + 1
                        final_entry_no = entry_no_val if entry_no_val else f"RMO-{datetime.now().year}-{seq:04d}"
                        c.execute("""INSERT INTO mtp_records
                            (id,entry_no,entry_date,patient_name,age,husband_father_name,address,contact,
                             weeks,doctor_id,referred_by,indication,notes,extra_fields_json)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (rid, final_entry_no, b['entry_date'], b['patient_name'], str(b.get('age','')),
                             b.get('husband_father_name',''), b.get('address',''), b.get('contact',''),
                             b.get('weeks',''), b.get('doctor_id',''), b.get('referred_by',''),
                             b.get('indication',''), b.get('notes',''),
                             json.dumps(b.get('extra_fields', {}))))
                    conn.commit()
                    row = c.execute("""SELECT m.*, d.name as doctor_name
                                        FROM mtp_records m LEFT JOIN doctors d ON m.doctor_id=d.id
                                        WHERE m.id=?""", (rid,)).fetchone()
                    self.send_json(dict(row))

            elif path.startswith('/api/mtp/') and len(parts) == 4:
                rid = parts[3]
                if method == 'GET':
                    row = c.execute("""SELECT m.*, d.name as doctor_name
                                        FROM mtp_records m LEFT JOIN doctors d ON m.doctor_id=d.id
                                        WHERE m.id=?""", (rid,)).fetchone()
                    self.send_json(dict(row) if row else {'error':'Not found'}, 200 if row else 404)
                elif method == 'PUT':
                    b = self.read_body()
                    c.execute("""UPDATE mtp_records SET
                        entry_date=?, patient_name=?, age=?, husband_father_name=?, address=?, contact=?,
                        weeks=?, doctor_id=?, referred_by=?, indication=?, notes=?, extra_fields_json=?
                        WHERE id=?""",
                        (b['entry_date'], b['patient_name'], str(b.get('age','')),
                         b.get('husband_father_name',''), b.get('address',''), b.get('contact',''),
                         b.get('weeks',''), b.get('doctor_id',''), b.get('referred_by',''),
                         b.get('indication',''), b.get('notes',''),
                         json.dumps(b.get('extra_fields', {})), rid))
                    conn.commit()
                    self.send_json({'success': True})
                elif method == 'DELETE':
                    c.execute("DELETE FROM mtp_records WHERE id=?", (rid,))
                    conn.commit()
                    self.send_json({'success': True})

            # ── SONOGRAPHY (Form F) ──
            elif path == '/api/sonography':
                if method == 'GET':
                    q = parse_qs(parsed.query)
                    sql = """SELECT s.*, d.name as doctor_name
                              FROM sonography s LEFT JOIN doctors d ON s.doctor_id=d.id WHERE 1=1"""
                    args = []
                    if q.get('date_from'):
                        sql += " AND s.entry_date>=?"; args.append(q['date_from'][0])
                    if q.get('date_to'):
                        sql += " AND s.entry_date<=?"; args.append(q['date_to'][0])
                    if q.get('search'):
                        sql += " AND (s.patient_name LIKE ? OR s.entry_no LIKE ?)"
                        term = f"%{q['search'][0]}%"; args += [term, term]
                    sql += " ORDER BY s.entry_date DESC, s.created_at DESC"
                    rows = c.execute(sql, args).fetchall()
                    self.send_json([dict(r) for r in rows])

                elif method == 'POST':
                    b = self.read_body()
                    required = ['entry_date','patient_name']
                    if any(not b.get(k) for k in required):
                        return self.send_json({'error': 'Required fields missing'}, 400)
                    rid = str(uuid.uuid4())
                    seq = c.execute("SELECT COUNT(*) FROM sonography").fetchone()[0] + 1
                    entry_no = f"SONO-{datetime.now().year}-{seq:04d}"
                    c.execute("""INSERT INTO sonography
                        (id,entry_no,entry_date,patient_name,age,husband_father_name,address,contact,
                         living_sons,living_daughters,referred_by,lmp,indications,procedure_done,
                         doctor_id,procedure_date,result_notes,declaration_no_sex_disclosed,extra_fields_json)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (rid, entry_no, b['entry_date'], b['patient_name'], str(b.get('age','')),
                         b.get('husband_father_name',''), b.get('address',''), b.get('contact',''),
                         b.get('living_sons',''), b.get('living_daughters',''), b.get('referred_by',''),
                         b.get('lmp',''), json.dumps(b.get('indications',[])),
                         b.get('procedure_done','Ultrasound'), b.get('doctor_id',''),
                         b.get('procedure_date',''), b.get('result_notes',''),
                         1 if b.get('declaration_no_sex_disclosed', True) else 0,
                         json.dumps(b.get('extra_fields', {}))))
                    conn.commit()
                    row = c.execute("""SELECT s.*, d.name as doctor_name
                                        FROM sonography s LEFT JOIN doctors d ON s.doctor_id=d.id
                                        WHERE s.id=?""", (rid,)).fetchone()
                    self.send_json(dict(row))

            elif path.startswith('/api/sonography/') and len(parts) == 4:
                rid = parts[3]
                if method == 'GET':
                    row = c.execute("""SELECT s.*, d.name as doctor_name
                                        FROM sonography s LEFT JOIN doctors d ON s.doctor_id=d.id
                                        WHERE s.id=?""", (rid,)).fetchone()
                    self.send_json(dict(row) if row else {'error':'Not found'}, 200 if row else 404)
                elif method == 'DELETE':
                    c.execute("DELETE FROM sonography WHERE id=?", (rid,))
                    conn.commit()
                    self.send_json({'success': True})

            # ── STATS ──
            elif path == '/api/stats':
                total_out     = c.execute("SELECT COUNT(*) FROM outpatients").fetchone()[0]
                total_in      = c.execute("SELECT COUNT(*) FROM inpatients").fetchone()[0]
                admitted      = c.execute("SELECT COUNT(*) FROM inpatients WHERE status='admitted'").fetchone()[0]
                total_docs    = c.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
                self.send_json({'totalOutpatients': total_out, 'totalInpatients': total_in,
                                'currentlyAdmitted': admitted, 'totalDoctors': total_docs})
            else:
                self.send_json({'error': 'Not found'}, 404)

        except Exception as e:
            self.send_json({'error': str(e)}, 500)
        finally:
            conn.close()

    def serve_static(self):
        parsed = urlparse(self.path)
        req_path = parsed.path.lstrip('/')
        if not req_path or req_path == 'index.html':
            rel_file = 'index.html'
        else:
            rel_file = req_path

        filepath = os.path.abspath(os.path.join(FRONTEND_DIR, rel_file))

        if not filepath.startswith(FRONTEND_DIR) or not os.path.isfile(filepath):
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'404 Not Found')
            return

        content_type, _ = mimetypes.guess_type(filepath)
        if content_type is None:
            content_type = 'application/octet-stream'

        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Access-Control-Allow-Origin', '*')
            # Never let browsers cache the app shell — every laptop/PC must always
            # load whatever version currently sits on this server.
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/api'):
            self.route('GET')
        else:
            self.serve_static()

    def do_POST(self):   self.route('POST')
    def do_PUT(self):    self.route('PUT')
    def do_DELETE(self): self.route('DELETE')

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

if __name__ == '__main__':
    init_db()
    PORT = 5000
    local_ip = get_local_ip()
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print("===================================================")
    print("           MediCare HMS Server Running             ")
    print("===================================================")
    print(f" [OK] Local PC:      http://localhost:{PORT}")
    print(f" [OK] Mobile/Wi-Fi:  http://{local_ip}:{PORT}")
    print("===================================================")
    print(f" Give this address to the Doctor's laptop and any")
    print(f" other PC on the same Wi-Fi/LAN: http://{local_ip}:{PORT}")
    print(f" (Tip: reserve this IP for this PC in your router so")
    print(f"  it never changes.)")
    print("===================================================")
    print(" Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] Server stopped.")

