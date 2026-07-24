# MediCare HMS — Hospital Management System

A full-stack Hospital Management System for Windows (also runs on macOS/Linux) covering
patient records, OPD/IPD billing with printable receipts, and PC&PNDT Form F sonography
record-keeping — backed by a proper relational (SQLite) database.

## ✅ No External Dependencies Required
The backend uses only Python's standard library (`http.server` + `sqlite3`). No `pip install`
needed. The frontend is a single HTML file with vanilla JavaScript — no npm, no build step.

## What's inside

- **Dashboard** — live stats: outpatient visits, admissions, currently admitted, doctors
- **Patient Records**
  - **Outpatients** — register/edit OPD visits with symptoms, diagnosis, prescription, follow-up
  - **Inpatients** — admit/edit IPD patients with ward, bed, admission/discharge tracking
- **Billing** (new)
  - Generate **OPD** or **IPD** bills that match a printed cash-memo layout: hospital
    name/logo header, Bill No., date, patient details, Consultant Doctor (dropdown, always
    in sync with the Doctors list), and an itemized charges table (Consultation, Bed,
    Nursing, OT, Surgeon, Assistant, Anesthetic, Visit, Pathology, X-Ray/ECG/USG,
    Monitor/O2, Dressing, Medicine, Service, Registration — all editable, and you can add
    custom line items too).
  - **Payment**: Cash or Paid Online. Choosing "Paid Online" requires a manually entered
    **UTR / transaction code**, which is saved with the bill so payment can be verified later.
  - Bill numbers auto-increment per type (e.g. `OPD-2026-0001`, `IPD-2026-0001`).
  - **Print** — "Save & Print Bill" opens a print preview styled like the receipt and sends
    it straight to your printer (`window.print()` — works with any Windows printer driver).
  - **Bill Records** — search/filter bills by patient name, bill number, type (OPD/IPD),
    doctor, and date range; reprint or delete any past bill.
- **Sonography — Form F** (new)
  - Data-entry form modeled on the PC&PNDT Act "Form F" (patient details, referring doctor,
    LMP, the standard indications checklist for ultrasound during pregnancy, procedure
    performed, doctor performing it, result, and the non-disclosure declaration).
  - Printable in the same hospital-branded layout, and searchable by patient name/date.
- **Doctors** — add doctors with specialization/contact; every new doctor immediately shows
  up in **every** Consultant Doctor dropdown across Outpatients, Inpatients, Billing, and
  Sonography — no page reload needed.
- **Settings** (new) — set your real hospital name, tagline, address, phone, registration
  number, and upload a logo image. These appear on every printed bill and Form F, and in the
  app header. (There's no bundled hospital logo file, so upload the hospital's actual logo
  image here once — the app immediately reuses it everywhere.)
- **RDBMS-backed** — SQLite with foreign keys and indexes on the columns you'll search by
  (date, doctor, patient name, bill type), so records for OPD, IPD, billing, and sonography
  are stored in clean, linked tables with no duplication or overlap.

## Tech Stack

| Layer    | Technology                       |
|----------|-----------------------------------|
| Backend  | Python 3.8+ (standard library)   |
| Database | SQLite3 (built-in, relational)   |
| Frontend | HTML5 / CSS3 / Vanilla JS        |

## 🚀 Setup & Run (Windows)

1. Install **Python 3.8+** from [python.org](https://www.python.org/downloads/) if you don't
   already have it. During install, tick **"Add Python to PATH"**.
2. Unzip this project anywhere, e.g. `C:\HospitalApp\hospital-mgmt`.
3. Start the backend:
   - Double-click `backend\run_server.bat`, **or**
   - Open Command Prompt in the `backend` folder and run:
     ```
     python server.py
     ```
   You should see: `✅ MediCare HMS Server running at http://localhost:5000`. Leave this
   window open — it's your database server.
4. Open `frontend\index.html` in your browser (Chrome/Edge recommended) — double-click it,
   or right-click → Open with → your browser.
5. That's the whole app. To make it easier to launch every day, right-click
   `frontend\index.html` and "Send to → Desktop (create shortcut)", and do the same for
   `backend\run_server.bat`.

> The database file `backend\hospital.db` is created automatically on first run, seeded with
> 5 sample doctors and default settings ("MediCare HMS"). Go to **Settings** in the app and
> replace this with your real hospital name, address, phone, registration number and logo —
> everything you enter is immediately used on printed bills and Form F.

### Setup on macOS / Linux
Same steps — just run `python3 server.py` instead of the `.bat` file, and open
`frontend/index.html` in a browser.

### Running the frontend from a local web server (optional)
Opening `index.html` directly (`file://...`) works fine in Chrome/Edge. If your browser
blocks anything over `file://`, serve the frontend folder instead:
```bash
cd frontend
python3 -m http.server 8080
```
then visit `http://localhost:8080`.

## Project Structure

```
hospital-mgmt/
├── backend/
│   ├── server.py          ← Python HTTP + SQLite server (zero dependencies)
│   ├── run_server.bat     ← double-click to start the server on Windows
│   └── hospital.db        ← auto-created SQLite database (created on first run)
└── frontend/
    └── index.html         ← full single-page application (Dashboard, Billing,
                              Sonography, Doctors, Settings)
```

## Printing bills / Form F
Click **Print** on any generated bill or Form F entry — a print preview opens showing only
the receipt (no app chrome). Click the **Print** button in that dialog (or use your browser's
Ctrl+P) and choose your physical printer. The on-screen preview is exactly what prints.

## Backing up your data
All patient, billing, and sonography records live in one file: `backend\hospital.db`. Copy
that file elsewhere regularly (or set up scheduled backups) to keep a safe copy of your data.

## API Endpoints

| Method | Endpoint                | Description                                   |
|--------|--------------------------|------------------------------------------------|
| GET    | /api/doctors             | List all doctors                               |
| POST   | /api/doctors             | Add a doctor                                   |
| DELETE | /api/doctors/:id         | Remove a doctor                                |
| GET    | /api/outpatients         | List all outpatient visits                     |
| POST   | /api/outpatients         | Register a visit                               |
| PUT    | /api/outpatients/:id     | Update a visit                                 |
| DELETE | /api/outpatients/:id     | Delete a visit                                 |
| GET    | /api/inpatients          | List all inpatients                            |
| POST   | /api/inpatients          | Admit a patient                                |
| PUT    | /api/inpatients/:id      | Update admission                               |
| DELETE | /api/inpatients/:id      | Delete admission                               |
| GET    | /api/settings            | Get hospital identity (name/logo/address/etc.) |
| PUT    | /api/settings            | Update hospital identity                       |
| GET    | /api/bill-templates      | Default OPD/IPD charge line items              |
| GET    | /api/bills               | List bills (filters: type, doctor_id, date_from, date_to, search) |
| POST   | /api/bills               | Create a bill (auto-generates bill_no)         |
| GET    | /api/bills/:id           | Get one bill                                   |
| DELETE | /api/bills/:id           | Delete a bill                                  |
| GET    | /api/sonography          | List Form F entries (filters: date_from, date_to, search) |
| POST   | /api/sonography          | Create a Form F entry (auto-generates entry_no)|
| GET    | /api/sonography/:id      | Get one Form F entry                           |
| DELETE | /api/sonography/:id      | Delete a Form F entry                          |
| GET    | /api/stats               | Dashboard statistics                           |
