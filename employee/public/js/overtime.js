frappe.ui.form.on('Overtime', {
    // Triggered whenever the form is validated (on save)
    validate: function(frm) {
        calculate_total_amount(frm);
    },

    // Triggered whenever total_working_hours field is changed
    total_working_hours: function(frm) {
        calculate_total_amount(frm);
    }
});

// Helper function to calculate total_amount_of_money
function calculate_total_amount(frm) {
    
    if (!frm.doc.employee || !frm.doc.total_working_hours) {
        frm.set_value('total_amount_of_money', 0);
        return;
    }

    // Fetch employee details
    frappe.db.get_doc('Employee', frm.doc.employee).then(employee => {
        let basic_salary = employee.custom_basic_salary || 0;

        // Assuming 240 working hours per month (30 days x 8 hours)
        let hourly_rate = basic_salary / 240;

        // Overtime multiplier 1.5
        let total_amount = frm.doc.total_working_hours * hourly_rate * 1.5;

        frm.set_value('total_amount_of_money', total_amount);

        frm.save();
    });
}
