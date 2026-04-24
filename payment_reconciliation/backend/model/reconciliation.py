import pandas as pd
import numpy as np

def reconcile(platform_df, bank_df, target_month="2023-11"):
    """
    Reconciles platform and bank datasets to find gaps.
    """
    # Auto-rename columns if exact match not found
    platform_cols_lower = {c: c.lower() for c in platform_df.columns}
    bank_cols_lower = {c: c.lower() for c in bank_df.columns}
    
    # 1. Standardize Data
    if 'date' not in platform_df.columns:
        date_col = next((c for c in platform_df.columns if 'date' in c.lower()), None)
        if date_col: platform_df.rename(columns={date_col: 'date'}, inplace=True)
        else: raise ValueError("Platform dataset missing a 'date' column.")

    if 'settlement_date' not in bank_df.columns:
        # User said "It is not having bank settlement data". Fall back to 'date'
        date_col = next((c for c in bank_df.columns if 'settlement' in c.lower() or 'date' in c.lower()), None)
        if date_col: bank_df.rename(columns={date_col: 'settlement_date'}, inplace=True)
        else: raise ValueError("Bank dataset missing 'settlement_date' or 'date' column.")

    if 'amount' not in bank_df.columns:
        amt_col = next((c for c in bank_df.columns if 'amount' in c.lower()), None)
        if amt_col: bank_df.rename(columns={amt_col: 'amount'}, inplace=True)

    if 'amount' not in platform_df.columns:
        amt_col = next((c for c in platform_df.columns if 'amount' in c.lower()), None)
        if amt_col: platform_df.rename(columns={amt_col: 'amount'}, inplace=True)

    if 'transaction_id' not in bank_df.columns:
        txn_col = next((c for c in bank_df.columns if 'transaction' in c.lower() or 'txn' in c.lower() or 'id' in c.lower()), None)
        if txn_col: bank_df.rename(columns={txn_col: 'transaction_id'}, inplace=True)
        else: raise ValueError("Bank dataset missing 'transaction_id' column.")

    if 'transaction_id' not in platform_df.columns:
        txn_col = next((c for c in platform_df.columns if 'transaction' in c.lower() or 'txn' in c.lower() or 'id' in c.lower()), None)
        if txn_col: platform_df.rename(columns={txn_col: 'transaction_id'}, inplace=True)
        else: raise ValueError("Platform dataset missing 'transaction_id' column.")

    platform_df['date'] = pd.to_datetime(platform_df['date'], errors='coerce')
    bank_df['settlement_date'] = pd.to_datetime(bank_df['settlement_date'], errors='coerce')
    
    # 2. Find Duplicates in Bank
    # We define a duplicate as same transaction_id and amount appearing more than once
    # Or just same exact row data minus the bank_ref.
    # In our generator, we duplicated the entire bank row but appended "-DUP" to bank_ref
    bank_dups = bank_df[bank_df.duplicated(subset=['transaction_id', 'amount', 'settlement_date'], keep=False)]
    
    # Let's keep the first occurrence as valid, and mark the others as duplicate gaps
    bank_valid = bank_df.drop_duplicates(subset=['transaction_id', 'amount', 'settlement_date'], keep='first').copy()
    duplicate_gaps = bank_dups[bank_dups.duplicated(subset=['transaction_id', 'amount', 'settlement_date'], keep='first')].to_dict('records')
    
    # 3. Match Exact Transactions (1:1)
    # We join platform and valid bank records on transaction_id
    
    # We also have grouped transactions to handle. Platform has group_id.
    # If group_id exists, we aggregate platform transactions first.
    if 'group_id' in platform_df.columns:
        # separate single vs grouped
        plat_single = platform_df[platform_df['group_id'].isna()].copy()
        plat_grouped = platform_df[platform_df['group_id'].notna()].copy()
        
        # Aggregate grouped
        plat_grouped_agg = plat_grouped.groupby('group_id').agg({
            'amount': 'sum',
            'date': 'max', # take latest date
            'transaction_id': lambda x: list(x)
        }).reset_index()
        # Rename group_id to transaction_id to match with bank, and save original IDs
        plat_grouped_agg.rename(columns={'group_id': 'transaction_id', 'transaction_id': 'child_transactions'}, inplace=True)
        plat_grouped_agg['is_group'] = True
        
        plat_single['is_group'] = False
        
        plat_combined = pd.concat([plat_single, plat_grouped_agg], ignore_index=True)
    else:
        plat_combined = platform_df.copy()
        plat_combined['is_group'] = False
        
    # Now left join platform to bank
    merged = pd.merge(plat_combined, bank_valid, on='transaction_id', how='outer', suffixes=('_plat', '_bank'), indicator=True)
    
    # 4. Identify Gaps
    
    results = {
        "summary": {
            "total_platform_records": len(platform_df),
            "total_bank_records": len(bank_df),
            "total_amount_platform": float(platform_df['amount'].sum()),
            "total_amount_bank": float(bank_df['amount'].sum()),
        },
        "gaps": {
            "cross_month": [],
            "rounding_differences": [],
            "duplicates": duplicate_gaps,
            "unmatched_refunds": [],
            "missing_in_bank": [],
            "missing_in_platform": []
        }
    }
    
    matched_amount = 0
    
    # Process merged records
    for _, row in merged.iterrows():
        # Exact Match / Handled Match
        if row['_merge'] == 'both':
            # Check for rounding differences
            diff = abs(row['amount_plat'] - row['amount_bank'])
            if diff > 0 and diff < 1.0: # Arbitrary threshold for rounding
                results["gaps"]["rounding_differences"].append({
                    "transaction_id": row['transaction_id'],
                    "platform_amount": row['amount_plat'],
                    "bank_amount": row['amount_bank'],
                    "difference": round(row['amount_plat'] - row['amount_bank'], 2)
                })
            else:
                matched_amount += row['amount_bank']
                
            # Check for cross-month settlement
            if pd.notnull(row['date']) and pd.notnull(row['settlement_date']):
                plat_month = row['date'].strftime("%Y-%m")
                bank_month = row['settlement_date'].strftime("%Y-%m")
                if plat_month != bank_month:
                    results["gaps"]["cross_month"].append({
                        "transaction_id": row['transaction_id'],
                        "platform_date": row['date'].strftime("%Y-%m-%d"),
                        "bank_settlement_date": row['settlement_date'].strftime("%Y-%m-%d"),
                        "amount": row['amount_plat']
                    })
                
        elif row['_merge'] == 'left_only':
            # Missing in bank
            # Check if it's a refund
            if 'type_plat' in row and row['type_plat'] == 'refund':
                results["gaps"]["unmatched_refunds"].append({
                    "transaction_id": row['transaction_id'],
                    "date": row['date'].strftime("%Y-%m-%d") if pd.notnull(row['date']) else None,
                    "amount": row['amount_plat']
                })
            else:
                results["gaps"]["missing_in_bank"].append({
                    "transaction_id": row['transaction_id'],
                    "date": row['date'].strftime("%Y-%m-%d") if pd.notnull(row['date']) else None,
                    "amount": row['amount_plat']
                })
        elif row['_merge'] == 'right_only':
            results["gaps"]["missing_in_platform"].append({
                "bank_ref": row.get('bank_ref', row.get('settlement_id', 'UNKNOWN')),
                "transaction_id": row['transaction_id'],
                "date": row['settlement_date'].strftime("%Y-%m-%d") if pd.notnull(row['settlement_date']) else None,
                "amount": row['amount_bank']
            })

    # Calculate match rates
    results["summary"]["match_rate_percentage"] = round((matched_amount / results["summary"]["total_amount_platform"]) * 100, 2) if results["summary"]["total_amount_platform"] else 0
    results["summary"]["total_gaps_found"] = sum(len(g) for g in results["gaps"].values())
    
    return results

