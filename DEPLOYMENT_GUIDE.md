# MediCare HMS — Deployment Guide
### Real-time sync between Receptionist's PC and Doctor's laptop, plus remote updates from the developer

This guide covers exactly what you asked for:
1. Receptionist enters a patient / bill → it shows up on the Doctor's laptop automatically (and vice versa).
2. You (the developer), from a different city, push a code change → it rolls out to both machines automatically.

---

## 1. How this works (read this first)

This app is **one backend server + a browser front end**. It is *not* two separate
copies of the app — it's **one shared database** that both machines look at.

```
                     Hospital Wi-Fi / LAN
                              │
      ┌───────────────────────┴────────────────────────┐
      │                                                  │
 SERVER PC (runs server.py + hospital.db)         DOCTOR'S LAPTOP
 e.g. Receptionist's PC                            (just a browser,
 http://192.168.1.50:5000  ◄────── same address ─── nothing installed)
      ▲
      │ also opens the same address in its own
      │ browser (http://localhost:5000)
 RECEPTIONIST'S PC BROWSER
```

- **One PC is the "Server PC."** It runs `server.py`, which stores everything in
  one file, `backend/hospital.db`, and also serves the app itself over the network.
- **Every other device** (doctor's laptop, and the receptionist's own browser)
  just opens that PC's address in Chrome/Edge — e.g. `http://192.168.1.50:5000`.
  No installation needed on those devices at all.
- Because everyone is reading/writing the *same* database through the *same*
  server, a bill or patient entry made by the receptionist is visible to the
  doctor the moment it's saved — the app now also **auto-refreshes every few
  seconds** and **auto-reloads itself when you push an update**, so nobody has
  to manually hit refresh.

