"""Mock data. Real dealership system ki jagah hum yahi use karenge."""

LOCAL_STORE = "A"
NOW = "09:00"  # demo ka "abhi ka time"

repair_orders = {
    "RO-1042": {"vehicle": "Honda City", "job": "Brake job", "job_type": "brakes", "part_no": "BP-221",
                "bay": 3, "tech": "T-07", "start": "10:00", "duration_hrs": 2,
                "status": "Waiting on Part", "promise_by_hours": 8},
    "RO-1055": {"vehicle": "Hyundai i20", "job": "Oil service", "job_type": "oil_service", "part_no": "OIL-10",
                "bay": 1, "tech": "T-02", "start": "14:00", "duration_hrs": 1, "status": "Scheduled"},
    "RO-1060": {"vehicle": "Maruti Swift", "job": "Oil service", "job_type": "oil_service", "part_no": "OIL-10",
                "bay": 2, "tech": "T-03", "start": "11:00", "duration_hrs": 1, "status": "Waiting on Part"},
    "RO-1070": {"vehicle": "Tata Nexon", "job": "Wipers", "job_type": "wipers", "part_no": "WP-5",
                "bay": 4, "tech": "T-05", "start": "12:00", "duration_hrs": 1, "status": "Scheduled"},
    # Neeche 2 RO "trap" hain: ek ka part local nahi hai, doosre ke liye T-07 qualified nahi hai.
    "RO-1080": {"vehicle": "Kia Seltos", "job": "AC repair", "job_type": "ac_repair", "part_no": "AC-9",
                "bay": 2, "tech": "T-03", "start": "15:00", "duration_hrs": 3, "status": "Scheduled"},
    "RO-1090": {"vehicle": "Toyota Innova", "job": "Coolant flush", "job_type": "coolant_flush", "part_no": "CF-1",
                "bay": 1, "tech": "T-02", "start": "16:00", "duration_hrs": 2, "status": "Scheduled"},
}

technicians = {
    "T-07": {"name": "Ramesh", "skills": ["brakes", "oil_service", "wipers"]},
    "T-02": {"name": "Suresh", "skills": ["oil_service", "coolant_flush"]},
    "T-03": {"name": "Anita", "skills": ["oil_service", "ac_repair"]},
    "T-05": {"name": "Dev", "skills": ["wipers", "tyres"]},
}

# inventory[store_id][part_no] = qty
inventory = {
    "A": {"BP-221": 0, "OIL-10": 5, "WP-5": 3, "CF-1": 2, "AC-9": 0},
    "B": {"BP-221": 2, "OIL-10": 10},
    "C": {"BP-221": 0},
}

stores = {
    "B": {"name": "Store B - Malviya Nagar", "distance_km": 12, "transfer_hours": 3, "transfer_cost": 400},
    "C": {"name": "Store C - Vaishali Nagar", "distance_km": 8, "transfer_hours": 2, "transfer_cost": 250},
}

vendors = [
    {"vendor": "AutoParts Direct", "part_no": "BP-221", "price": 1850, "eta_hours": 24, "qty": 20},
    {"vendor": "QuickSpares", "part_no": "BP-221", "price": 2100, "eta_hours": 6, "qty": 5},
]

# Internal transfer price (store-to-store), vendor price se alag
internal_part_price = {"BP-221": 1600, "OIL-10": 300, "WP-5": 150}
