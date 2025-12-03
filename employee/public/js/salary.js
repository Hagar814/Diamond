frappe.ui.form.on("Payroll Entry", {
    validate(frm) {
        frappe.call({
            method: "employee.api.validate_payroll_half_day",
            args: { name: frm.doc.name }
        });

        frappe.call({
            method: "employee.api.LateMin",
            args: { name: frm.doc.name }
        });
    }
});