**Decide now: which PC is the "Server PC"?**
Recommendation: the **Receptionist's PC**, since it's on all day and it's where
most data entry happens. The doctor's laptop then only ever needs a browser
bookmark. (If the doctor's laptop leaves the building, it loses access —
that's expected for a LAN-only setup; see §7 if you need off-site access later.)

---

## 2. One-time setup — GitHub repo (so you can push updates)

You'll keep the project in a **private GitHub repository**. This is what lets
you edit code in your city and have it reach the hospital PCs automatically.

1. Create a free GitHub account if you don't have one, and create a new
   **private** repository, e.g. `hospital-mgmt`.
2. On your own machine, inside this project folder:
   ```bash
   git init
   git add .
   git commit -m "Initial version"
   git branch -M main
   git remote add origin https://github.com/<your-username>/hospital-mgmt.git
   git push -u origin main
   ```
3. From now on, whenever you make changes:
   ```bash
   git add .
   git commit -m "Describe what changed"
   git push
   ```
   That single `git push` is the only thing you ever need to do to update
   both hospital PCs (see §5 — the auto-update watchdog does the rest).

> If you'd rather not use GitHub, GitLab or Bitbucket work identically —
> everything below only relies on plain `git`.

---

## 3. Setting up the SERVER PC (recommended: Receptionist's PC)

### 3.1 Install prerequisites (one time)
1. **Python 3.8+** — [python.org/downloads](https://www.python.org/downloads/).
   During install, tick **"Add Python to PATH"**.
2. **Git for Windows** — [git-scm.com/download/win](https://git-scm.com/download/win).
   Default options are fine.

### 3.2 Get the project onto this PC
Open Command Prompt and run (replace with your repo URL and a real folder):
```
cd C:\
git clone https://github.com/<your-username>/hospital-mgmt.git HospitalApp
```
> Important: use `git clone`, **not** "unzip the file I sent you". Only a
> real git clone can auto-update itself later.

If the repo is **private**, Windows will ask you to sign in to GitHub the
first time — sign in with the account that owns the repo (or one you've
added as a collaborator).

### 3.3 Give this PC a fixed local IP address
Right now the PC's local IP (e.g. `192.168.1.50`) is normally assigned by
your Wi-Fi router and could change after a reboot — that would break the
doctor's bookmark. Fix it once:
- Open your router's admin page (commonly `192.168.1.1` or `192.168.0.1`)
  → find **DHCP reservation / Static Lease** → reserve the current IP for
  this PC's MAC address.
- (Alternative: set a static IP directly in Windows network settings.)

Write this IP down — you'll use it everywhere below. This guide will call
it `<SERVER-IP>`.

### 3.4 Open the firewall for port 5000 (one time)
Run Command Prompt **as Administrator**:
```
netsh advfirewall firewall add rule name="MediCare HMS" dir=in action=allow protocol=TCP localport=5000
```

### 3.5 Start the app with auto-update
Inside `C:\HospitalApp`, double-click:
```
Start_With_AutoUpdate.bat
```
Leave this window open — it's both the database server **and** the
background process that checks GitHub for your updates every couple of
minutes. You should see it print `MediCare HMS Server Running` and the
address for other devices.

### 3.6 Make it start automatically when the PC turns on (recommended)
So the receptionist never has to remember to start anything:
1. Press `Win + R`, type `shell:startup`, press Enter.
2. Right-click `Start_With_AutoUpdate.bat` in `C:\HospitalApp` → **Copy**.
3. Right-click inside the Startup folder → **Paste shortcut**.

Now the server starts automatically every time this PC is turned on.

---

## 4. Setting up the DOCTOR'S LAPTOP (and receptionist's own browser)

Nothing to install. Just:
1. Make sure the laptop is on the **same Wi-Fi/LAN** as the Server PC.
2. Open Chrome or Edge and go to: `http://<SERVER-IP>:5000`
   (e.g. `http://192.168.1.50:5000`)
3. Log in with the doctor account.
4. Bookmark it, or create a desktop shortcut:
   - Right-click the desktop → **New → Shortcut**
   - Location: `http://<SERVER-IP>:5000`
   - Name it "MediCare HMS"

That's the entire doctor's-laptop setup. Every time you push an update,
this same browser tab will pick it up automatically (see §6) — there is
nothing to reinstall on the laptop, ever.

---

## 5. How the automatic sync works day-to-day

- **New patient/bill entries:** the app now silently re-checks the screen
  you're looking at every ~6 seconds. If the receptionist adds a patient
  or saves a bill, the doctor's dashboard/list updates on its own within a
  few seconds — no refresh needed. (It pauses this quiet refresh while
  someone has an edit window open, so it never overwrites what you're typing.)
- **Code updates from you:** `auto_update.py` on the Server PC checks
  GitHub roughly every 2 minutes. If it finds new commits, it pulls them
  and restarts the server automatically. Every open browser (doctor's
  laptop included) notices the app version changed and quietly reloads
  itself within about a minute — showing your update with zero action
  from hospital staff.
- Everything the watchdog does is logged to `auto_update.log` in the
  project folder, in case you ever need to ask the hospital to send it to
  you for troubleshooting.

---

## 6. Making a change and rolling it out (your workflow, from any city)

1. Edit the code on your machine as usual.
2. Test it locally (`python backend/server.py`).
3. Commit and push:
   ```bash
   git add .
   git commit -m "What changed"
   git push
   ```
4. Within ~2 minutes, the Server PC pulls it and restarts; within ~1 more
   minute, every open browser reloads with the new version automatically.

No remote access to the hospital PCs is required for a normal update.

---

## 7. If you need to fix something urgently or the watchdog itself breaks

The auto-update watchdog only works if git/Python/internet are all fine on
the Server PC. For the rare cases where something's actually broken there
(not just a code bug), you'll want **remote-desktop access** as a fallback:
- Install **AnyDesk** or **TeamViewer** on the Server PC and set up
  "unattended access" once, so you can log in yourself anytime without
  needing hospital staff to click "accept."
- This is only a safety net — it's not needed for routine updates.

---

## 8. Backups

All data lives in one file: `backend\hospital.db` on the Server PC.
- Set up a daily copy of this file to a USB drive, Google Drive, or OneDrive.
- Because `hospital.db` is intentionally **not** tracked in git (see
  `.gitignore`), your `git pull` updates will never overwrite or touch the
  hospital's real data — only application code changes.

---

## 9. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Doctor's laptop can't reach the app | Not on the same Wi-Fi as the Server PC, or `<SERVER-IP>` changed (see §3.3), or the firewall rule (§3.4) is missing. |
| Changes don't show up on the doctor's screen | Confirm both devices are pointed at the *same* `<SERVER-IP>` — not `localhost` on two different machines. |
| Your update isn't rolling out | Check `auto_update.log` on the Server PC — likely no internet, or the repo needs a fresh `git pull` login/credential. |
| "This folder is not a git repository" | The project was unzipped instead of `git clone`d on the Server PC — redo §3.2. |
| Server window closed by accident | Just re-double-click `Start_With_AutoUpdate.bat` (or it restarts on its own at next login if you did §3.6). |
