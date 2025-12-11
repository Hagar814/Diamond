frappe.ui.form.on('ZkTeco BioTime Settings', {
    onload(frm) {
        add_sync_button(frm);
    },
    refresh(frm) {
        add_sync_button(frm);
    }
});

function add_sync_button(frm) {
    // Prevent adding multiple buttons
    if (!frm.sync_button_added) {
        frm.add_custom_button("Sync Now", () => {
            frappe.call({
                method: "employee.sync.sync_biotime_checkins",
                callback: function() {
                    frappe.msgprint("Sync Completed");
                }
            });
        });
        frm.sync_button_added = true;
    }
}
