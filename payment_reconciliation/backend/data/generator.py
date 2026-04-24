import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

def generate_datasets(num_normal_transactions=100, month="2023-11"):
    """
    Generates test datasets for payment reconciliation with specific planted gaps.
    """
    start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")
    
    # 1. Normal Transactions
    platform_records = []
    bank_records = []
    
    for i in range(num_normal_transactions):
        txn_id = f"TXN-{1000 + i}"
        amount = round(random.uniform(500.0, 50000.0), 2)
        # Random date within the month
        day_offset = random.randint(0, 27)
        plat_date = start_date + timedelta(days=day_offset)
        
        # Bank settles 1-2 days later
        settle_delay = random.randint(1, 2)
        bank_date = plat_date + timedelta(days=settle_delay)
        
        platform_records.append({
            "transaction_id": txn_id,
            "date": plat_date.strftime("%Y-%m-%d"),
            "amount": amount,
            "type": "sale"
        })
        
        bank_records.append({
            "bank_ref": f"BNK-{1000 + i}",
            "transaction_id": txn_id,
            "settlement_date": bank_date.strftime("%Y-%m-%d"),
            "amount": amount,
            "type": "settlement"
        })

    # PLANTED GAPS

    # Gap 1: Transactions that settled the following month
    # Let's add 5 of these
    plat_date_eom = datetime(start_date.year, start_date.month, 30)
    bank_date_next_month = plat_date_eom + timedelta(days=1)
    
    for k in range(5):
        txn_id_cross = f"TXN-9001-{k}"
        amount_cross = 15000.00 + (k * 100)
        
        platform_records.append({
            "transaction_id": txn_id_cross,
            "date": plat_date_eom.strftime("%Y-%m-%d"),
            "amount": amount_cross,
            "type": "sale"
        })
        
        bank_records.append({
            "bank_ref": f"BNK-9001-{k}",
            "transaction_id": txn_id_cross,
            "settlement_date": bank_date_next_month.strftime("%Y-%m-%d"),
            "amount": amount_cross,
            "type": "settlement"
        })

    # Gap 2: Rounding difference that only shows when summed
    # Platform has 3 transactions of 3333.33 (Sum 9999.99). Bank settles as 10000.00
    # Let's add 3 groups like this
    for g in range(3):
        plat_date_round = start_date + timedelta(days=10 + g)
        bank_date_round = plat_date_round + timedelta(days=1)
        
        txn_group_id = f"TXN-9002-{g}"
        group_ref = f"GRP-{g+1}"
        for j in range(3):
            platform_records.append({
                "transaction_id": f"{txn_group_id}-{j}",
                "date": plat_date_round.strftime("%Y-%m-%d"),
                "amount": 3333.33,
                "type": "sale",
                "group_id": group_ref
            })
            
        bank_records.append({
            "bank_ref": f"BNK-9002-{g}",
            "transaction_id": group_ref,
            "settlement_date": bank_date_round.strftime("%Y-%m-%d"),
            "amount": 10000.00,
            "type": "settlement"
        })

    # Gap 3: Duplicate entries in one dataset
    # We will duplicate 4 normal transactions in the bank dataset
    for d in range(4):
        dup_source = bank_records[d].copy()
        dup_source['bank_ref'] = dup_source['bank_ref'] + "-DUP"
        bank_records.append(dup_source)


    # Gap 4: Refunds with no matching original transaction
    for r in range(6):
        platform_records.append({
            "transaction_id": f"TXN-9004-{r}",
            "date": (start_date + timedelta(days=15 + r)).strftime("%Y-%m-%d"),
            "amount": -5000.00 - (r * 50),
            "type": "refund"
        })
        
    # Gap 5: Missing in Bank
    for m in range(4):
        platform_records.append({
            "transaction_id": f"TXN-9005-{m}",
            "date": (start_date + timedelta(days=5)).strftime("%Y-%m-%d"),
            "amount": 12500.00,
            "type": "sale"
        })
        
    # Gap 6: Missing in Platform
    for m in range(3):
        bank_records.append({
            "bank_ref": f"BNK-9006-{m}",
            "transaction_id": f"TXN-9006-{m}",
            "settlement_date": (start_date + timedelta(days=20)).strftime("%Y-%m-%d"),
            "amount": 8000.00,
            "type": "settlement"
        })

    # Shuffle datasets
    random.shuffle(platform_records)
    random.shuffle(bank_records)

    # Convert to DataFrames
    df_platform = pd.DataFrame(platform_records)
    df_bank = pd.DataFrame(bank_records)

    # To ensure grouping logic for rounding difference works without explicit group_id in all rows
    # We will let the model group by date or similar, but typically a batch ID is used.
    # Let's adjust Gap 2 slightly to be more realistic:
    # Multiple platform transactions might settle as one batch in the bank.
    
    return df_platform, df_bank

if __name__ == "__main__":
    df_p, df_b = generate_datasets()
    os.makedirs("generated", exist_ok=True)
    df_p.to_csv("generated/platform_data.csv", index=False)
    df_b.to_csv("generated/bank_data.csv", index=False)
    print("Datasets generated in 'generated' folder.")
