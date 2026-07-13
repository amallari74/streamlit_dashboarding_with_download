import pandas as pd
import datetime as dt


def generate_ledger_data(
    df: pd.DataFrame,
    type_column: str,
    partner_identifier: str,
    company_identifier: str,
    partner_id_col: str = None,
    company_id_col: str = None,
    subscription_id_col: str = None,
    partner_cost_col: str = None,
    company_cost_col: str = None,
    company_name_col: str = None,
    product_name_col: str = None,
    quantity_col: str = None,
    start_period_col: str = None,
    end_period_col: str = None,
    product_id_col: str = None,
    description_col: str = None, 
    calculation_method: str = None
) -> pd.DataFrame:
    """
    Generates ledger data based on specified calculation method.

    Args:
        df: Input DataFrame.
        type_column: Column name identifying row type.
        partner_identifier: Value for partner rows in type_column.
        company_identifier: Value for company rows in type_column.
        calculation_method: Method to use ('missed_billing' or 'duplicate_billing').
        *_col args: Column names for corresponding data.
        description_col: Base description string.

    Returns:
        DataFrame formatted for ledger upload.
    """

    ledger_upload_list = []
    today_first_of_month = dt.date.today().replace(day=1).strftime('%Y-%m-%d')

    allowed_methods = ['missed_billing', 'duplicate_billing']
    if calculation_method not in allowed_methods:
        raise ValueError(
            f"Invalid calculation_method: '{calculation_method}'. "
            f"Allowed values are: {allowed_methods}"
        )

    for _, row in df.iterrows():
        row_type = row.get(type_column)
        partner_cost = row.get(partner_cost_col, 0.0) if partner_cost_col else 0.0
        customer_cost = row.get(company_cost_col, 0.0) if company_cost_col else 0.0
        
        account_target = None
        cost_basis = 0.0
        partner_id = None
        
        if row_type == partner_identifier:
            account_target = 'Partner'
            cost_basis = partner_cost
            partner_id = row.get(partner_id_col) if partner_id_col else None
        elif row_type == company_identifier:
            account_target = 'Company'
            cost_basis = customer_cost
        else:
            continue

        ledger_type = None
        credit = None
        debit = None

        if calculation_method == 'missed_billing':
            if cost_basis > 0:
                ledger_type = 'SERVICE_CHARGE'
                debit = round(abs(cost_basis), 2)
            elif cost_basis < 0:
                ledger_type = 'SERVICE_CREDIT'
                credit = round(abs(cost_basis), 2)
        
        elif calculation_method == 'duplicate_billing':
            if cost_basis < 0:
                ledger_type = 'SERVICE_CHARGE'
                debit = round(abs(cost_basis), 2)
            elif cost_basis > 0:
                ledger_type = 'SERVICE_CREDIT'
                credit = round(abs(cost_basis), 2)

        if ledger_type:
            company_id = row.get(company_id_col) if company_id_col else None
            subscription_id = row.get(subscription_id_col) if subscription_id_col else None
            billing_period_start = row.get(start_period_col) if start_period_col else None
            billing_period_end = row.get(end_period_col) if end_period_col else None
            company_name = row.get(company_name_col, 'N/A') if company_name_col else 'N/A'
            product_name = row.get(product_name_col, 'N/A') if product_name_col else 'N/A'
            quantity = row.get(quantity_col, None) if quantity_col else None
            
            try:
                quantity_str = str(int(quantity)) if pd.notna(quantity) else 'N/A'
            except (ValueError, TypeError):
                quantity_str = 'N/A'
            
            base_desc = description_col if description_col else "Ledger Adjustment"
            description = f"{base_desc} for Company: {company_name} and Product: {product_name} at a quantity of {quantity_str}".strip()

            ledger_entry = {
                'Partner ID': partner_id, 
                'Company ID': company_id,
                'Subscription ID': subscription_id,
                'Type': ledger_type,
                'Transaction Date': today_first_of_month,
                'Credit': credit,
                'Debit': debit,
                'Description': description,
                'Partner UUID': None,
                'Vendor ID': None,
                'Company UUID': None,
                'Tax Excluded': False,
                'Subscription UUID': None,
                'Vendor UUID': None,
                'Billing Period Start': billing_period_start,
                'Billing Period End': billing_period_end,
                'Product ID': None 
            }
            ledger_upload_list.append(ledger_entry)

    return pd.DataFrame(ledger_upload_list)
