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
# =====================================================================
# SHIFT-BASED LATE CALCULATION (FINAL RULES)
# =====================================================================

def get_employee_late_minutes(employee, start_date, end_date):
    print(f"[DEBUG] get_employee_late_minutes START for {employee}")

    start_dt = datetime.combine(getdate(start_date), datetime.min.time())
    end_dt = datetime.combine(getdate(end_date), datetime.max.time())

    logs = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee, "time": ["between", [start_dt, end_dt]]},
        fields=["time", "log_type"],
        order_by="time asc"
    )

    last_in = None
    total_late = 0

    for log in logs:
        if log.log_type == "IN":
            last_in = log.time
            continue

        if log.log_type == "OUT" and last_in:
            in_t = last_in.time()
            out_t = log.time.time()

            # ----- MORNING SHIFT -----
            if time(9, 0) <= in_t < time(12, 0):

                required_minutes = 180  # 3h = 180 min

                # IN <= 9:15 → spent starts from 9:00
                start_count_from = time(9, 0) if in_t <= time(9, 15) else in_t

                spent = minutes_between(
                    datetime.combine(last_in.date(), start_count_from),
                    log.time
                )

                late = max(0, required_minutes - spent)
                total_late += late

                print(f"[DEBUG] Morning late: {late}")
                last_in = None
                continue

            # ----- EVENING SHIFT -----
            if time(16, 0) <= in_t < time(21, 0):

                required_minutes = 300  # 5h = 300 min

                # IN <= 16:15 → spent starts from 16:00
                start_count_from = time(16, 0) if in_t <= time(16, 15) else in_t

                spent = minutes_between(
                    datetime.combine(last_in.date(), start_count_from),
                    log.time
                )

                late = max(0, required_minutes - spent)
                total_late += late

                print(f"[DEBUG] Evening late: {late}")
                last_in = None
                continue

            last_in = None

    print(f"[DEBUG] Total late minutes: {total_late}")
    return total_late





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

        print(f"[DEBUG] Late minutes: {late_minutes}, Deduction value: {deduction_value}")
        print(f"[DEBUG] Updating SSA for {employee}")

        ssa = frappe.get_all(
            "Salary Structure Assignment",
            filters={"employee": employee},
            fields=["name"],
            limit=1
        )

        if ssa:
            # Save deduction value (currency) instead of minutes
            frappe.db.set_value(
                "Salary Structure Assignment",
                ssa[0].name,
                "custom_late_min",
                deduction_value
            )

            frappe.msgprint(f"✔ {employee} → Deduction: {deduction_value:.2f}")
            updated_employees.append(f"{employee}: {deduction_value:.2f}")

    frappe.db.commit()

    return "Late Deduction Updated:\n" + "\n".join(updated_employees)
