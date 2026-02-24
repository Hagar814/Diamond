import frappe

def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = []

    opportunity_filters = {}
    if filters.get("opportunity"):
        opportunity_filters["name"] = filters["opportunity"]
    if filters.get("project"):
        opportunity_filters["custom_project"] = filters["project"]
    if filters.get("customer"):
        opportunity_filters["party_name"] = filters["customer"]
    

    opportunities = frappe.get_all(
        "Opportunity",
        filters=opportunity_filters,
        fields=[
            "name",
            "status",
            "opportunity_from",
            "party_name",
            "custom_project"
        ]
    )

    for opp in opportunities:
        quotation_filters = {"opportunity": opp.name}
        if filters.get("quotation"):
            quotation_filters["name"] = filters["quotation"]

        quotations = frappe.get_all(
            "Quotation",
            filters=quotation_filters,
            fields=["name", "status"]
        )

        # If no quotations, just add opportunity row
        if not quotations:
            data.append(base_row(opp))
            continue

        for qt in quotations:
            # -----------------------------
            # Fetch Timesheet linked to Opportunity
            # -----------------------------
            opp_timesheets = frappe.get_all(
                "Timesheet",
                filters=[["custom_opportunity", "=", opp.name]],
                fields=["name"]
            )

            # -----------------------------
            # Fetch Timesheet linked to Project
            # -----------------------------
            project_timesheets = frappe.get_all(
                "Timesheet",
                filters=[["parent_project", "=", opp.custom_project]],
                fields=["name"]
            )

            # -----------------------------
            # Fetch Timesheet linked to Quotation
            # -----------------------------
            quotation_timesheets = frappe.get_all(
                "Timesheet",
                filters=[["custom_opportunity", "=", opp.name], ["custom_quotation", "=", qt.name]],
                fields=["name"]
            )

            # -----------------------------
            # Fetch Sales Orders linked to Quotation Items
            # -----------------------------
            sales_orders_info = []
            quotation_items = frappe.get_all(
                "Quotation Item",
                filters={"parent": qt.name},
                fields=["name", "item_code", "item_name", "qty"]
            )
            for q_item in quotation_items:
                so_items = frappe.get_all(
                    "Sales Order Item",
                    filters={"quotation_item": q_item.name},
                    fields=["parent", "item_code", "item_name", "qty", "rate", "amount"]
                )
                for so_item in so_items:
                    so_doc = frappe.get_doc("Sales Order", so_item.parent)
                    sales_orders_info.append({
                        "sales_order": so_doc.name,
                        "so_status": so_doc.status,
                        "so_item_code": so_item.item_code,
                        "so_item_name": so_item.item_name,
                        "so_item_qty": so_item.qty,
                        "so_item_rate": so_item.rate,
                        "so_item_amount": so_item.amount
                    })

            # If no timesheets, add base row with Sales Orders
            if not opp_timesheets and not project_timesheets and not quotation_timesheets:
                row = base_row(opp, qt.name)
                row["sales_orders"] = ", ".join([so["sales_order"] for so in sales_orders_info])
                row["so_status"] = ", ".join([so["so_status"] for so in sales_orders_info])
                row["so_items"] = ", ".join([f"{so['so_item_code']} ({so['so_item_qty']})" for so in sales_orders_info])
                data.append(row)
                continue

            # -----------------------------
            # Fill rows for Opportunity Timesheets
            # -----------------------------
            for ts in opp_timesheets:
                time_logs = frappe.get_all(
                    "Timesheet Detail",
                    filters={"parent": ts.name},
                    fields=["activity_type", "from_time", "to_time", "hours", "completed"]
                )
                if not time_logs:
                    row = base_row(opp, qt.name, ts.name)
                    row["opp_timesheet"] = ts.name
                    data.append(row)
                    continue
                for tl in time_logs:
                    row = base_row(opp, qt.name, ts.name)
                    row.update({
                        "timesheet": ts.name,
                        "activity_type": tl.activity_type,
                        "from_time": tl.from_time,
                        "to_time": tl.to_time,
                        "completed": tl.completed,
                        "sales_orders": ", ".join([so["sales_order"] for so in sales_orders_info]),
                        "so_status": ", ".join([so["so_status"] for so in sales_orders_info]),
                        "so_items": ", ".join([f"{so['so_item_code']} ({so['so_item_qty']})" for so in sales_orders_info]),
                        "quotation": qt.name,
                        "quotation_status": qt.status,
                        "project": opp.custom_project
                    })
                    data.append(row)

            # -----------------------------
            # Fill rows for Project Timesheets
            # -----------------------------
            for ts in project_timesheets:
                time_logs = frappe.get_all(
                    "Timesheet Detail",
                    filters={"parent": ts.name},
                    fields=["activity_type", "from_time", "to_time", "hours", "completed"]
                )
                if not time_logs:
                    row = base_row(opp, qt.name, ts.name)
                    row["p_timesheet"] = ts.name
                    data.append(row)
                    continue
                for tl in time_logs:
                    row = base_row(opp, qt.name, ts.name)
                    row.update({
                        "p_timesheet": ts.name,
                        "p_activity_type": tl.activity_type,
                        "p_from_time": tl.from_time,
                        "p_to_time": tl.to_time,
                        "p_completed": tl.completed,
                        "sales_orders": ", ".join([so["sales_order"] for so in sales_orders_info]),
                        "so_status": ", ".join([so["so_status"] for so in sales_orders_info]),
                        "so_items": ", ".join([f"{so['so_item_code']} ({so['so_item_qty']})" for so in sales_orders_info]),
                        "quotation": qt.name,
                        "quotation_status": qt.status,
                        "project": opp.custom_project
                    })
                    data.append(row)

            # -----------------------------
            # Fill rows for Quotation Timesheets
            # -----------------------------
            for ts in quotation_timesheets:
                time_logs = frappe.get_all(
                    "Timesheet Detail",
                    filters={"parent": ts.name},
                    fields=["activity_type", "from_time", "to_time", "hours", "completed"]
                )
                if not time_logs:
                    row = base_row(opp, qt.name, ts.name)
                    row["q_timesheet"] = ts.name
                    data.append(row)
                    continue
                for tl in time_logs:
                    row = base_row(opp, qt.name, ts.name)
                    row.update({
                        "q_timesheet": ts.name,
                        "q_activity_type": tl.activity_type,
                        "q_from_time": tl.from_time,
                        "q_to_time": tl.to_time,
                        "q_completed": tl.completed,
                        "sales_orders": ", ".join([so["sales_order"] for so in sales_orders_info]),
                        "so_status": ", ".join([so["so_status"] for so in sales_orders_info]),
                        "so_items": ", ".join([f"{so['so_item_code']} ({so['so_item_qty']})" for so in sales_orders_info]),
                        "quotation": qt.name,
                        "quotation_status": qt.status,
                        "project": opp.custom_project
                    })
                    data.append(row)

    return columns, data


