from utils import db_util
import pandas as pd

def fetch_duplicate_cira_line_items(invoice_date):
    query = """
    SELECT 
        * 
    FROM mart_observability_and_automation.fact_order_manager_cira_duplicates
    WHERE invoice_date = :invoice_date
    """

    params = {"invoice_date": invoice_date}
    return db_util.query(query, params=params)


def fetch_missing_subscriptions_invoice_line_items(invoice_date, cira_status, prorate_status=None, ledger_status=None, omt_subscription_match_status=None, omt_prorate_match_status=None, mt_subscription_match_status=None, mt_prorate_match_status=None):
    """
    Fetch missing subscriptions invoice line items for the given date range and status
    Returns a pandas DataFrame containing the data
    """
    if prorate_status is not None and ledger_status is not None and omt_subscription_match_status is not None and omt_prorate_match_status is not None and mt_subscription_match_status is not None and mt_prorate_match_status is not None:
        query = """
        SELECT 
            transaction_month,
            successor_partner_id AS partner_id,
            successor_partner_name AS partner_name,
            successor_company_id AS company_id,
            successor_company_name AS company_name,
            subscription_vendor AS vendor, 
            successor_product_id AS product_id,
            successor_product_name AS product_name, 
            impacted_audience, 
            partner_segment, 
            partner_country, 
            partner_region, 
            successor_term, 
            prior_term, 
            app_user_partner_id,
            app_user_company_id,
            app_user_email,
            app_user_name,
            modified_by_pax8,
            original_subscription_id, 
            original_subscription_guid, 
            max_subscription_id_transaction_month, 
            min_subscription_id_transaction_month, 
            successor_completed_line_item_id, 
            prior_completed_line_item_id, 
            successor_subscription_start_date, 
            successor_subscription_end_date,
            successor_billing_cycle_start_date, 
            successor_commitment_term_end_date, 
            commitment_term_end_date_in_past, 
            transaction_month_cancelled,
            cancellation_date,
            estimated_billing_renewal_date, 
            successor_quantity AS current_subscription_quantity,
            prior_quantity AS prior_subscription_quantity,
            cancellation_quantity, 
            successor_partner_buy_rate AS partner_buy_rate,
            successor_actual_retail_price AS actual_retail_price, 
            successor_wholesale_buy_rate AS wholesale_buy_rate,
            successor_exchange_rate_conversion_rate, 
            cira_record_id, 
            cira_invoice_date,
            cira_invoice_id,
            cira_partner_unit_cost,
            cira_partner_cost_total,
            cira_customer_unit_cost,
            cira_customer_cost_total,
            cira_start_period,
            cira_end_period,
            cira_subscription_match_status, 
            missed_revenue_non_usd,  
            missed_revenue_usd, 
            cira_prorate_match_status, 
            cira_prorate_total,
            cira_prorate_count,
            net_subscription_and_prorate_non_usd, 
            net_subscription_and_prorate_usd, 
            ledger_charge_count, 
            non_usd_debit AS service_charge_amount, 
            usd_debit AS service_charge_amount_usd,
            ledger_charge_match_status, 
            estimated_billing_start_period, 
            estimated_billing_end_period, 
            product_unit_of_measure, 
            successor_rate_plan_type, 
            charge_type, 
            completed_order_purchase_order_number, 
            currency_guid, 
            completed_line_item_guid, 
            subscription_guid, 
            product_uuid, 
            product_vendor_uuid, 
            completed_line_item_sku, 
            is_flat_rate, 
            partner_guid, 
            company_guid
        FROM mart_observability_and_automation.fact_subscription_monthly_billing_projection_combined
        WHERE cira_subscription_match_status = :cira_status
        AND cira_prorate_match_status = :prorate_status
        AND ledger_charge_match_status = :ledger_status
        AND transaction_month = :invoice_date
        AND omt_subscription_match_status = :omt_subscription_match_status
        AND omt_prorate_match_status = :omt_prorate_match_status
        AND mt_subscription_match_status = :mt_subscription_match_status
        AND mt_prorate_match_status = :mt_prorate_match_status
        """

        params = {"invoice_date": invoice_date, "cira_status": cira_status, "prorate_status": prorate_status, "ledger_status": ledger_status, "omt_subscription_match_status": omt_subscription_match_status, "omt_prorate_match_status": omt_prorate_match_status, "mt_subscription_match_status": mt_subscription_match_status, "mt_prorate_match_status": mt_prorate_match_status}
    else:
        query = """
        SELECT 
            transaction_month,
            successor_partner_id AS partner_id,
            successor_partner_name AS partner_name,
            successor_company_id AS company_id,
            successor_company_name AS company_name,
            subscription_vendor AS vendor, 
            successor_product_id AS product_id,
            successor_product_name AS product_name, 
            impacted_audience, 
            partner_segment, 
            partner_country, 
            partner_region, 
            successor_term, 
            prior_term, 
            app_user_partner_id,
            app_user_company_id,
            app_user_email,
            app_user_name,
            modified_by_pax8,
            original_subscription_id, 
            original_subscription_guid, 
            max_subscription_id_transaction_month, 
            min_subscription_id_transaction_month, 
            successor_completed_line_item_id, 
            prior_completed_line_item_id, 
            successor_subscription_start_date, 
            successor_subscription_end_date,
            successor_billing_cycle_start_date, 
            successor_commitment_term_end_date, 
            commitment_term_end_date_in_past, 
            transaction_month_cancelled,
            cancellation_date,
            estimated_billing_renewal_date, 
            successor_quantity AS current_subscription_quantity,
            prior_quantity AS prior_subscription_quantity,
            cancellation_quantity, 
            successor_partner_buy_rate AS partner_buy_rate,
            successor_actual_retail_price AS actual_retail_price, 
            successor_wholesale_buy_rate AS wholesale_buy_rate,
            successor_exchange_rate_conversion_rate, 
            cira_record_id, 
            cira_invoice_date,
            cira_invoice_id,
            cira_partner_unit_cost,
            cira_partner_cost_total,
            cira_customer_unit_cost,
            cira_customer_cost_total,
            cira_start_period,
            cira_end_period,
            cira_subscription_match_status, 
            missed_revenue_non_usd,  
            missed_revenue_usd, 
            cira_prorate_match_status, 
            cira_prorate_total,
            cira_prorate_count,
            net_subscription_and_prorate_non_usd, 
            net_subscription_and_prorate_usd, 
            ledger_charge_count, 
            non_usd_debit AS service_charge_amount, 
            usd_debit AS service_charge_amount_usd,
            ledger_charge_match_status, 
            estimated_billing_start_period, 
            estimated_billing_end_period, 
            product_unit_of_measure, 
            successor_rate_plan_type, 
            charge_type, 
            completed_order_purchase_order_number, 
            currency_guid, 
            completed_line_item_guid, 
            subscription_guid, 
            product_uuid, 
            product_vendor_uuid, 
            completed_line_item_sku, 
            is_flat_rate, 
            partner_guid, 
            company_guid
        FROM mart_observability_and_automation.fact_subscription_monthly_billing_projection_combined
        WHERE cira_subscription_match_status = :cira_status
        AND transaction_month = :invoice_date
        """

        params = {"invoice_date": invoice_date, "cira_status": cira_status}
    return db_util.query(query, params=params)


def fetch_missing_subscription_invoice_line_summary(invoice_date):
    query = """
    SELECT 
        transaction_month,
        product_count, 
        missing_partner_count, 
        missing_company_count, 
        missing_subscription_count, 
        missed_revenue_usd,
        missed_revenue_non_usd, 
        service_charges_posted_count,
        service_charges_posted_non_usd,
        service_charges_posted_usd,
        service_charges_posted_tax_non_usd,
        service_charges_posted_tax_usd
    FROM mart_observability_and_automation.agg_subscription_monthly_billing_projection
    WHERE transaction_month = :invoice_date
    """
    params = {"invoice_date": invoice_date}
    return db_util.query(query, params=params)