#!/usr/bin/env python3
"""
MediCare HMS — Auto-Update Watchdog
------------------------------------
Runs on the ONE PC that acts as the server (the machine both the doctor's
laptop and the receptionist's PC connect to over Wi-Fi/LAN).

What it does, forever, in a loop:
  1. Checks the GitHub repo for new commits from the developer.
  2. If there are new commits: pulls them, then restarts the backend server
     so the change takes effect immediately.
  3. If the backend server crashes for any other reason, restarts it too.
  4. Writes everything it does to auto_update.log so the developer can ask
     for that file if something looks wrong.

This is what makes "the developer changes code in another city -> it shows
up on the hospital PCs automatically" work: the developer just needs to
`git push`. No one at the hospital has to do anything.

Requirements on THIS machine only (the server PC):
  - Python 3.8+  (already required by the app)
  - Git for Windows, and this folder must be a `git clone` of the project's
    GitHub repository (see DEPLOYMENT_GUIDE.md).
  - Internet access (only needed to check for updates — the app itself
    works fine offline on the local Wi-Fi).

Usage: double-click Start_With_AutoUpdate.bat (Windows) — it just runs:
    python auto_update.py
"""

import subprocess
import sys
import os
import time
import datetime

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(REPO_DIR, 'backend', 'server.py')
LOG_PATH = os.path.join(REPO_DIR, 'auto_update.log')

CHECK_INTERVAL_SECONDS = 120   # how often to check GitHub for new commits
CRASH_RECHECK_SECONDS = 5      # how often to see if the server process died


def log(msg):
    line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass  # never let logging itself crash the watchdog


def run_git(*args):
    """Run a git command in the repo dir. Returns (success, output)."""
    try:
        result = subprocess.run(
            ['git', *args],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (result.stdout or '') + (result.stderr or '')
        return result.returncode == 0, output.strip()
    except FileNotFoundError:
        return False, 'Git is not installed or not on PATH.'
    except Exception as e:
        return False, str(e)


def has_new_commits():
    """Fetch from origin and check if the local branch is behind it."""
    ok, _ = run_git('fetch', '--quiet')
    if not ok:
        return False  # e.g. no internet right now — just skip this cycle

    ok, local_head = run_git('rev-parse', 'HEAD')
    if not ok:
        return False
    ok, remote_head = run_git('rev-parse', '@{u}')
    if not ok:
        return False
    return local_head.strip() != remote_head.strip()


def pull_latest():
    ok, output = run_git('pull', '--ff-only')
    log(f"git pull -> {'OK' if ok else 'FAILED'}: {output}")
    return ok


def start_server():
    log('Starting backend server...')
    return subprocess.Popen(
        [sys.executable, SERVER_SCRIPT],
        cwd=os.path.join(REPO_DIR, 'backend'),
    )


def stop_server(proc):
    if proc and proc.poll() is None:
        log('Stopping backend server for update...')
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    log('=== MediCare HMS auto-update watchdog started ===')
    ok, _ = run_git('rev-parse', '--is-inside-work-tree')
    if not ok:
        log('ERROR: This folder is not a git repository. '
            'See DEPLOYMENT_GUIDE.md — clone the project with `git clone` '
            'instead of unzipping it, then run this again.')
        log('Starting the server anyway, without auto-update.')

    if ok:
        pull_latest()

    server_proc = start_server()
    last_check = time.time()

    try:
        while True:
            time.sleep(CRASH_RECHECK_SECONDS)

            # 1) Did the server crash on its own? Bring it back.
            if server_proc.poll() is not None:
                log('Backend server stopped unexpectedly — restarting it.')
                server_proc = start_server()

            # 2) Time to check GitHub for a new version?
            if ok and (time.time() - last_check) >= CHECK_INTERVAL_SECONDS:
                last_check = time.time()
                if has_new_commits():
                    log('New update found on GitHub — applying it now.')
                    stop_server(server_proc)
                    if pull_latest():
                        log('Update applied.')
                    else:
                        log('Update failed to apply — restarting old version.')
                    server_proc = start_server()
    except KeyboardInterrupt:
        log('Watchdog stopped by user (Ctrl+C).')
        stop_server(server_proc)


if __name__ == '__main__':
    main()
