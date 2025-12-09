import frappe
from frappe.utils import getdate, add_days, now_datetime, get_datetime, flt
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
# GET EMPLOYEE LATE MINUTES WITH FINAL RULES
# =====================================================================

# =====================================================================
# GET EMPLOYEE LATE MINUTES WITH SHIFT RULES (FRIDAY EXCLUDED)
# =====================================================================
def get_employee_late_minutes(employee, start_date, end_date):
    print(f"[DEBUG] get_employee_late_minutes START for {employee}")

    start_dt = datetime.combine(getdate(start_date), datetime.min.time())
    end_dt = datetime.combine(getdate(end_date), datetime.max.time())

    # Fetch all checkins/outs
    logs = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee, "time": ["between", [start_dt, end_dt]]},
        fields=["time", "log_type", "shift"],  # assuming shift field exists
        order_by="time asc"
    )

    last_in = None
    total_late = 0

    for log in logs:

        if log.log_type == "IN":
            last_in = log.time
            last_shift = getattr(log, "shift", None)  # get shift if available
            continue

        if log.log_type == "OUT" and last_in:

            # Skip Fridays
            if last_in.weekday() == 4:
                print(f"[DEBUG] Friday detected → skipping {last_in.date()}")
                last_in = None
                continue

            in_t = last_in.time()
            out_t = log.time.time()

            # ----- MORNING SHIFT (9:00–12:00) -----
            if last_shift == "Showroom (Morning Period)" or (time(9, 0) <= in_t < time(12, 0)):
                if in_t <= time(9, 15):
                    required = 180
                    start_from = time(9, 0)
                else:
                    required = 165
                    start_from = in_t

                spent = minutes_between(datetime.combine(last_in.date(), start_from), log.time)
                late = max(0, required - spent)
                total_late += late
                print(f"[DEBUG] Morning late: {late}")
                last_in = None
                continue

            # ----- EVENING SHIFT (16:00–21:00) -----
            if last_shift == "Showroom (Evening period Saudian)" or (time(16, 0) <= in_t < time(21, 0)):
                if in_t <= time(16, 15):
                    required = 300
                    start_from = time(16, 0)
                else:
                    required = 285
                    start_from = in_t

                spent = minutes_between(datetime.combine(last_in.date(), start_from), log.time)
                late = max(0, required - spent)
                total_late += late
                print(f"[DEBUG] Evening late: {late}")
                last_in = None
                continue

            # ----- FACTORY SHIFT (9:00–16:45) -----
            if last_shift == "Factory Shift":
                required = 525  # minutes for Factory Shift
                start_9 = datetime.combine(last_in.date(), time(9, 0))
                end_1645 = datetime.combine(last_in.date(), time(16, 45))
                end_1700 = datetime.combine(last_in.date(), time(17, 0))

                check_in_dt = last_in
                check_out_dt = log.time

                print(f"[DEBUG][FACTORY] IN={in_t} OUT={out_t}")

                # 1️⃣ In <=8:15 and Out >=16:45 → 0 late
                if in_t <= time(8, 15) and out_t >= time(16, 45):
                    late = 0
                    print("[DEBUG][FACTORY] Case 1: In<=8:15 & Out>=16:45 → late=0")

                # 2️⃣ In >8:15 and Out >=16:45 → late = 525 - duration(in → 17:00)
                elif in_t > time(8, 15) and out_t >= time(16, 45):
                    duration = minutes_between(check_in_dt, end_1700)
                    late = max(0, required - duration)
                    print(f"[DEBUG][FACTORY] Case 2: In>8:15 & Out>=16:45 → duration={duration}, late={late}")

                # 3️⃣ In <=8:15 and Out <16:45 → late = 525 - duration(8:00 → out)
                elif in_t <= time(8, 15) and out_t < time(16, 45):
                    duration = minutes_between(start_9, check_out_dt)
                    late = max(0, required - duration)
                    print(f"[DEBUG][FACTORY] Case 3: In<=8:15 & Out<16:45 → duration={duration}, late={late}")

                # 4️⃣ In >8:15 and Out <16:45 → late = 510 - duration(in → out)
                else:
                    duration = minutes_between(check_in_dt, check_out_dt)
                    late = max(0, 510 - duration)
                    print(f"[DEBUG][FACTORY] Case 4: In>8:15 & Out<16:45 → duration={duration}, late={late}")

                total_late += late
                print(f"[DEBUG] Factory late: {late}")
                last_in = None
                continue


            last_in = None

    print(f"[DEBUG] TOTAL late minutes for {employee}: {total_late}")
    return total_late




