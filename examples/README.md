# Standardized Camply Background Search Scripts

This directory contains a standardized, heavily commented `camply` search template and a `screen` session manager for running multiple searches in the background:

- [`mueller_state_park.sh`](./mueller_state_park.sh) — Standardized search script configured for **Mueller State Park (`#50032`)** via the `ColoradoStateParks` provider (2-night weekend stay, 25-foot trailer, continuous polling with email notifications and offline state persistence).
- [`run_all_camply.sh`](./run_all_camply.sh) — Launcher script that discovers every `*.sh` search script in the folder and runs each one inside its own detached GNU `screen` session (`camply_<script_name>`) with logs written to `./logs/<script_name>.log`.

## Quick Start

1. **Copy the scripts to a dedicated working folder** (e.g. `~/camply`):
   ```bash
   mkdir -p ~/camply
   cp examples/*.sh ~/camply/
   chmod +x ~/camply/*.sh
   ```

2. **Configure `~/.camply` for Email Notifications** (optional, required when `NOTIFICATIONS` includes `"email"`):
   Create `~/.camply` (`chmod 600 ~/.camply`) with your SMTP settings. For Gmail, generate a 16-character [Google App Password](https://myaccount.google.com/apppasswords):
   ```ini
   EMAIL_TO_ADDRESS="recipient@example.com"
   EMAIL_USERNAME="sender@gmail.com"
   EMAIL_PASSWORD="your16charapppassword"
   EMAIL_FROM_ADDRESS="sender@gmail.com"
   EMAIL_SMTP_SERVER="smtp.gmail.com"
   EMAIL_SMTP_PORT=465
   EMAIL_SUBJECT_LINE="Camply Campsite Notification"
   ```

3. **Start, Check, or Stop All Searches**:
   ```bash
   # Start all *.sh search scripts in detached screen sessions
   ~/camply/run_all_camply.sh

   # Check status of running camply_* screen sessions
   ~/camply/run_all_camply.sh --status

   # Stop all running camply_* screen sessions
   ~/camply/run_all_camply.sh --stop
   ```

4. **Add More Campground Searches**:
   Look up any Colorado State Park campground ID:
   ```bash
   camply campgrounds --provider ColoradoStateParks --search "Cherry Creek"
   ```
   Then copy `mueller_state_park.sh` to a new file (e.g. `cherry_creek.sh`), update `CAMPGROUND_IDS`, `START_DATE`, `END_DATE`, or `EQUIPMENT_LENGTH`, and re-run `./run_all_camply.sh`.
