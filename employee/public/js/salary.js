frappe.ui.form.on("Payroll Entry", {
    on_submit: function(frm) {
        frappe.call({
            method: "employee.api.on_submit_payroll_entry",
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
    }
});