# =====================================================================
# SALARY DEDUCTION CALCULATION
# =====================================================================
@frappe.whitelist()
def calculate_late_deduction(employee, start_date, end_date):

    late_minutes = get_employee_late_minutes(employee, start_date, end_date)

    emp = frappe.get_doc("Employee", employee)
    salary = emp.custom_basic_salary or 0

    salary_per_day = salary / 30
    salary_per_minute = salary_per_day / 480

    deduction = late_minutes * salary_per_minute

    print(f"[DEBUG] Late: {late_minutes}, Deduction: {deduction}")

    return late_minutes, deduction


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

    updated = []

    for row in payroll.employees:
        employee = row.employee

        late_minutes, deduction_value = calculate_late_deduction(
            employee, start_date, end_date
        )

        # Update Salary Structure Assignment
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
                deduction_value
            )

            frappe.msgprint(f"✔ {employee} → Deduction: {deduction_value:.2f}")
            updated.append(f"{employee}: {deduction_value:.2f}")

    frappe.db.commit()

    return "Late Deduction Updated:\n" + "\n".join(updated)

@frappe.whitelist()
def calculate_overtime_for_salary_slip(salary_slip, employee, start_date, end_date):
    print(f"[DEBUG] Calculating overtime for Salary Slip: {salary_slip}")
    print(f"[DEBUG] Employee: {employee}, Period: {start_date} → {end_date}")

    overtime = get_employee_overtime(employee, start_date, end_date)

    print(f"[DEBUG] Total overtime for {employee}: {overtime}")

    return {
        "overtime_amount": overtime
    }

@frappe.whitelist()
def get_employee_overtime(employee, start_date, end_date):
    """
    Calculate total overtime amount for an employee in a given period.
    """

    print(f"[DEBUG] Fetching Overtime logs for Employee: {employee}")
    print(f"[DEBUG] Date range: {start_date} → {end_date}")

    # Fetch all approved overtime records for the employee in the period
    overtime_logs = frappe.db.get_all(
        "Overtime",
        filters={
            "employee": employee,
            "posting_date": ["between", [start_date, end_date]]
        },
        fields=["name", "posting_date", "total_amount_of_money"]
    )

    print(f"[DEBUG] Found {len(overtime_logs)} overtime logs")

    for log in overtime_logs:
        print(f"[DEBUG] Overtime log: {log}")

    # Sum all total_amount_of_money
    total_overtime = sum([flt(log.total_amount_of_money) for log in overtime_logs])

    print(f"[DEBUG] Computed total overtime: {total_overtime}")

    return total_overtime


# @frappe.whitelist()
# def adjust_friday_attendance_on_refresh(employee, start_date, end_date):
#     """
#     Check attendance for the employee in the given period.
#     If attendance is found on Friday → +0.5 payment_days, -0.5 absent_days.
#     """

#     print("[DEBUG] Friday Attendance Check START")
#     print(f"[DEBUG] Employee: {employee}")
#     print(f"[DEBUG] Period: {start_date} → {end_date}")

#     # Fetch attendance
#     attendances = frappe.get_all(
#         "Attendance",
#         filters={
#             "employee": employee,
#             "attendance_date": ["between", [start_date, end_date]],
#             "status": "Present"
#         },
#         fields=["attendance_date"]
#     )

#     print(f"[DEBUG] Attendance records found: {len(attendances)}")

#     added_days = 0

#     for att in attendances:
#         weekday = getdate(att.attendance_date).weekday()  # Monday=0 ... Sunday=6

#         if weekday == 4:  # 4 = Friday
#             added_days += 0.5
#             print(f"[DEBUG] Friday attendance: {att.attendance_date}")

#     print(f"[DEBUG] Total Friday days to add: {added_days}")

#     return {"added_days": added_days}
