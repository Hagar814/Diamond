import frappe
import requests

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