def base_row(opp, quotation=None, timesheet=None):
    return {
        "opportunity": opp.name,
        "opportunity_from": opp.party_name,
        "opp_status":opp.status,
        "project": opp.custom_project,
        "customer": opp.party_name,
        "quotation": quotation,
        "timesheet": timesheet
    }


def get_columns():
    return [
        {"label": "Opportunity", "fieldname": "opportunity", "fieldtype": "Link", "options": "Opportunity", "width": 160},
        {"label": "Opportunity Status", "fieldname": "opp_status", "fieldtype": "Data", "width": 120},
        {"label": "Opportunity Form", "fieldname": "opportunity_from", "fieldtype": "Data", "width": 160},
        {"label": "Party", "fieldname": "customer", "fieldtype": "Data", "width": 160},

        {"label": "Timesheet", "fieldname": "timesheet", "fieldtype": "Link", "options": "Timesheet", "width": 160},
        {"label": "Activity Type", "fieldname": "activity_type", "fieldtype": "Link", "options": "Activity Type", "width": 140},
        {"label": "From Time", "fieldname": "from_time", "fieldtype": "Datetime", "width": 150},
        {"label": "To Time", "fieldname": "to_time", "fieldtype": "Datetime", "width": 150},
        {"label": "Completed", "fieldname": "completed", "fieldtype": "Check", "width": 100},

        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
        {"label": "P_Timesheet", "fieldname": "p_timesheet", "fieldtype": "Link", "options": "Timesheet", "width": 160},
        {"label": "P_Activity Type", "fieldname": "p_activity_type", "fieldtype": "Link", "options": "Activity Type", "width": 140},
        {"label": "P_From Time", "fieldname": "p_from_time", "fieldtype": "Datetime", "width": 150},
        {"label": "P_To Time", "fieldname": "p_to_time", "fieldtype": "Datetime", "width": 150},
        {"label": "P_Completed", "fieldname": "p_completed", "fieldtype": "Check", "width": 100},

        {"label": "Quotation", "fieldname": "quotation", "fieldtype": "Link", "options": "Quotation", "width": 160},
        {"label": "Quotation Status", "fieldname": "quotation_status", "fieldtype": "Data", "width": 120},

        {"label": "Q_Timesheet", "fieldname": "q_timesheet", "fieldtype": "Link", "options": "Timesheet", "width": 160},
        {"label": "Q_Activity Type", "fieldname": "q_activity_type", "fieldtype": "Link", "options": "Activity Type", "width": 140},
        {"label": "Q_From Time", "fieldname": "q_from_time", "fieldtype": "Datetime", "width": 150},
        {"label": "Q_To Time", "fieldname": "q_to_time", "fieldtype": "Datetime", "width": 150},
        {"label": "Q_Completed", "fieldname": "q_completed", "fieldtype": "Check", "width": 100},

        {"label": "Sales Orders", "fieldname": "sales_orders", "fieldtype": "Data", "width": 160},
        {"label": "Sales Order Status", "fieldname": "so_status", "fieldtype": "Data", "width": 120},
        {"label": "Sales Order Items", "fieldname": "so_items", "fieldtype": "Data", "width": 300},
    ]
