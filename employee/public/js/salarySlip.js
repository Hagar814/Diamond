frappe.ui.form.on("Salary Slip", {
    refresh(frm) {
        if (frm.doc.docstatus === 0) {
            calculate_overtime(frm);
        }
        frappe.call({
            method: "employee.api.adjust_friday_attendance_on_refresh",
            args: { name: frm.doc.name },
            callback: function(r) {
                console.log("✅ adjust_friday_attendance_on_refresh response:", r.message);
            },
            error: function(err) {
                console.error("❌ adjust_friday_attendance_on_refresh error:", err);
            }
        });

    }
});

function calculate_overtime(frm) {
    frappe.call({
        method: "employee.api.calculate_overtime_for_salary_slip",
        args: {
            salary_slip: frm.doc.name,
            employee: frm.doc.employee,
            start_date: frm.doc.start_date,
            end_date: frm.doc.end_date
        },
        callback: function (r) {
            if (!r.message) return;

            let overtime_amount = r.message.overtime_amount;

            // remove old overtime row
            frm.clear_table("earnings");

            // Add overtime as a new row
            let row = frm.add_child("earnings");
            row.salary_component = "Overtime";   // <-- your salary component name
            row.amount = overtime_amount;

            frm.refresh_field("earnings");

            frappe.msgprint(`Overtime calculated: ${overtime_amount}`);
        }
    });
}
