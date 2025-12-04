frappe.ui.form.on("Payroll Entry", {
    validate(frm) {

        // Call half-day validation

        frappe.call({
            method: "employee.api.validate_payroll_half_day",
            args: { name: frm.doc.name },
            callback: function(r) {
                console.log("✅ validate_payroll_half_day response:", r.message);
            },
            error: function(err) {
                console.error("❌ validate_payroll_half_day error:", err);
            }
        });

        // Call late minutes calculation
        frappe.call({
            method: "employee.api.LateMin",
            args: { name: frm.doc.name },
            callback: function(r) {
                console.log("✅ LateMin response:", r.message);
            },
            error: function(err) {
                console.error("❌ LateMin error:", err);
            }
        });

        // Call late minutes calculation
        frappe.call({
            method: "employee.api.update_overtime_on_payroll_validate",
            args: { name: frm.doc.name },
            callback: function(r) {
                console.log("✅ update_overtime_on_payroll_validate response:", r.message);
            },
            error: function(err) {
                console.error("❌ update_overtime_on_payroll_validate error:", err);
            }
        });

    }
});
