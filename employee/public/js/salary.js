frappe.ui.form.on("Payroll Entry", {
    validate: function(frm) {
        console.log("validate");
        frappe.call({
            method: "employee.api.validate_payroll_half_day",
            args: {
                name: frm.doc.name
            },
            callback: function(r) {
                if (r.message) {
                    frappe.msgprint(r.message);
                    frm.reload_doc();
                }
            }
        });

         frappe.call({
            method: "employee.api.LateMin",
            args: { name: frm.doc.name },
            callback(r) {
                if (r.message) {
                    frappe.msgprint(r.message);
                }
            }
        });
    }
});
