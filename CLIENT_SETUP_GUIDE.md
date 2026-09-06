# MediCare HMS — Client Installation & Setup Guide

Welcome to **MediCare HMS** (Hospital Management System). This guide will help you setup, run, and access the application on your computer and mobile devices.

---

## 📋 System Requirements

- **Computer OS**: Windows 10/11 (or macOS / Linux)
- **Software Needed**: **Python 3.8 or higher** (Download from [python.org](https://www.python.org/downloads/))
  > ⚠️ **Important during Python Installation**: Be sure to tick the checkbox **"Add Python to PATH"** before clicking Install.

---

## 🚀 Step-by-Step Installation on Client Computer

1. **Extract the ZIP File**:
   - Right-click `hospital-mgmt-dist.zip` and select **Extract All...**
   - Extract it to a folder of your choice, e.g. `C:\HospitalApp\hospital-mgmt`.

2. **Start the Hospital Management System**:
   - Double-click **`Run_MediCare_HMS.bat`** in the extracted folder.
   - The launcher will start the backend database server and automatically open the application in your browser (Google Chrome or Microsoft Edge recommended).

3. **Desktop Shortcut (Optional)**:
   - Right-click `Run_MediCare_HMS.bat` → **Send to** → **Desktop (create shortcut)**.
   - You can rename this shortcut to **MediCare HMS**. Double-clicking this shortcut every day will start the server and open the app.

---

## 📱 How to Access from Mobile Phones & Tablets (Local Wi-Fi)

You can view, enter patient records, and access the software directly from any **Android phone, iPhone, iPad, or tablet** connected to the hospital Wi-Fi!

1. Make sure your mobile device is connected to the **same Wi-Fi network** as the main hospital computer.
2. When you double-click `Run_MediCare_HMS.bat`, the server command window displays a network address under **`Mobile/Wi-Fi`**, for example:
   ```
   http://192.168.1.15:5000
   ```
3. Open **Chrome** or **Safari** on your mobile phone or tablet, type that exact address into the browser address bar, and press Enter.
4. The mobile-optimized hospital management system will open instantly!

---

## 🔑 Default Login Credentials

| Account Role | Username | Password | Access Rights |
| :--- | :--- | :--- | :--- |
| **Doctor / Admin** | `doctor` | `doctor123` | Full access (Dashboard, Records, Billing, Sonography, Doctors, Settings & Password Manager) |
| **Operator** | `operator` | `operator123` | Patient Records Registration, Billing & Form F Sonography |
| **Receptionist** | `receptionist` | `receptionist123` | Patient Records Registration, Billing & Form F Sonography |

*Note: The Doctor account can change passwords for any account under the **Settings → User Account & Security** section.*

---

## 💾 Data Backup & Safety

All your patient records, bills, doctor lists, and Form F sonography data are safely stored in one single file:
- File location: `backend\hospital.db`

### Recommended Backup Strategy:
- Periodically copy `backend\hospital.db` to an external USB flash drive or Google Drive / OneDrive to keep your hospital data safe.

---

## 📞 Support & Troubleshooting

- **Server Window Closed**: If the app says "Connection Error", make sure the `MediCare HMS Server` command prompt window is open in the background. If closed, re-run `Run_MediCare_HMS.bat`.
- **Port Conflict**: If port 5000 is occupied by another application, close that application or restart the computer.
