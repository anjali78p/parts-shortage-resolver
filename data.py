"""Mock data. Real dealership system ki jagah hum yahi use karenge."""

LOCAL_STORE = "A"

repair_orders = {
    "RO-1042": {"vehicle": "Honda City", "job": "Brake job", "part_no": "BP-221",
                "bay": 3, "tech": "T-07", "start": "10:00", "duration_hrs": 2,
                "status": "Waiting on Part"},
    "RO-1055": {"vehicle": "Hyundai i20", "job": "Oil service", "part_no": "OIL-10",
                "bay": 1, "tech": "T-02", "start": "14:00", "duration_hrs": 1,
                "status": "Scheduled"},
    "RO-1060": {"vehicle": "Maruti Swift", "job": "Oil service", "part_no": "OIL-10",
                "bay": 2, "tech": "T-03", "start": "11:00", "duration_hrs": 1,
                "status": "Waiting on Part"},
    "RO-1070": {"vehicle": "Tata Nexon", "job": "Wipers", "part_no": "WP-5",
                "bay": 4, "tech": "T-05", "start": "12:00", "duration_hrs": 1,
                "status": "Scheduled"},
}

# inventory[store_id][part_no] = qty
inventory = {
    "A": {"BP-221": 0, "OIL-10": 5, "WP-5": 3},
    "B": {"BP-221": 2, "OIL-10": 10},
    "C": {"BP-221": 0},
}

stores = {
    "B": {"name": "Store B - Malviya Nagar", "distance_km": 12, "transfer_hours": 3},
    "C": {"name": "Store C - Vaishali Nagar", "distance_km": 8, "transfer_hours": 2},
}

vendors = [
    {"vendor": "AutoParts Direct", "part_no": "BP-221", "price": 1850, "eta_hours": 24, "qty": 20},
    {"vendor": "QuickSpares", "part_no": "BP-221", "price": 2100, "eta_hours": 6, "qty": 5},
]
