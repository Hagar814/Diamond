import frappe
import requests
from datetime import datetime, time
from frappe.utils import getdate, nowdate, get_datetime, convert_utc_to_system_timezone, now_datetime
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
import math



@frappe.whitelist()
def sync_zkteco_token():
    try:
        url = "http://biotime.almasa.com.sa/jwt-api-token-auth/"
        payload = {
            "username": "Admin",
            "password": "Almasa2026"
        }

        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()

        data = response.json()
        token = data.get("token")

        if not token:
            frappe.throw("Token not found in response")

        # Save to Single DocType
        doc = frappe.get_single("Zkteco Setting")
        doc.token = token
        doc.last_sync = now_datetime()
        doc.save(ignore_permissions=True)

        frappe.db.commit()

        return "Token synced successfully"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Zkteco Token Sync Failed")
        raise



# ------------------------------------------------------------
# Main Sync Function
# ------------------------------------------------------------

def sync_biotime_checkins():
    frappe.log_error(
        "BioTime sync started",
        "BioTime Sync Debug"
    )

    # ✅ Get token from Single DocType
    settings = frappe.get_single("Zkteco Setting")

    # If field type is Password, use get_password()
    token = settings.get_password("token")

    if not token:
        frappe.log_error("Token is empty", "BioTime Sync Error")
        return    
    headers = {"Authorization": f"JWT {token}"}

    base_url = "http://biotime.almasa.com.sa/iclock/api/transactions/"
    total_records = 0
    page_size = 10
    max_pages = 10

    # ------------------------------------------------
    # Step 1: Get total count
    # ------------------------------------------------
    response = requests.get(base_url, headers=headers, timeout=30)
    response.raise_for_status()
    total_count = response.json().get("count", 0)
    total_pages = math.ceil(total_count / page_size)

    # ------------------------------------------------
    # Step 2: Calculate starting page
    # ------------------------------------------------
    start_page = max(total_pages - max_pages + 1, 1)
    current_page = start_page

    # ------------------------------------------------
    # Step 3: Loop pages
    # ------------------------------------------------
    while current_page <= total_pages:
        url = f"{base_url}?page={current_page}"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        checkins = data.get("data", [])
        total_records += len(checkins)

        frappe.log_error(
            f"BioTime sync page fetched. "
            f"Records: {len(checkins)}, "
            f"Total: {total_records}, "
            f"Page: {current_page}",
            "BioTime Sync Debug"
        )

        for entry in checkins:
            emp_code = entry.get("emp_code")
            punch_time_str = entry.get("punch_time")

            if not emp_code or not punch_time_str:
                continue

            try:
                punch_time = frappe.utils.get_datetime(punch_time_str).replace(
                    tzinfo=None,
                    microsecond=0
                )

                # ------------------------------------------------
                # Find employee
                # ------------------------------------------------
                employee_name = frappe.db.get_value(
                    "Employee",
                    {"attendance_device_id": emp_code},
                    "name"
                )

                if not employee_name:
                    frappe.log_error(
                        f"No employee found for device ID {emp_code}",
                        "BioTime Sync Missing Employee"
                    )
                    continue

                # ------------------------------------------------
                # Prevent exact duplicates
                # ------------------------------------------------
                if frappe.db.exists(
                    "Employee Checkin",
                    {"employee": employee_name, "time": punch_time}
                ):
                    continue

                # ------------------------------------------------
                # Create Employee Checkin (NO manual shift)
                # ------------------------------------------------
                doc = frappe.new_doc("Employee Checkin")
                doc.employee = employee_name
                doc.time = punch_time
                doc.device_id = entry.get("terminal_sn")
                doc.log_type = "IN" if entry.get("punch_state") == "0" else "OUT"

                # 🔥 Let HRMS auto-fetch shift
                doc.fetch_shift()

                doc.flags.ignore_validate = True
                doc.insert(ignore_permissions=True)

            except Exception as e:
                frappe.log_error(
                    f"""
Employee Code : {emp_code}
Punch Time    : {punch_time_str}
Error         : {str(e)}
                    """,
                    "BioTime Sync Critical Error"
                )
                frappe.db.rollback()

        frappe.db.commit()
        current_page += 1

    frappe.log_error(
        f"BioTime sync completed successfully. "
        f"Total records processed: {total_records}",
        "BioTime Sync Debug"
    )

    frappe.db.commit()





