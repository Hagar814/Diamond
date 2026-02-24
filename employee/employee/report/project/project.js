// Copyright (c) 2026, Shiftits and contributors
// For license information, please see license.txt

frappe.query_reports["Project"] = {
  filters: [
    {
      fieldname: "opportunity",
      label: __("Opportunity"),
      fieldtype: "Link",
      options: "Opportunity"
    },
    {
      fieldname: "project",
      label: __("Project"),
      fieldtype: "Link",
      options: "Project"
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer"
    },
    {
      fieldname: "lead",
      label: __("Lead"),
      fieldtype: "Link",
      options: "Lead"
    },
    {
      fieldname: "quotation",
      label: __("Quotation"),
      fieldtype: "Link",
      options: "Quotation"
    },

    // 🔽 OPTIONAL BUT VERY USEFUL FOR TIMESHEETS
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date"
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date"
    },
    {
      fieldname: "employee",
      label: __("Employee"),
      fieldtype: "Link",
      options: "Employee"
    }
  ]
};
