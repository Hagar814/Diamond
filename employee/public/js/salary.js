frappe.ui.form.on("Payroll Entry", {
    validate(frm) {
        console.log("🟢 Validate triggered for Payroll Entry:", frm.doc.name);

        // Call half-day validation
        console.log("➡ Calling validate_payroll_half_day...");
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
        console.log("➡ Calling LateMin...");
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

        console.log("🟢 Validate function finished triggering calls");
    }
});