def leave_cf_carry_forward():
    today = getdate(nowdate())

    frappe.log_error(
        title="Annual Leave CF Job Started",
        message=f"Carry Forward job started on {today}"
    )

    # TEMP: change to 31 later
    if not (today.month == 12 and today.day == 31):
        return

    try:
        employees = frappe.get_all(
            "Employee",
            filters={"status": "Active"},
            pluck="name"
        )

        for emp in employees:
            try:
                from_date = today.replace(year=today.year + 1, month=1, day=1)
                to_date = today.replace(year=today.year + 1, month=12, day=31)

                # 🔴 FIRST: Check if CF allocation exists
                existing = frappe.get_all(
                "Leave Allocation",
                filters={
                    "employee": emp,
                    "leave_type": "Accrual",
                    "docstatus": ("!=", 2),
                },
                pluck="name",
                order_by="from_date desc",
                limit=1
            )

                if not existing:
                    frappe.log_error(
                        title=f"Annual Leave CF Skipped (No CF Allocation - {emp})",
                        message=f"{emp} has no Accrual allocation"
                    )
                    continue

                # ✅ CF exists → now calculate balance
                balance = (
                    get_leave_balance_on(
                        employee=emp,
                        leave_type="Annual leave (less than 5 years)",
                        date=today
                    ) or 0
                ) + (
                    get_leave_balance_on(
                        employee=emp,
                        leave_type="Annual Leave (more than 5 years)",
                        date=today
                    ) or 0
                )

                if balance <= 0:
                    frappe.log_error(
                        title=f"Annual Leave CF Skipped (No Balance - {emp})",
                        message=f"{emp} has no remaining Annual Leave balance"
                    )
                    continue

                # 🔁 Override existing CF allocation
                doc = frappe.get_doc("Leave Allocation", existing[0])
                previous_total = doc.total_leaves_allocated or 0

                doc.new_leaves_allocated = balance
                doc.total_leaves_allocated = balance
                doc.save()

                frappe.log_error(
                    title="Annual Leave CF Updated",
                    message=(
                        f"{emp} → CF overridden "
                        f"(old: {previous_total}, new: {balance})"
                    )
                )

            except Exception:
                frappe.log_error(
                    title=f"Annual Leave CF Error (Employee {emp})",
                    message=frappe.get_traceback()
                )

    except Exception:
        frappe.log_error(
            title="Annual Leave CF Job Failed",
            message=frappe.get_traceback()
        )

def send_leads_notification_if_saturday():
    # Python weekday(): Monday=0 ... Sunday=6
    today = datetime.today()

    if today.weekday() != 5:  # 5 = Saturday
        return

    leads = frappe.get_all(
        "Lead",
        filters={"status": "Lead"},
        fields=["name", "lead_name"]
    )

    if not leads:
        return

    base_url = frappe.utils.get_url()

    rows = ""
    for lead in leads:
        lead_url = f"{base_url}/app/lead/{lead.name}"
        rows += f"""
            <tr>
                <td>{lead.lead_name or lead.name}</td>
                <td><a href="{lead_url}">Open Lead</a></td>
            </tr>
        """

    message = f"""
        <p>Hello,</p>
        <p>Here is the list of all Leads with status <b>Open</b>:</p>

        <table border="1" cellpadding="6" cellspacing="0">
            <tr>
                <th>Lead Name</th>
                <th>Link</th>
            </tr>
            {rows}
        </table>

        <p>Total Leads: <b>{len(leads)}</b></p>
    """

    frappe.sendmail(
        recipients = ["mirna_hany@almasa.com.sa","mariam_ezzat@almasa.com.sa"],
        subject="Saturday Leads Summary",
        message=message
    )
