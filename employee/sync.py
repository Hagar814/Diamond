import frappe
import requests
from frappe.utils import getdate, nowdate
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

def sync_biotime_checkins():
    # settings = frappe.get_single("ZkTeco BioTime Settings")
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYzQ1MDJlZGUtZDJiOS0xMWYwLWI4ZDMtMGE1OGE5ZmVhYzAyIiwidXNlcm5hbWUiOiJNb2hhbWVkX0VsLURlZWJAYWxtYXNhLmNvbS5zYSIsImV4cCI6MTc2NjA1MzQ2NiwiZW1haWwiOiJNb2hhbWVkX0VsLURlZWJAYWxtYXNhLmNvbS5zYSIsIm9yaWdfaWF0IjoxNzY1NDQ4NjY2fQ.ac-n7kYzVTQmL_G9BicHBZmSdOghb_Ha2WzUfMcvhuY"

    url = "https://almasacompany.biotimecloud.com/iclock/api/transactions/"
    headers = {"Authorization": f"JWT {token}"}

    
    # if not settings.api_url or not settings.token:
    #     frappe.log_error("BioTime Settings are not configured", "BioTime Sync")
    #     return

    # url = f"{settings.api_url}/iclock/api/transactions/"
    
    # headers = {
    #     "Authorization": f"JWT {token}"
    # }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    checkins = response.json().get("data", [])

    for entry in checkins:
        emp_code = entry.get("emp_code")
        punch_time = entry.get("punch_time")

        try:
            employee_name = frappe.db.get_value(
                "Employee",
                {"attendance_device_id": emp_code},
                "name"
            )

            if not employee_name:
                frappe.log_error(
                    f"No Frappe Employee found for Attendance Device ID: {emp_code}",
                    "BioTime Sync Failure"
                )
                continue

            exists = frappe.db.exists(
                "Employee Checkin",
                {"employee": employee_name, "time": punch_time}
            )

            if not exists:
                doc = frappe.new_doc("Employee Checkin")
                doc.employee = employee_name
                doc.time = punch_time
                doc.device_id = entry.get("terminal_sn")

                if entry.get("punch_state") == "0":
                    doc.log_type = "IN"
                elif entry.get("punch_state") == "1":
                    doc.log_type = "OUT"
                else:
                    doc.log_type = ""  # optional: default to blank if unknown


                doc.insert(ignore_permissions=True)

        except Exception as e:
            frappe.log_error(
                f"Critical Insert Error for Employee {emp_code}: {str(e)}",
                "BioTime Sync Failure"
            )
            frappe.db.rollback()

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
                    "leave_type": "Annual Carry Forward",
                    "docstatus": ("!=", 2),
                },
                pluck="name",
                order_by="from_date desc",
                limit=1
            )

                if not existing:
                    frappe.log_error(
                        title=f"Annual Leave CF Skipped (No CF Allocation - {emp})",
                        message=f"{emp} has no Annual Carry Forward allocation"
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
