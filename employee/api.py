import frappe
from frappe.utils import getdate, add_days, now_datetime, get_datetime
from datetime import datetime, time

# =====================================================================
# VALIDATE HALF DAY
# =====================================================================
@frappe.whitelist()
def validate_payroll_half_day(name):
    frappe.msgprint(f"🔍 validate_payroll_half_day STARTED for: {name}")
    print(f"[DEBUG] validate_payroll_half_day STARTED for: {name}")

    payroll = frappe.get_doc("Payroll Entry", name)
    start = getdate(payroll.start_date)
    end = getdate(payroll.end_date)

    msg = []

    for row in payroll.employees:
        emp_id = row.employee
        frappe.msgprint(f"➡ Checking employee: {emp_id}")
        print(f"[DEBUG] Checking employee: {emp_id}")

        current = start

        while current <= end:
            frappe.msgprint(f"📌 Checking date: {current}")
            print(f"[DEBUG] Checking date: {current}")

            day_start = get_datetime(str(current) + " 00:00:00")
            day_end = get_datetime(str(current) + " 23:59:59")

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
            print(f"[DEBUG] IN count for {emp_id} on {current}: {in_count}")

            if in_count == 1:
                print(f"[DEBUG] Half-Day candidate found for {emp_id} on {current}")

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
                    print(f"[DEBUG] Updating Attendance {attendance[0].name} → Half Day")

                    att_doc.flags.ignore_validate_update_after_submit = True
                    att_doc.flags.ignore_permissions = True

                    att_doc.status = "Half Day"
                    att_doc.save()

                    frappe.msgprint(
                        f"✔ Updated Attendance for {emp_id} on {current} → Half Day"
                    )

            current = add_days(current, 1)

    return "\n".join(msg)



# =====================================================================
# UTILITY – MINUTES BETWEEN TWO TIMES
# =====================================================================
def minutes_between(t1, t2):
    diff = int((t2 - t1).total_seconds() / 60)
    print(f"[DEBUG] minutes_between → {diff} minutes")
    return diff



# =====================================================================
# GET EMPLOYEE LATE MINUTES WITH DEBUG LOGGING
# =====================================================================
@frappe.whitelist()
def get_employee_late_minutes(employee, start_date, end_date):

    frappe.msgprint(f"⏱ Calculating late minutes for {employee}")
    print(f"[DEBUG] get_employee_late_minutes START for {employee}")

    start_dt = datetime.combine(getdate(start_date), datetime.min.time())
    end_dt = datetime.combine(getdate(end_date), datetime.max.time())

    logs = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee, "time": ["between", [start_dt, end_dt]]},
        fields=["time", "log_type"],
        order_by="time asc"
    )

    print(f"[DEBUG] Total checkins found: {len(logs)}")
    last_in = None
    total_late_minutes = 0

    for log in logs:
        print(f"[DEBUG] Log: {log.log_type} - {log.time}")

        if log.log_type == "IN":
            last_in = log.time
            print(f"[DEBUG] IN stored: {last_in}")

        elif log.log_type == "OUT" and last_in:

            # Skip Friday
            if last_in.weekday() == 4:
                print(f"[DEBUG] Friday detected → Skipping late calculation")
                last_in = None
                continue

            in_time = last_in.time()
            print(f"[DEBUG] Checking shift for IN time: {in_time}")

            # MORNING SHIFT
            if time(9, 0) <= in_time < time(12, 0):
                print("[DEBUG] Morning shift detected")
                threshold = time(9, 15)

                if in_time > threshold:
                    late = minutes_between(
                        datetime.combine(last_in.date(), threshold),
                        last_in
                    )
                    total_late_minutes += late
                    print(f"[DEBUG] Late (morning): {late}")

                last_in = None
                continue

            # EVENING SHIFT
            if time(16, 0) <= in_time < time(21, 0):
                print("[DEBUG] Evening shift detected")
                threshold = time(16, 15)

                if in_time > threshold:
                    late = minutes_between(
                        datetime.combine(last_in.date(), threshold),
                        last_in
                    )
                    total_late_minutes += late
                    print(f"[DEBUG] Late (evening): {late}")

                last_in = None
                continue

            print("[DEBUG] No shift matched → ignoring")
            last_in = None

    print(f"[DEBUG] Total late minutes for {employee}: {total_late_minutes}")
    return total_late_minutes



# =====================================================================
# SALARY DEDUCTION CALCULATION WITH DEBUG LOGGING
# =====================================================================
@frappe.whitelist()
def calculate_late_deduction(employee, start_date, end_date):

    print(f"[DEBUG] calculate_late_deduction for {employee}")

    late_minutes = get_employee_late_minutes(employee, start_date, end_date)
    print(f"[DEBUG] Late minutes: {late_minutes}")

    emp = frappe.get_doc("Employee", employee)
    salary = emp.custom_basic_salary or 0

    print(f"[DEBUG] Employee salary: {salary}")

    salary_per_day = salary / 30
    salary_per_minute = salary_per_day / 480

    deduction_value = late_minutes * salary_per_minute

    print(f"[DEBUG] Deduction value: {deduction_value}")

    return late_minutes, deduction_value



# =====================================================================
# MAIN FUNCTION – UPDATE SALARY STRUCTURE
# =====================================================================
@frappe.whitelist()
def LateMin(name):

    frappe.msgprint(f"🚀 LateMin STARTED for payroll: {name}")
    print(f"[DEBUG] LateMin STARTED for payroll: {name}")

    payroll = frappe.get_doc("Payroll Entry", name)
    start_date = payroll.start_date
    end_date = payroll.end_date

    updated_employees = []

    for row in payroll.employees:
        employee = row.employee
        print(f"[DEBUG] Processing {employee}")

        late_minutes, deduction_value = calculate_late_deduction(
            employee, start_date, end_date
        )

        print(f"[DEBUG] Updating SSA for {employee}")

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

            frappe.msgprint(f"✔ {employee} → {late_minutes} min late")
            updated_employees.append(f"{employee}: {late_minutes} min")

    frappe.db.commit()

    return "Late Minutes Updated:\n" + "\n".join(updated_employees)
