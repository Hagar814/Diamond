# import frappe
# from datetime import datetime, timedelta


import frappe
from frappe.utils import getdate, add_days, now_datetime, get_datetime

@frappe.whitelist()
def validate_payroll_half_day(name):
    payroll = frappe.get_doc("Payroll Entry", name)
    start = getdate(payroll.start_date)
    end = getdate(payroll.end_date)

    msg = []

    for row in payroll.employees:
        emp_id = row.employee
        current = start

        while current <= end:
            # Define exact datetime range for the day
            day_start = get_datetime(str(current) + " 00:00:00")
            day_end = get_datetime(str(current) + " 23:59:59")

            # Count only IN logs for that day
            checkins = frappe.get_all(
                "Employee Checkin",
                filters={
                    "employee": emp_id,
                    "log_type": "IN",
                    "time": ["between", [day_start, day_end]]
                },
                fields=["name"]
            )

            in_count = len(checkins)

            if in_count == 1:
                # Get attendance for that day
                attendance = frappe.get_all(
                    "Attendance",
                    filters={
                        "employee": emp_id,
                        "attendance_date": current,
                        "docstatus": 1
                    },
                    fields=["name"]
                )

                if attendance:
                    att_doc = frappe.get_doc("Attendance", attendance[0].name)

                    # Allow update after submit
                    att_doc.flags.ignore_validate_update_after_submit = True
                    att_doc.flags.ignore_permissions = True

                    att_doc.status = "Half Day"
                    att_doc.save()

                    

            # Move to next day
            current = add_days(current, 1)

    return "\n".join(msg)


from datetime import datetime, time

# ----------------------------------------------------------
# Helper: Minutes difference
# ----------------------------------------------------------
def minutes_between(t1, t2):
    return int((t2 - t1).total_seconds() / 60)


# ----------------------------------------------------------
# Get total late minutes based on shift periods
# ----------------------------------------------------------
@frappe.whitelist()
def get_employee_late_minutes(employee, start_date, end_date):

    start_dt = datetime.combine(frappe.utils.getdate(start_date), datetime.min.time())
    end_dt = datetime.combine(frappe.utils.getdate(end_date), datetime.max.time())

    logs = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee, "time": ["between", [start_dt, end_dt]]},
        fields=["time", "log_type"],
        order_by="time asc"
    )

    last_in = None
    total_late_minutes = 0

    for log in logs:

        if log.log_type == "IN":
            last_in = log.time

        elif log.log_type == "OUT" and last_in:

            # Skip Fridays
            if last_in.weekday() == 4:
                last_in = None
                continue

            in_time = last_in.time()

            # ----------------------------------------------------
            # SHIFT MATCHING RULES
            # ----------------------------------------------------

            # 1️⃣ Morning Shift (09:00 → 12:00)
            if time(9, 0) <= in_time < time(12, 0):
                threshold = time(9, 15)
                if in_time > threshold:
                    late = minutes_between(
                        datetime.combine(last_in.date(), threshold),
                        last_in
                    )
                    total_late_minutes += late

                last_in = None
                continue

            # 2️⃣ Evening Shift (16:00 → 21:00)
            if time(16, 0) <= in_time < time(21, 0):
                threshold = time(16, 15)
                if in_time > threshold:
                    late = minutes_between(
                        datetime.combine(last_in.date(), threshold),
                        last_in
                    )
                    total_late_minutes += late

                last_in = None
                continue

            # ----------------------------------------------------
            # Other time periods → NOT a shift → ignore
            # ----------------------------------------------------
            last_in = None

    return total_late_minutes




# ----------------------------------------------------------
# Main calculation: salary deduction based on late minutes
# ----------------------------------------------------------
@frappe.whitelist()
def calculate_late_deduction(employee, start_date, end_date):
    late_minutes = get_employee_late_minutes(employee, start_date, end_date)

    emp = frappe.get_doc("Employee", employee)
    salary = emp.custom_basic_salary or 0

    salary_per_day = salary / 30
    salary_per_minute = salary_per_day / 480  # 8 hours × 60 minutes

    deduction_value = late_minutes * salary_per_minute

    return late_minutes, deduction_value


# ----------------------------------------------------------
# Called when Payroll Entry is submitted
# ----------------------------------------------------------
@frappe.whitelist()
def LateMin(name):
    payroll = frappe.get_doc("Payroll Entry", name)
    start_date = payroll.start_date
    end_date = payroll.end_date

    updated_employees = []

    for row in payroll.employees:
        employee = row.employee

        late_minutes, deduction_value = calculate_late_deduction(
            employee, start_date, end_date
        )

        # Update SSA
        ssa = frappe.get_all(
            "Salary Structure Assignment",
            filters={"employee": employee},
            fields=["name"],
            limit=1
        )

        if ssa:
            frappe.db.set_value(
                "Salary Structure Assignment",
                ssa[0].name,
                "custom_late_min",
                late_minutes
            )

            updated_employees.append(f"{employee}: {late_minutes} min")

    frappe.db.commit()

    return "Late Minutes Updated:\n" + "\n".join(updated_employees)