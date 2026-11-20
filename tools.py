"""Plain Python functions. Abhi inhe nodes seedha call karenge.
Step 3 mein inhe @tool bana ke LLM ko denge."""
from data import LOCAL_STORE, internal_part_price, inventory, stores, vendors


def check_local_inventory(part_no: str) -> int:
    return inventory.get(LOCAL_STORE, {}).get(part_no, 0)


def check_sister_stores(part_no: str) -> list[dict]:
    found = []
    for store_id, stock in inventory.items():
        if store_id == LOCAL_STORE:
            continue
        qty = stock.get(part_no, 0)
        if qty > 0:
            total = internal_part_price.get(part_no, 0) + stores[store_id]["transfer_cost"]
            found.append({"store_id": store_id, "qty": qty, "total_cost_inr": total,
                          **stores[store_id]})
    return found


def check_vendor_stock(part_no: str) -> list[dict]:
    return [v for v in vendors if v["part_no"] == part_no and v["qty"] > 0]
