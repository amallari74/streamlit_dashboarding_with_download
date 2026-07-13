from datetime import datetime
import pandas as pd
from typing import Dict, Any, List
from .models.invoice_validation_model import (
    fetch_invoice_by_id,
    fetch_invoice_line_items,
    fetch_invoice_subscriptions,
    fetch_invoice_transactions,
    fetch_all_partner_transactions,
    fetch_all_partner_subscriptions,
    fetch_all_partner_line_items,
    fetch_all_completed_line_items,
    fetch_invoice_completed_line_items
)

class InvoiceValidationService:
    """Service for validating invoice data and related components"""
    
    def __init__(self, schema: str = "", database: str = None):
        """Initialize the service with schema and database parameters"""
        self.schema = schema
        self.database = database
        
    def fetch_full_invoice_data(self, invoice_id: int) -> Dict[str, Any]:
        """Fetch all relevant data for an invoice"""
        try:
            # Fetch invoice header
            invoice_df = fetch_invoice_by_id(invoice_id, self.schema, self.database)
            if invoice_df.empty:
                return {
                    "invoice": pd.DataFrame(),
                    "invoice_line_items": pd.DataFrame(),
                    "subscriptions": pd.DataFrame(),
                    "transactions": pd.DataFrame(),
                    "partner_id": None,
                    "invoice_date": None,
                    "error": "Invoice not found"
                }
            
            # Get partner ID and invoice date for additional queries
            partner_id = invoice_df.iloc[0]['partner_id']
            invoice_date = invoice_df.iloc[0]['invoice_date']
            
            # Fetch related data
            invoice_line_items_df = fetch_invoice_line_items(invoice_id, self.schema, self.database)
            subscriptions_df = fetch_invoice_subscriptions(invoice_id, self.schema, self.database)
            transactions_df = fetch_invoice_transactions(invoice_id, self.schema, self.database)
            completed_line_items_df = fetch_invoice_completed_line_items(invoice_id, self.schema, self.database)
            
            # Fetch partner-wide data for comparison
            partner_line_items_df = fetch_all_partner_line_items(partner_id, self.schema, self.database)
            partner_subscriptions_df = fetch_all_partner_subscriptions(partner_id, self.schema, self.database)
            partner_transactions_df = fetch_all_partner_transactions(partner_id, self.schema, self.database)
            partner_completed_line_items_df = fetch_all_completed_line_items(partner_id, self.schema, self.database)
            
            return {
                "invoice": invoice_df,
                "invoice_line_items": invoice_line_items_df,
                "subscriptions": subscriptions_df,
                "transactions": transactions_df,
                "partner_transactions": partner_transactions_df,
                "partner_subscriptions": partner_subscriptions_df,
                "partner_line_items": partner_line_items_df,
                "completed_line_items": completed_line_items_df,
                "partner_completed_line_items": partner_completed_line_items_df,
                "partner_id": partner_id,
                "invoice_date": invoice_date,
                "error": None
            }
            
        except Exception as e:
            return {
                "invoice": pd.DataFrame(),
                "invoice_line_items": pd.DataFrame(),
                "subscriptions": pd.DataFrame(),
                "transactions": pd.DataFrame(),
                "partner_transactions": pd.DataFrame(),
                "partner_subscriptions": pd.DataFrame(),
                "partner_line_items": pd.DataFrame(),
                "completed_line_items": pd.DataFrame(),
                "partner_id": None,
                "invoice_date": None,
                "error": str(e)
            }
    
    def validate_invoice(self, invoice_id: int) -> Dict[str, Any]:
        """Validate an invoice and its components"""
        # Fetch all data
        data = self.fetch_full_invoice_data(invoice_id)
        
        if data["error"]:
            return {
                "success": False,
                "invoice_id": invoice_id,
                "error": data["error"],
                "invoice_data": None,
                "timestamp": datetime.now().isoformat()
            }
        
        # Basic counts for display
        counts = {
            "invoice": len(data["invoice"]),
            "invoice_line_items": len(data["invoice_line_items"]),
            "transactions": len(data["transactions"]),
            "subscriptions": len(data["subscriptions"]),
            "completed_line_items": len(data["completed_line_items"]),
            "partner_line_items": len(data["partner_line_items"]),
            "partner_transactions": len(data["partner_transactions"]),
            "partner_subscriptions": len(data["partner_subscriptions"]),
            "partner_completed_line_items": len(data["partner_completed_line_items"])
        }
        
        return {
            "success": True,
            "invoice_id": invoice_id,
            "error": None,
            "invoice_data": data,
            "counts": counts,
            "timestamp": datetime.now().isoformat()
        }
      
    def analyze_invoice_data(self, data: dict) -> dict:
        """Analyze invoice data and related records"""
        results = {
            "missing_subscriptions": 0,
            "missing_transactions": 0,
            "invoice_info": {},
            "records_associated": {},
            "partner_records": {},
            "billing_period": {},
            "subscription_analysis": {},
            "transaction_analysis": {},
            "line_item_analysis": {}
        }
        
        # Get invoice information
        invoice = data["invoice"].iloc[0] if not data["invoice"].empty else None
        if invoice is not None:
            invoice_date = pd.to_datetime(invoice.get('invoice_date'))
            invoice_month = invoice_date.month if invoice_date else None
            invoice_year = invoice_date.year if invoice_date else None
            
            results["invoice_info"] = {
                "id": invoice.get('id'),
                "invoice_date": invoice.get('invoice_date'),
                "partner_id": invoice.get('partner_id'),
                "company_id": invoice.get('company_id'),
                "status": invoice.get('status'),
                "total": invoice.get('total'),
                "month": invoice_month,
                "year": invoice_year
            }
            
            # Get billing period from line items
            if not data["invoice_line_items"].empty:
                line_items = data["invoice_line_items"]
                if 'start_period' in line_items.columns:
                    line_items['start_period'] = pd.to_datetime(line_items['start_period'])
                if 'end_period' in line_items.columns:
                    line_items['end_period'] = pd.to_datetime(line_items['end_period'])
                min_start = line_items['start_period'].min() if 'start_period' in line_items.columns else None
                max_end = line_items['end_period'].max() if 'end_period' in line_items.columns else None
                
                results["billing_period"] = {
                    "start": min_start,
                    "end": max_end
                }
            
            # Records associated with invoice
            results["records_associated"] = {
                "invoice_line_items": len(data["invoice_line_items"]),
                "subscriptions": len(data["subscriptions"]),
                "transactions": len(data["transactions"])
            }
            
            # Partner records
            results["partner_records"] = {
                "partner_transactions": len(data["partner_transactions"]),
                "partner_subscriptions": len(data["partner_subscriptions"]),
                "partner_line_items": len(data["partner_line_items"]),
                "completed_line_items": len(data["completed_line_items"])
            }
            
            # Subscription analysis
            if not data["partner_subscriptions"].empty:
                subs_df = data["partner_subscriptions"]
                
                # Convert dates and get invoice month range
                invoice_date = pd.to_datetime(invoice.get('invoice_date'))
                invoice_month_start = pd.Timestamp(year=invoice_date.year, month=invoice_date.month, day=1)
                prev_month_start = invoice_month_start - pd.DateOffset(months=1)
                prev_month_start_plus_one_day = prev_month_start + pd.DateOffset(days=1)
                
                # Initialize the subscription analysis with the date range data
                results["subscription_analysis"] = {
                    "total_subscriptions": len(subs_df),
                    "date_range": {
                        "start": prev_month_start_plus_one_day.strftime("%Y-%m-%d"),
                        "end": invoice_month_start.strftime("%Y-%m-%d")
                    }
                }
                
                # Ensure start_period is datetime
                if 'start_period' in subs_df.columns:
                    subs_df['start_period'] = pd.to_datetime(subs_df['start_period'])
                    
                    # Filter subscriptions within the valid date range
                    # Changed to exclude the first day of the previous month
                    valid_range_subs = subs_df[
                        (subs_df['start_period'] >= prev_month_start_plus_one_day) & 
                        (subs_df['start_period'] <= invoice_month_start)
                    ]
                    
                    # Set valid range subscriptions count
                    results["subscription_analysis"]["valid_range_subscriptions"] = len(valid_range_subs)
                    
                    # Filter active subscriptions
                    if 'status' in subs_df.columns:
                        active_subs = subs_df[subs_df['status'].str.lower() == 'active']
                        active_valid_range_subs = valid_range_subs[valid_range_subs['status'].str.lower() == 'active']
                        
                        # Update subscription analysis with active counts
                        results["subscription_analysis"]["active_subscriptions"] = len(active_subs)
                        results["subscription_analysis"]["active_valid_range_subscriptions"] = len(active_valid_range_subs)
                        
                        # Check billing cycles
                        if 'billing_cycle_start' in active_subs.columns:
                            active_subs['billing_cycle_start'] = pd.to_datetime(active_subs['billing_cycle_start'])
                            active_subs['billing_cycle_month'] = active_subs['billing_cycle_start'].dt.month
                            active_subs['billing_cycle_year'] = active_subs['billing_cycle_start'].dt.year
                            
                            should_be_in_invoice = active_subs[
                                (active_subs['billing_cycle_month'] == invoice_month) & 
                                (active_subs['billing_cycle_year'] == invoice_year)
                            ]
                            
                            # Update subscription analysis with should be in invoice count
                            results["subscription_analysis"]["should_be_in_invoice"] = len(should_be_in_invoice)
                            
                            # Check which are in the invoice
                            if not data["subscriptions"].empty and 'completed_line_id' in active_subs.columns:
                                invoice_subs = data["subscriptions"]
                                
                                if 'completed_line_id' in invoice_subs.columns:
                                    invoice_completed_line_ids = set(invoice_subs['completed_line_id'].dropna())
                                    should_be_in_cli_ids = set(should_be_in_invoice['completed_line_id'].dropna())
                                    missing_subs = should_be_in_cli_ids - invoice_completed_line_ids
                                    results["missing_subscriptions"] = len(missing_subs)
                                    
                                    # Add remaining missing subscriptions details
                                    results["subscription_analysis"]["missing_subscriptions"] = len(missing_subs)
                                    results["subscription_analysis"]["missing_subscription_details"] = should_be_in_invoice[
                                        should_be_in_invoice['completed_line_id'].isin(missing_subs)
                                    ].to_dict('records') if len(missing_subs) > 0 else []
            
            # Transaction analysis
            if not data["partner_transactions"].empty:
                trans_df = data["partner_transactions"]
                
                # Check which transactions are in the invoice
                if not data["transactions"].empty and 'transaction_id' in data["transactions"].columns:
                    invoice_trans = data["transactions"]
                    
                    if 'transaction_id' in invoice_trans.columns and 'transaction_id' in trans_df.columns:
                        invoice_trans_ids = set(invoice_trans['transaction_id'].astype(str).dropna())
                        all_trans_ids = set(trans_df['transaction_id'].astype(str).dropna())
                        
                        missing_trans = all_trans_ids - invoice_trans_ids
                        
                        # Filter by invoice month/year
                        if 'invoice_date' in trans_df.columns:
                            missing_trans_df = trans_df[trans_df['transaction_id'].astype(str).isin(missing_trans)]
                            missing_trans_df['invoice_date'] = pd.to_datetime(missing_trans_df['invoice_date'])
                            missing_trans_df['trans_month'] = missing_trans_df['invoice_date'].dt.month
                            missing_trans_df['trans_year'] = missing_trans_df['invoice_date'].dt.year
                            
                            should_be_in_invoice = missing_trans_df[
                                (missing_trans_df['trans_month'] == invoice_month) & 
                                (missing_trans_df['trans_year'] == invoice_year)
                            ]
                            
                            results["missing_transactions"] = len(should_be_in_invoice)
                            
                            # Add detailed transaction analysis
                            results["transaction_analysis"] = {
                                "total_transactions": len(trans_df),
                                "distinct_transaction_ids": len(all_trans_ids),
                                "duplicate_transactions": len(trans_df) - len(all_trans_ids),
                                "missing_transactions": len(should_be_in_invoice),
                                "missing_transaction_details": should_be_in_invoice.to_dict('records') if len(should_be_in_invoice) > 0 else [],
                                "monthly_distribution": missing_trans_df.groupby(['trans_year', 'trans_month']).size().to_dict()
                            }
            
            # Line item analysis
            if not data["invoice_line_items"].empty and not data["partner_line_items"].empty:
                invoice_line_items = data["invoice_line_items"]
                partner_line_items = data["partner_line_items"]
                
                invoice_line_item_ids = set(invoice_line_items['line_item_id'].astype(str)) if 'line_item_id' in invoice_line_items.columns else set()
                partner_line_item_ids = set(partner_line_items['line_item_id'].astype(str)) if 'line_item_id' in partner_line_items.columns else set()
                
                missing_line_items = partner_line_item_ids - invoice_line_item_ids
                
                results["line_item_analysis"] = {
                    "missing_line_items": len(missing_line_items),
                    "missing_line_item_details": partner_line_items[partner_line_items['line_item_id'].astype(str).isin(missing_line_items)].to_dict('records') if len(missing_line_items) > 0 else []
                }
        
        return results

    @staticmethod
    def analyze_single_cli(
        cli_record: Dict[str, Any],
        linked_subscription: Dict[str, Any],
        linked_transactions: pd.DataFrame,
        invoice_line_items: pd.DataFrame,
        invoice_month: int,
        invoice_year: int
    ) -> Dict[str, bool]:
        """
        Analyzes a single Completed Line Item (CLI) to determine if it 
        should be billable for a given invoice month, if it is present 
        on the invoice, and if a transaction exists for the period.

        Args:
            cli_record: A dictionary representing the single Completed Line Item.
            linked_subscription: A dictionary representing the subscription linked to the CLI.
            linked_transactions: DataFrame of transactions linked to the CLI.
            invoice_line_items: DataFrame of line items from the specific invoice being analyzed.
            invoice_month: The month of the invoice (1-12).
            invoice_year: The year of the invoice.

        Returns:
            A dictionary containing:
            - cli_in_invoice (bool): True if a corresponding line item is found on the invoice.
            - cli_should_be_billable (bool): True if the analysis suggests this CLI 
                                             represents a potential charge based on subscription 
                                             status and billing frequency (monthly).
            - has_transaction_for_period (bool): True if a linked transaction exists with a 
                                                 start_period matching the invoice month/year.
        """
        analysis = {
            "cli_in_invoice": False,
            "cli_should_be_billable": False,
            "has_transaction_for_period": False # Initialize new key
        }
        cli_id = cli_record.get('id')
        print(f"\n--- Analyzing CLI ID: {cli_id} for Invoice Period: {invoice_year}-{invoice_month:02d} ---")

        # --- 1. Check if the CLI is represented on the current invoice --- 
        if cli_id is not None and not invoice_line_items.empty and 'completed_line_item_id' in invoice_line_items.columns:
            invoice_line_items['completed_line_item_id'] = invoice_line_items['completed_line_item_id'].astype(str)
            if str(cli_id) in invoice_line_items['completed_line_item_id'].values:
                analysis["cli_in_invoice"] = True
        print(f"[Debug analyze_single_cli] CLI {cli_id} - Found in invoice: {analysis['cli_in_invoice']}")

        # --- 2. Determine if the CLI *should* potentially be billable & check transaction --- 
        should_bill = False # Default assumption
        
        # Condition A: Subscription must be valid
        sub_id = linked_subscription.get('id')
        sub_status = linked_subscription.get('status', '')
        sub_is_active = sub_status.lower() == 'active'
        sub_quantity = linked_subscription.get('quantity', 0)
        sub_quantity_ok = sub_quantity > 0
        commitment_end_str = linked_subscription.get('commitment_term_end_date')
        sub_commitment_ok = False
        invoice_period_start = pd.Timestamp(year=invoice_year, month=invoice_month, day=1)
        if commitment_end_str:
            try:
                commitment_end_date = pd.to_datetime(commitment_end_str)
                if commitment_end_date >= invoice_period_start:
                    sub_commitment_ok = True
            except Exception as e:
                 print(f"[Debug analyze_single_cli] CLI {cli_id} - Error parsing commitment date '{commitment_end_str}': {e}")
                 pass
        subscription_valid = sub_is_active and sub_quantity_ok and sub_commitment_ok
        print(f"[Debug analyze_single_cli] CLI {cli_id} - Subscription Validity Check (Sub ID: {sub_id}):")
        print(f"  - Status Active? ({sub_status}): {sub_is_active}")
        print(f"  - Quantity > 0? ({sub_quantity}): {sub_quantity_ok}")
        print(f"  - Commitment OK? (End: {commitment_end_str} >= {invoice_period_start.strftime('%Y-%m-%d')}): {sub_commitment_ok}")
        print(f"  --> Subscription Valid Overall: {subscription_valid}")
        
        # Condition B: Billing frequency must be monthly (based on CLI)
        cli_term_months = cli_record.get('term_in_months')
        is_monthly_billing = cli_term_months == 1 
        print(f"[Debug analyze_single_cli] CLI {cli_id} - Monthly Billing Check:")
        print(f"  - CLI term_in_months: {cli_term_months}")
        print(f"  --> Is Monthly Billing: {is_monthly_billing}")
        
        # Condition C: Check if a linked transaction exists for the invoice month/year
        transaction_matches_period = False
        matching_tx_id = None
        if not linked_transactions.empty and 'start_period' in linked_transactions.columns:
            linked_transactions['start_period'] = pd.to_datetime(linked_transactions['start_period'], errors='coerce')
            for index, tx in linked_transactions.iterrows():
                tx_date = tx['start_period']
                tx_id_col = 'transaction_id' if 'transaction_id' in tx else 'id'
                tx_id = tx.get(tx_id_col, 'N/A')
                if pd.notna(tx_date) and tx_date.year == invoice_year and tx_date.month == invoice_month:
                    transaction_matches_period = True
                    matching_tx_id = tx_id
                    break
        print(f"[Debug analyze_single_cli] CLI {cli_id} - Transaction Period Check ({invoice_year}-{invoice_month:02d}):")
        if matching_tx_id:
            print(f"  - Found matching transaction ID: {matching_tx_id}")
        print(f"  --> Transaction Matches Period: {transaction_matches_period}")
        
        # Set the separate transaction check result
        analysis["has_transaction_for_period"] = transaction_matches_period
                    
        # Final Decision: Should it potentially be billable (based on sub and freq)?
        print(f"[Debug analyze_single_cli] CLI {cli_id} - Final Decision Logic (Should Bill?):")
        print(f"  - Subscription Valid: {subscription_valid}")
        print(f"  - Is Monthly Billing: {is_monthly_billing}")
        # Note: Transaction existence is NOT part of this decision anymore
        
        if subscription_valid and is_monthly_billing:
            should_bill = True
            
        analysis["cli_should_be_billable"] = should_bill
        print(f"  --> Calculated cli_should_be_billable: {should_bill}")
        print(f"--- End Analysis for CLI ID: {cli_id} ---")

        return analysis

    @staticmethod
    def identify_potentially_billable_clis(
        partner_subscriptions: pd.DataFrame,
        partner_completed_line_items: pd.DataFrame,
        invoice_month: int,
        invoice_year: int
    ) -> List[int]:
        """
        Identifies Completed Line Item IDs that are potentially billable for a given month
        based on subscription status (linked via subscription.completed_line_id -> cli.id) 
        and monthly billing terms derived from the CLI.
        Refactored to iterate through subscriptions and look up linked CLIs.

        Args:
            partner_subscriptions: DataFrame of all subscriptions for the partner.
            partner_completed_line_items: DataFrame of all CLIs for the partner.
            invoice_month: The month of the invoice (1-12).
            invoice_year: The year of the invoice.

        Returns:
            A list of unique integer CLI IDs that are potentially billable.
        """
        billable_cli_ids = set() # Use a set to automatically handle uniqueness
        print(f"\n--- Identifying Potentially Billable CLIs for {invoice_year}-{invoice_month:02d} (Sub -> CLI approach) ---")

        if partner_subscriptions.empty or partner_completed_line_items.empty:
            print("[Debug identify_potentially_billable_clis] Input subscriptions or CLIs DataFrame is empty. Returning empty list.")
            return []

        # --- Pre-process and Index CLIs for faster lookup --- 
        clis_df = partner_completed_line_items.copy()
        clis_df['id_num'] = pd.to_numeric(clis_df['id'], errors='coerce')
        clis_df = clis_df.dropna(subset=['id_num'])
        clis_df['id_num'] = clis_df['id_num'].astype(int)
        # Check for duplicate CLI IDs before setting index
        if clis_df['id_num'].duplicated().any():
             print("[Debug identify_potentially_billable_clis] Warning: Duplicate CLI IDs found. Indexing may lose data.")
             # Optionally handle duplicates, e.g., keep first or last
             clis_df = clis_df.drop_duplicates(subset=['id_num'], keep='last') 
        clis_df = clis_df.set_index('id_num')
        print(f"[Debug identify_potentially_billable_clis] Indexed {len(clis_df)} CLIs for lookup.")

        # --- Iterate through Partner Subscriptions --- 
        subs_df = partner_subscriptions.copy()
        subs_processed = 0
        clis_passed = 0
        invoice_period_start = pd.Timestamp(year=invoice_year, month=invoice_month, day=1)

        # Check for essential columns
        required_cli_cols = ['term_in_months'] # Checked via clis_df.loc access
        required_sub_cols = ['id', 'status', 'quantity', 'commitment_term_end_date', 'completed_line_id'] 
        
        if not all(col in subs_df.columns for col in required_sub_cols):
            missing = set(required_sub_cols) - set(subs_df.columns)
            print(f"[Debug identify_potentially_billable_clis] Missing required columns in partner_subscriptions: {missing}. Aborting.")
            return []
        # Check for required columns in the indexed clis_df
        if not all(col in clis_df.columns for col in required_cli_cols):
             missing = set(required_cli_cols) - set(clis_df.columns)
             print(f"[Debug identify_potentially_billable_clis] Missing required columns in partner_completed_line_items: {missing}. Aborting.")
             return []
             
        print(f"[Debug identify_potentially_billable_clis] Iterating through {len(subs_df)} Subscriptions...")
        for index, sub_row in subs_df.iterrows():
            subs_processed += 1
            sub_id = sub_row['id']
            
            # 1. Check Subscription Validity first
            sub_status = sub_row.get('status', '')
            sub_is_active = sub_status.lower() == 'active'

            sub_quantity = pd.to_numeric(sub_row.get('quantity'), errors='coerce')
            sub_quantity_ok = (sub_quantity is not None and sub_quantity > 0)

            commitment_end_str = sub_row.get('commitment_term_end_date')
            sub_commitment_ok = False
            if commitment_end_str:
                try:
                    commitment_end_date = pd.to_datetime(commitment_end_str)
                    if commitment_end_date >= invoice_period_start:
                        sub_commitment_ok = True
                except Exception:
                    pass # Ignore parsing errors, commitment assumed not ok

            subscription_valid = sub_is_active and sub_quantity_ok and sub_commitment_ok
            
            if not subscription_valid:
                # print(f"  Skipping Sub {sub_id}: Not valid (Status: {sub_status}, Qty: {sub_quantity}, CommitEnd: {commitment_end_str})")
                continue

            # 2. Find linked CLI
            linked_cli_id = pd.to_numeric(sub_row.get('completed_line_id'), errors='coerce')
            if pd.isna(linked_cli_id):
                # print(f"  Skipping Sub {sub_id}: Missing or invalid linked completed_line_id")
                continue
            linked_cli_id_int = int(linked_cli_id)

            try:
                cli_data = clis_df.loc[linked_cli_id_int]
            except KeyError:
                # print(f"  Skipping Sub {sub_id}: Linked CLI ID {linked_cli_id_int} not found in indexed CLIs.")
                continue
            # If duplicate CLI IDs existed and loc returns a DataFrame (shouldn't if we dropped duplicates)
            if isinstance(cli_data, pd.DataFrame):
                if not cli_data.empty:
                    cli_data = cli_data.iloc[0]
                else:
                     continue 

            # 3. Check if linked CLI indicates Monthly billing
            cli_term_months = pd.to_numeric(cli_data.get('term_in_months'), errors='coerce')
            is_monthly_billing = (cli_term_months == 1)

            # 4. If Sub is Valid AND linked CLI is Monthly, add the CLI ID
            if is_monthly_billing:
                # print(f"  PASSED: Sub {sub_id} -> CLI {linked_cli_id_int} (Valid: {subscription_valid}, Monthly: {is_monthly_billing}) ")
                billable_cli_ids.add(linked_cli_id_int) # Add the CLI ID itself
                clis_passed += 1
            # else:
                # print(f"  FAILED: Sub {sub_id} -> CLI {linked_cli_id_int} (Valid: {subscription_valid}, Monthly: {is_monthly_billing})")
        
        final_list = sorted(list(billable_cli_ids))
        print(f"[Debug identify_potentially_billable_clis] Processed {subs_processed} Subscriptions. Found {len(final_list)} potentially billable CLI IDs.")
        print(f"--- Identification Complete. Returning {len(final_list)} IDs ---")
        return final_list
