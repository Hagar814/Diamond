import frappe
from datetime import datetime, timedelta

# ----------------------------------------------------------
# Calculate difference between IN/OUT time logs
# ----------------------------------------------------------
@frappe.whitelist()
def hours_between(t1, t2):
    return (t2 - t1).total_seconds() / 3600


# ----------------------------------------------------------
# Get all IN/OUT logs for the employee within period
# ----------------------------------------------------------
@frappe.whitelist()
def get_employee_work_hours(employee, start_date, end_date):
    # Convert dates to datetime objects
    start_dt = datetime.combine(frappe.utils.getdate(start_date), datetime.min.time())
    end_dt = datetime.combine(frappe.utils.getdate(end_date), datetime.max.time())

    logs = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [start_dt, end_dt]]
        },
        fields=["time", "log_type"],
        order_by="time asc"
    )

    total_hours_list = []
    last_in = None

    for log in logs:
        if log["log_type"] == "IN":
            last_in = log["time"]
        elif log["log_type"] == "OUT" and last_in:
            hours = hours_between(last_in, log["time"])
            total_hours_list.append(hours)
            last_in = None

    return total_hours_list


# ----------------------------------------------------------
# Main calculation for quarter-day deduction
# ----------------------------------------------------------
@frappe.whitelist()
def calculate_quarter_day(employee, start_date, end_date):
    hours_list = get_employee_work_hours(employee, start_date, end_date)

    # Count number of days with exactly 6 hours
    counter = sum(1 for h in hours_list if round(h, 1) == 6)

    # Employee salary
    emp_doc = frappe.get_doc("Employee", employee)
    salary = emp_doc.custom_basic_salary or 0
    salary_per_day = salary / 30

    quarter_day_value = salary_per_day / 4
    final_value = quarter_day_value * counter

    return final_value


# ----------------------------------------------------------
# Called from JS on Payroll Entry submit
# ----------------------------------------------------------
@frappe.whitelist()
def on_submit_payroll_entry(name):
    payroll = frappe.get_doc("Payroll Entry", name)
    start_date = payroll.start_date
    end_date = payroll.end_date

    updated_employees = []

    # Loop through child table of employees
    for row in payroll.employees:
        employee = row.employee

        value = calculate_quarter_day(employee, start_date, end_date)

        # Update Salary Structure Assignment for this employee
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
                "custom_quarter_day",
                value
            )
            updated_employees.append(f"{employee}: {value}")

    frappe.db.commit()

    return f"Quarter Day Updated for Employees:\n" + "\n".join(updated_employees)
