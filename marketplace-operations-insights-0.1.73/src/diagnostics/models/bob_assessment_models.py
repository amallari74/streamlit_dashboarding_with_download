from utils import db_util
import pandas as pd



def fetch_bob_assessment_summary_metrics(start_date, end_date):
    query = f"""
        select
            invoice_date,
            partner_id,
            partner_name,
            invoice_balance,
            invoice_balance_usd,
            company_count,
            bob_company_count,
            bob_invoice_paid_count,
            bob_payment_partner_ledger_total,
            partner_net_after_billing_fee_and_taxes,
            bob_payment_failed_posting_count,
            bob_payment_failed_posting_total,
            bob_with_duplicate_payment_posting,
            ledger_id,
            ledger_transaction_date,
            ledger_description,
            ledger_debit,
            ledger_debit_usd,
            ledger_duplicate_present
        from mart_observability_and_automation.agg_partner_bob_invoice_payment_summary 
        where invoice_date >= :start_date
        and invoice_date <= :end_date
        """
    return db_util.query(query, params={"start_date": start_date, "end_date": end_date})



def fetch_bob_assessment_overview_details(start_date, end_date, partner_id):
    query = f"""
    select
        invoice_date,
        partner_id,
        partner_name,
        partner_invoice_id, 
        partner_invoice_status, 
        company_id, 
        company_name, 
        invoice_type, 
        bob_invoice_id, 
        bob_invoice_status,
        partner_invoice_partner_total, 
        partner_billing_fee, 
        partner_surcharge_total, 
        bob_customer_total_with_tax,
        partner_net_after_customer_total, 
        partner_net_after_billing_fee_and_taxes, 
        bob_tax_witholding,
        bob_payment_posting_date, 
        bob_payment_credit, 
        bob_payment_id, 
        bob_payment_description, 
        bob_payment_duplicate_count, 
        expected_partner_bob_ledger_payment, 
        partner_bob_failed_posting
    from mart_observability_and_automation.agg_partner_bob_invoice_payment_assessment
        where invoice_date >= :start_date 
        and invoice_date <= :end_date
        and partner_id = :partner_id
    order by invoice_date desc
    """
    return db_util.query(query, params={"start_date": start_date, "end_date": end_date, "partner_id": partner_id})

def fetch_failed_bob_payment_postings():
    query = f"""
    select
        invoice_date,
        partner_id,
        partner_name,
        partner_invoice_id,
        partner_invoice_status,
        company_id,
        company_name,
        invoice_type,
        bob_invoice_id,
        bob_invoice_status,
        partner_invoice_partner_total,
        partner_billing_fee,
        partner_surcharge_total,
        bob_customer_total_with_tax,
        partner_net_after_customer_total,
        partner_net_after_billing_fee_and_taxes,
        bob_tax_witholding,
        bob_payment_posting_date,
        bob_payment_credit,
        bob_payment_id,
        bob_payment_description,
        bob_payment_duplicate_count,
        expected_partner_bob_ledger_payment,
        partner_bob_failed_posting
    from mart_observability_and_automation.agg_partner_bob_invoice_payment_assessment
        where partner_bob_failed_posting=True
        AND invoice_date>=date_trunc('year',current_date)
    order by invoice_date desc
    """
    return db_util.query(query)


def fetch_duplicate_settlement_postings():
    query = f"""
    SELECT
        invoice_date,
        partner_id,
        partner_name,
        invoice_balance,
        invoice_balance_usd,
        company_count,
        bob_company_count,
        bob_invoice_paid_count,
        bob_payment_partner_ledger_total,
        partner_net_after_billing_fee_and_taxes,
        bob_payment_failed_posting_count,
        bob_payment_failed_posting_total,
        bob_with_duplicate_payment_posting,
        ledger_id,
        ledger_transaction_date,
        ledger_description,
        ledger_debit AS settlement_debit,
        ledger_debit_usd AS settlement_debit_usd,
        ledger_duplicate_present
    FROM mart_observability_and_automation.agg_partner_bob_invoice_payment_summary
    WHERE ledger_duplicate_present=TRUE
    AND invoice_date>=date_trunc('year',current_date)
    ORDER BY invoice_date DESC """
    return db_util.query(query)