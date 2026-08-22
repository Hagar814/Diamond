# Employee (Diamond)

A custom [Frappe](https://frappeframework.com/) app that extends **Frappe HR (HRMS)** with additional HR/payroll functionality: overtime tracking, ZKTeco/BioTime biometric attendance sync, payroll & salary slip customizations, job orders, and reporting.

> Internal app name: `employee` · Repository name: `Diamond` · Publisher: Shiftits

## Features

- **Overtime** — track per-employee overtime hours and computed overtime pay (`Overtime` doctype), linked to `Payroll Entry`.
- **ZKTeco / BioTime integration** — syncs biometric check-in/check-out data from a BioTime device server into Frappe `Employee Checkin` records, and keeps the device auth token refreshed (`Zkteco Setting` doctype, `employee/sync.py`).
- **Payroll customizations** — client-side scripts for `Payroll Entry` and `Salary Slip` (half-day detection, late-entry handling).
- **Job Order** — a sales-order-style doctype for tracking customer orders (customer, item, delivery date, pricing, terms).
- **Attachments** — a lightweight doctype for storing named file attachments against other records.
- **Project report** — a custom report under the Employee module.
- **Scheduled jobs** — automatic BioTime check-in sync, leave carry-forward, ZKTeco token refresh, and late-entry counter resets (see [Scheduled Jobs](#scheduled-jobs)).

## Prerequisites

- [Frappe Bench](https://docs.frappe.io/framework/user/en/installation) set up locally
- A Frappe site running **Frappe Framework v15**
- [**Frappe HR (HRMS)**](https://github.com/frappe/hrms) installed on the site — this app extends HRMS doctypes (`Payroll Entry`, `Salary Slip`, `Employee Checkin`, leave application balances) and will not install without it
- Python ≥ 3.10
- Network access to a BioTime/ZKTeco device server, if you intend to use the biometric sync feature

## Installation

```bash
# From your bench directory
bench get-app employee https://github.com/Hagar814/Diamond.git
bench --site <your-site-name> install-app employee
bench --site <your-site-name> migrate
```

Then build assets and restart:

```bash
bench build --app employee
bench restart
```

## Configuration

### ZKTeco / BioTime sync

Attendance sync is driven by the single doctype **Zkteco Setting**, which stores the auth `token` and `last_sync` timestamp used to talk to the BioTime server.

1. Open **Zkteco Setting** in the desk.
2. Run the `sync_zkteco_token` scheduled job once (or trigger it manually) to populate the token.
3. `sync_biotime_checkins` (run every 4 minutes by default) will then pull check-ins and create `Employee Checkin` records.

⚠️ **Action needed before deploying this anywhere:** `employee/sync.py` currently hardcodes the BioTime server URL and a username/password directly in source. Move these to `Zkteco Setting` fields or `site_config.json` (accessed via `frappe.conf`) and use `get_password()` for the secret, so credentials aren't committed to git. Rotate the existing credential once it's been moved, since it's currently public in the repository history.

### Payroll / Salary customizations

Client scripts are auto-loaded via `hooks.py`:

| Doctype | Script |
|---|---|
| Payroll Entry | `public/js/salary.js` |
| Overtime | `public/js/overtime.js` |
| Zkteco Setting | `public/js/biotime.js` |
| Salary Slip | `public/js/salarySlip.js` |

## Scheduled Jobs

Defined in `hooks.py`:

| Frequency | Job | Purpose |
|---|---|---|
| Every 4 min (`all`) | `employee.sync.sync_biotime_checkins` | Pull new check-ins from BioTime |
| Daily | `employee.sync.leave_cf_carry_forward` | Carry forward unused leave balances |
| Daily | `employee.sync.sync_zkteco_token` | Refresh the BioTime auth token |
| Daily | `employee.api.reset_late_entry_counter` | Reset the per-employee late-arrival counter |

## App Structure

```
employee/
├── api.py                  # Whitelisted server methods (late-minute calc, half-day logic, etc.)
├── sync.py                 # BioTime/ZKTeco sync + leave carry-forward
├── hooks.py                # App config: scheduler events, doctype JS
├── patches.txt             # DB migration patches (pre/post model sync)
├── config/                 # App module config
├── templates/pages/         # Web page templates
├── public/js/              # Client scripts for HRMS doctypes
└── employee/
    ├── doctype/
    │   ├── overtime/        # Overtime tracking, linked to Payroll Entry
    │   ├── zkteco_setting/  # Single doctype: BioTime token + last sync time
    │   ├── job_order/       # Sales-order-style customer order tracking
    │   └── attachments/     # Generic named file attachments
    └── report/
        └── project/         # Custom project report
```

## Testing

CI runs on GitHub Actions (`.github/workflows/ci.yml`) against MariaDB 10.6 + Redis, using `bench run-tests`. To run locally:

```bash
bench --site <your-site-name> set-config allow_tests true
bench --site <your-site-name> run-tests --app employee
```

Each doctype ships a corresponding `test_*.py` file (e.g. `test_overtime.py`, `test_job_order.py`, `test_zkteco_setting.py`) — extend these as you add functionality.

## Contributing

1. Fork the repo and create a feature branch.
2. Make your changes and add/update tests under the relevant `doctype/test_*.py`.
3. Open a pull request against `develop` — CI must pass before merge.

## Security Notes

- Do not commit device credentials, API tokens, or passwords in source. Use `site_config.json` + `frappe.conf.get(...)`, or store secrets on the relevant doctype and read them with `get_password()`.
- `frappe.log_error` calls in `sync.py` write debug-level logs on every sync run ("BioTime sync started") — consider gating these behind a debug flag to avoid flooding the Error Log in production.

## License

MIT — see [license.txt](license.txt).
