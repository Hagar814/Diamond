frappe.ui.form.on("Zkteco Setting", {
    refresh: function(frm) {
        frm.add_custom_button("Sync Checkins", function() {

            frappe.call({
                method: "employee.sync.sync_zkteco_token",
                freeze: true,
                freeze_message: "Syncing BioTime checkins...",
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frm.reload_doc();
                    }
                }
            });

        });
    }
});
