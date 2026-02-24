frappe.ui.form.on("Payroll Entry", {

    // ===============================
    // RUN BEFORE SAVE (DRAFT)
    // ===============================
    // validate(frm)  {
    //     if (frm.doc.docstatus !== 0) return;

    //     // Half-day validation
    //     frappe.call({
    //         method: "employee.api.validate_payroll_half_day",
    //         args: { name: frm.doc.name },
    //         callback: function (r) {
    //             console.log("✅ validate_payroll_half_day response:", r.message);
    //         },
    //         error: function (err) {
    //             console.error("❌ validate_payroll_half_day error:", err);
    //         }
    //     });
    // },

    // ===============================
    // RUN AFTER SAVE (DRAFT)
    // ===============================
    after_save(frm) {
        if (frm.doc.docstatus !== 0) return;

        // Update Overtime in Salary Structure Assignment
        frappe.call({
            method: "employee.api.UpdateOvertime",
            args: { name: frm.doc.name },
            callback: function (r) {
                console.log("✅ UpdateOvertime response:", r.message);
            },
            error: function (err) {
                console.error("❌ UpdateOvertime error:", err);
            }
        });
    },

    // ===============================
    // RUN ON SUBMIT ONLY
    // ===============================
    refresh(frm) {
        if (frm.doc.docstatus == 0) return;
        frappe.call({
            method: "employee.api.LateMin",
            args: { name: frm.doc.name },
            callback: function (r) {
                console.log("✅ LateMin response:", r.message);
            },
            error: function (err) {
                console.error("❌ LateMin error:", err);
            }
        });
    }
});
