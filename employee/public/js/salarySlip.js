frappe.ui.form.on("Salary Slip", {
    refresh(frm) {
        // Run only in Draft
        if (frm.doc.docstatus !== 0) return;

        // Prevent infinite refresh loops
        if (frm._friday_adjusted) return;

        // Make sure all required fields exist
        if (!frm.doc.employee || !frm.doc.start_date || !frm.doc.end_date) return;

        // 1️⃣ Calculate overtime (your function)
        calculate_overtime(frm);
        frappe.call({
            method: "employee.api.adjust_friday_attendance_on_refresh",
            args: {
                employee: frm.doc.employee,
                start_date: frm.doc.start_date,
                end_date: frm.doc.end_date
            },
            callback(r) {
                console.log(r.message.added_days);
            }
        });
    }
});


// function calculate_overtime(frm) {
//     frappe.call({
//         method: "employee.api.calculate_overtime_for_salary_slip",
//         args: {
//             salary_slip: frm.doc.name,
//             employee: frm.doc.employee,
//             start_date: frm.doc.start_date,
//             end_date: frm.doc.end_date
//         },
//         callback: function (r) {
//             if (!r.message) return;

//             let overtime_amount = r.message.overtime_amount;

//             // remove old overtime row
//             frm.clear_table("earnings");

//             // Add overtime as a new row
//             let row = frm.add_child("earnings");
//             row.salary_component = "Overtime";   // <-- your salary component name
//             row.amount = overtime_amount;

//             frm.refresh_field("earnings");

//             frappe.msgprint(`Overtime calculated: ${overtime_amount}`);
//         }
//     });
// }
