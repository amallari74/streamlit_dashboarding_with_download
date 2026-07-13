import streamlit as st
import graphviz as gv
from datetime import datetime, timedelta
from diagnostics.models.bob_assessment_models import (
    fetch_bob_assessment_summary_metrics,
    fetch_bob_assessment_overview_details,
    fetch_failed_bob_payment_postings,
    fetch_duplicate_settlement_postings,
)


def render_bob_assessment_information():
    gv_chart = """
    digraph {
        rankdir=TB;
        nodesep=1.2;
        ranksep=0.9;
        node [shape=box, style="rounded,filled", fillcolor=white, fontname=Arial, fontsize=11];
        edge [fontname=Arial, fontsize=10, penwidth=1.2];

        A [label="fact_csv_invoice_row_archive \\(partner)", fillcolor="#24C0FF", fontcolor=black];
        B [label="fact_csv_invoice_row_archive \\(company)", fillcolor="#24C0FF", fontcolor=black];
        C [label="Compare Partner/BOB Invoices against BOB Payments", fillcolor="#FB9D41", fontcolor=black];
        D [label="Fact Ledger (BOB_CUSTOMER_PAYMENT)", fillcolor="#24C0FF", fontcolor=black];
        E [label="Fact Invoice NonVoid", fillcolor="#24C0FF", fontcolor=black];
        F [label="agg_partner_bob_invoice_payment_assessment", fillcolor="#21DE3D", fontcolor=black];
        G [label="Fact Ledger (CHECK_ISSUED)", fillcolor="#24C0FF", fontcolor=black];
        H [label="Fact Invoice NonVoid", fillcolor="#24C0FF", fontcolor=black];
        I [label="agg_partner_bob_invoice_payment_summary", fillcolor="#21DE3D", fontcolor=black];
        J [label="Sum the Agg Assessment Model by partner invoice then compare \\ against the Invoice and Ledger table (settlements)", fillcolor="#FB9D41", fontcolor=black];


        // Organize nodes into ranks for proper layout matching screenshot
        { rank=same; A B D E}
        { rank=same; C}
        { rank=same; F G H}
        { rank=same; I}

        A -> C
        B -> C
        D -> C
        E -> C
        C -> F
        F -> J
        G -> J
        H -> J
        J -> I

subgraph cluster_legend {
  label="Legend";
  style="rounded,dashed"; color=gray70; fontsize=10;

  key1 [label="Fact/Staging", shape=box, style="rounded,filled", fillcolor="#24C0FF"];
  key2 [label="Logic that Compares Multiple Models", shape=box, style="rounded,filled", fillcolor="#FB9D41"];
  key3 [label="Finalized Partner/BOB Models", shape=box, style="rounded,filled", fillcolor="#21DE3D"];

  // keep them on one row and tidy
  key1 -> key2 [style=invis];
  key2 -> key3 [style=invis];
}

    }
    """

    return st.graphviz_chart(gv_chart)

def render_bob_assessment_summary_metrics(start_date, end_date, partner_id=None):
    if start_date and end_date:
        bob_assessment_summary_metrics = fetch_bob_assessment_summary_metrics(start_date, end_date)
        summary_metrics = {
            "partner_name": 'Multiple Partners',
            "company_count": bob_assessment_summary_metrics["company_count"].sum(),
            "bob_company_count": bob_assessment_summary_metrics["bob_company_count"].sum(),
            "bob_invoice_paid_count": bob_assessment_summary_metrics["bob_invoice_paid_count"].sum(),
            "bob_payment_partner_ledger_total": bob_assessment_summary_metrics["bob_payment_partner_ledger_total"].sum(),
            "bob_payment_failed_posting_count": bob_assessment_summary_metrics["bob_payment_failed_posting_count"].sum(),
            "partner_net_after_billing_fee_and_taxes": bob_assessment_summary_metrics["partner_net_after_billing_fee_and_taxes"].sum(),
            "bob_with_duplicate_payment_postings": bob_assessment_summary_metrics["bob_with_duplicate_payment_posting"].sum(),
            "ledger_debit": bob_assessment_summary_metrics["ledger_debit"].sum(),
            "settlement_duplicate_count": bob_assessment_summary_metrics[bob_assessment_summary_metrics["ledger_duplicate_present"] == True].shape[0],

        }
    if partner_id and start_date and end_date:
        summary_metrics = {
            "partner_name": bob_assessment_summary_metrics.loc[bob_assessment_summary_metrics["partner_id"] == partner_id, "partner_name"].iloc[0],
            "company_count": bob_assessment_summary_metrics.loc[bob_assessment_summary_metrics["partner_id"] == partner_id, "company_count"].sum(),
            "bob_company_count": bob_assessment_summary_metrics.loc[bob_assessment_summary_metrics["partner_id"] == partner_id, "bob_company_count"].sum(),
            "bob_invoice_paid_count": bob_assessment_summary_metrics.loc[bob_assessment_summary_metrics["partner_id"] == partner_id, "bob_invoice_paid_count"].sum(),
            "bob_payment_partner_ledger_total": bob_assessment_summary_metrics.loc[bob_assessment_summary_metrics["partner_id"] == partner_id, "bob_payment_partner_ledger_total"].sum(),
            "bob_payment_failed_posting_count": bob_assessment_summary_metrics.loc[bob_assessment_summary_metrics["partner_id"] == partner_id, "bob_payment_failed_posting_count"].sum(),
            "partner_net_after_billing_fee_and_taxes": bob_assessment_summary_metrics.loc[bob_assessment_summary_metrics["partner_id"] == partner_id, "partner_net_after_billing_fee_and_taxes"].sum(),
            "bob_with_duplicate_payment_postings": bob_assessment_summary_metrics.loc[bob_assessment_summary_metrics["partner_id"] == partner_id, "bob_with_duplicate_payment_posting"].sum(),
            "ledger_debit": bob_assessment_summary_metrics.loc[bob_assessment_summary_metrics["partner_id"] == partner_id, "ledger_debit"].sum(),
            "settlement_duplicate_count": bob_assessment_summary_metrics.loc[(bob_assessment_summary_metrics["partner_id"] == partner_id) & (bob_assessment_summary_metrics["ledger_duplicate_present"] == True)].shape[0],
        }
    return summary_metrics

@st.fragment
def render_bob_assessment_overview_details(start_date, end_date, partner_id):
    bob_assessment_overview_details = fetch_bob_assessment_overview_details(start_date, end_date, partner_id)
    return bob_assessment_overview_details

def model_and_logic_information():
    model_information = st.markdown("""
    ### Agg_partner_bob_invoice_payment_assessment
    This model does a comparison of the partner invoice (group by company ID and Invoice Month) then compares it to the 
    the Bill on Behalf invoices which will determine partner margin, sales tax, billing fee and overall net back to the partner. In addition to invoice comparison, 
    the model maps to the partner ledger table to look for the associated BOB_CUSTOMER_PAYMENT to validate the payment was posted. If there are multiple BOB_CUSTOMER_PAYMENT 
    for a given partner, company and invoice ID, then it will reflect as a duplicate payment posting.
    
    #### Data Points 
    - **invoice_date:** invoice month that the partner and company invoices were generated.
    - **partner_id:** partner ID on the invoice
    - **partner_name:** partner name on the invoice
    - **partner_invoice_id:** The alternate ID for the partner invoice. This is reflected on the PDF file. 
    - **partner_invoice_status:** The status of the partner invoice.
    - **company_id:** Company ID that is on the partner invoice. 
    - **company_name:** Company name that is on the partner invoice.
    - **invoice_type:** If the company ID has a matching BOB invoice ID, then it will reflect 'Company Invoice'. If not the column will reflect 'Non-BOB' since partners can have a mix of both on their invoices.
    - **bob_invoice_id:** BOB invoice ID that is on the partner invoice.
    - **bob_invoice_status:** The status of the BOB invoice.
    - **partner_invoice_partner_total:** The total amount of the partner invoice.
    - **partner_billing_fee:** The billing fee of the partner invoice.
    - **partner_surcharge_total:** The surcharge total of the partner invoice. This is reflected as a seperate line item on the partner invoice without a company name. 
    - **bob_customer_total_with_tax:** Sum of the customer total with tax from the BOB invoice
    - **partner_net_after_customer_total:** Customer Total with Tax - Partner Total (partner invoice)
    - **partner_net_after_billing_fee_and_taxes:** Customer total - Partner Total (partner invoice) - Billing Fee
    - **bob_tax_witholding:** The tax total from the BOB invoice
    - **bob_payment_posting_date:** This pulles from the associated partner ledger where type='BOB_CUSTOMER_PAYMENT' to validate the payment was posted
    - **bob_payment_credit:** Total of the BOB_CUSTOMER_PAYMENT
    - **bob_payment_id:** The ID from the ledger of the BOB_CUSTOMER_PAYMENT
    - **bob_payment_description:** The description of the BOB payment.
    - **bob_payment_duplicate_count:** The duplicate count of the BOB payment.
    - **expected_partner_bob_ledger_payment:** The expected partner BOB ledger payment.
    - **partner_bob_failed_posting:** Whether the partner BOB failed posting.


    ### Agg_partner_bob_invoice_payment_summary
    This model sums from the agg_partner_bob_invoice_payment_assessment model to provide a summary of the partner invoice. This will also map to the ledger table to
    look to verify if the CHECK_ISSUED is posted on the partner ledger for settlements. If there are multiple CHECK_ISSUED for a given partner and invoice month then
    it will reflect as a duplicate settlement posting.
    - **invoice_date:** invoice month that the partner and company invoices were generated.
    - **partner_id:** partner ID on the invoice
    - **partner_name:** partner name on the invoice
    - **invoice_balance:** The total amount of the partner invoice.
    - **invoice_balance_usd:** The total amount of the partner invoice in USD.
    - **company_count:* Total number of companies on the partner invoice, including both non-BOB and BOB companies.
    - **bob_company_count:** The number of companies on the BOB invoice.
    - **bob_invoice_paid_count:** The number of invoices paid on the BOB invoice.
    - **bob_payment_partner_ledger_total:** The total amount BOB_CUSTOMER_PAYMENT posted on the partner ledger.
    - **partner_net_after_billing_fee_and_taxes:** The net amount after the billing fee and taxes of the partner invoice.
    - **bob_payment_failed_posting_count:** The number of failed payment postings on the BOB invoice.
    - **bob_payment_failed_posting_total:** The total amount of the failed payment postings on the BOB invoice.
    - **bob_with_duplicate_payment_posting:** The number of duplicate payment postings on the BOB invoice.
    - **ledger_id:** The ID from the ledger of the CHECK_ISSUED.
    - **ledger_transaction_date:** The transaction date of the CHECK_ISSUED.
    - **ledger_description:** The description of the CHECK_ISSUED.
    - **ledger_debit:** The debit amount of the CHECK_ISSUED.
    - **ledger_debit_usd:** The debit amount of the CHECK_ISSUED in USD.
    - **ledger_duplicate_present:** Whether the CHECK_ISSUED is a duplicate posting.
    """, unsafe_allow_html=True)

    return model_information

def csv_export_file(df, file_name, partner_name=None):
    if partner_name:
        file_name = f"{file_name}_{partner_name}"
    else:
        file_name = file_name
    today_str = datetime.now().strftime("%Y-%m-%d")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.markdown(
        """
        <style>
        div[data-testid="stDownloadButton"] > button {
            background-color: #058ef0; /* Light blue */
            color: #000305;            /* Dark blue text */
            border: 1px solid #000305;
            font-weight: 700;         /* Bold label */
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background-color: #058ef0;
            color: #00070a;
            border-color: #64b5f6;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.download_button(
        label=f"Download {file_name}.csv",
        data=csv_bytes,
        file_name=f"{file_name}_{today_str}.csv",
        mime="text/csv"
    )



def render_bob_assessment_monitoring():
    st.title("Bill-On-Behalf Assessment") 
    st.markdown("""
    <div style="text-align: left; font-size: 0.7em; opacity: 0.5; margin-top: 20px;">Overview Metrics built by Isaac Buck and the OIA Team</div>
    """, unsafe_allow_html=True)

    st.divider()

    colfilter1, colfilter2, colfilter3 = st.columns(3)
    with colfilter1:
        start_date = (lambda d: d.replace(day=1))(st.date_input(
            "Select Start Date", 
            value=datetime.now().date(), format="YYYY-MM-DD"))
    
    with colfilter2:
        end_date = (lambda d: d.replace(day=1))(st.date_input(
            "Select End Date",
            value=datetime.now().date(), format="YYYY-MM-DD"))
    with colfilter3:
        partner_id_str = st.text_input("Input Partner ID", key="selected_partner_id_input", value="", placeholder="e.g. 12345")
        selected_partner_id = int(partner_id_str) if partner_id_str.strip().isdigit() else None
    
    # Call render_bob_assessment_summary_metrics to get overview metrics
    if start_date and end_date: 
        overview_metrics = render_bob_assessment_summary_metrics(start_date, end_date)
    if start_date and end_date and selected_partner_id:
        overview_metrics = render_bob_assessment_summary_metrics(start_date, end_date, selected_partner_id)

    col1, col2, col3, col4, col5 = st.columns(5)
    col6, col7, col8, col9, col10 = st.columns(5)
    with col1:
        st.metric("Partner Name", overview_metrics.get("partner_name", "-"))
    with col2:
        st.metric("Total Companies", overview_metrics.get("company_count", 0))
    with col3: 
        st.metric("BOB Companies", overview_metrics.get("bob_company_count", 0))
    with col4:
        st.metric("BOB Invoice Paid Count", overview_metrics.get('bob_invoice_paid_count', 0))
    with col5:
        st.metric("BOB Payment Amount (Partner Ledger)", f"${overview_metrics.get('bob_payment_partner_ledger_total', 0):,.2f}")
    with col6:
        st.metric("BOB Failed Payment Posting Count", f"{int(overview_metrics.get('bob_payment_failed_posting_count', 0) or 0):,}")
    with col7:
        st.metric("Partner Net (after billing fee and taxes)", f"${overview_metrics.get('partner_net_after_billing_fee_and_taxes', 0):,.2f}")
    with col8:
        st.metric("BOB With Duplicate Payment Postings", overview_metrics.get("bob_with_duplicate_payment_postings", 0))
    with col9:
        st.metric("Settlement Total", f"${overview_metrics.get('ledger_debit', 0):,.2f}")
    with col10:
        st.metric("Settlement Duplicate Count", overview_metrics.get("settlement_duplicate_count", 0))


    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["Modeling and Logic Information","Partner and BOB Overview Detail","Paid BOB Invoices Failed Payment Posting","Duplicate Settlement Postings"])
    with tab1:
        with st.expander("Modeling and Logic Information", expanded=False):
            model_and_logic_information()
        with st.expander("Data Flow Diagram", expanded=False):
            render_bob_assessment_information()

    with tab2:
        if start_date is not None and end_date is not None and selected_partner_id is not None:
            bob_assessment_overview_details = render_bob_assessment_overview_details(start_date, end_date, selected_partner_id)
            csv_export_file(bob_assessment_overview_details, "bob_assessment_overview_details_for", partner_name=overview_metrics.get("partner_name", ""))
            st.dataframe(
                bob_assessment_overview_details,
                hide_index=True,
                column_config={
                    "partner_id" : st.column_config.NumberColumn(format="%d"),
                    "company_id" : st.column_config.NumberColumn(format="%d"),
                    "partner_invoice_partner_total" : st.column_config.NumberColumn(format="$%.2f"),
                    "partner_billing_fee" : st.column_config.NumberColumn(format="$%.2f"),
                    "partner_surcharge_total" : st.column_config.NumberColumn(format="$%.2f"),
                    "bob_customer_total_with_tax" : st.column_config.NumberColumn(format="$%.2f"),
                    "partner_net_after_customer_total" : st.column_config.NumberColumn(format="$%.2f"),
                    "partner_net_after_billing_fee_and_taxes" : st.column_config.NumberColumn(format="$%.2f"),
                    "bob_tax_witholding": st.column_config.NumberColumn(format="$%.2f"),
                    "bob_payment_id" : st.column_config.NumberColumn(format="%d"),
                    "bob_payment_credit" : st.column_config.NumberColumn(format="$%.2f"),
                    "bob_payment_posting_date" : st.column_config.DateColumn(format="YYYY-MM-DD"),
                    "bob_payment_description" : st.column_config.TextColumn(),
                    "bob_payment_duplicate_count" : st.column_config.NumberColumn(format="%d"),
                    "expected_partner_bob_ledger_payment" : st.column_config.NumberColumn(format="$%.2f"),
                }
            )
        else:
            st.error("Please select a date and partner id to view the overview details")

    with tab3:
        st.markdown("""
        #### Failed BOB Payment Postings
        This section shows all the instances where a BOB invoice is paid but there is not an associated BOB_CUSTOMER_PAYMENT posted on the partner ledger
        from the current year. To verify these are duplicated and need remediation, please navigate to the Platform with the partner ID and search the 
        ledger table for CHECK_ISSUED for the invoice month in question. 
        """, unsafe_allow_html=True)
        st.divider()
        failed_bob_payment_postings = fetch_failed_bob_payment_postings()
        csv_export_file(failed_bob_payment_postings, "failed_bob_payment_postings")
        st.dataframe(
            failed_bob_payment_postings,
            hide_index=True,
            column_config={
                "partner_id" : st.column_config.NumberColumn(format="%d"),
                    "company_id" : st.column_config.NumberColumn(format="%d"),
                    "partner_invoice_partner_total" : st.column_config.NumberColumn(format="$%.2f"),
                    "partner_billing_fee" : st.column_config.NumberColumn(format="$%.2f"),
                    "partner_surcharge_total" : st.column_config.NumberColumn(format="$%.2f"),
                    "bob_customer_total_with_tax" : st.column_config.NumberColumn(format="$%.2f"),
                    "partner_net_after_customer_total" : st.column_config.NumberColumn(format="$%.2f"),
                    "partner_net_after_billing_fee_and_taxes" : st.column_config.NumberColumn(format="$%.2f"),
                    "bob_tax_witholding": st.column_config.NumberColumn(format="$%.2f"),
                    "bob_payment_id" : st.column_config.NumberColumn(format="%d"),
                    "bob_payment_credit" : st.column_config.NumberColumn(format="$%.2f"),
                    "bob_payment_posting_date" : st.column_config.DateColumn(format="YYYY-MM-DD"),
                    "bob_payment_description" : st.column_config.TextColumn(),
                    "bob_payment_duplicate_count" : st.column_config.NumberColumn(format="%d"),
                    "expected_partner_bob_ledger_payment" : st.column_config.NumberColumn(format="$%.2f"),
            }
        )
    with tab4:
        st.markdown("""
            #### Duplicate Settlement Postings
            This section shows all the instances where a CHECK_ISSUED is posted on the partner ledger more than once for a given partner and invoice month. To verify these are duplicated and need remediation, please navigate to the Platform with the partner ID and search the 
            ledger table for CHECK_ISSUED for the invoice month in question. 
        """, unsafe_allow_html=True)
        st.divider()
        duplicate_settlement_postings = fetch_duplicate_settlement_postings()
        csv_export_file(duplicate_settlement_postings, "duplicate_settlement_postings")
        st.dataframe(
            duplicate_settlement_postings,
            hide_index=True,
            column_config={
                "invoice_date" : st.column_config.DateColumn(format="YYYY-MM-DD"),
                "partner_id" : st.column_config.NumberColumn(format="%d"),
                "partner_name" : st.column_config.TextColumn(),
                "invoice_balance" : st.column_config.NumberColumn(format="$%.2f"),
                "invoice_balance_usd" : st.column_config.NumberColumn(format="$%.2f"),
                "company_count" : st.column_config.NumberColumn(format="%d"),
                "bob_company_count" : st.column_config.NumberColumn(format="%d"),
                "bob_invoice_paid_count" : st.column_config.NumberColumn(format="%d"),
                "bob_payment_partner_ledger_total": st.column_config.NumberColumn(format="$%.2f"),
                "partner_net_after_billing_fee_and_taxes" : st.column_config.NumberColumn(format="$%.2f"),
                "bob_payment_failed_posting_count" : st.column_config.NumberColumn(format="%d"),
                "bob_payment_failed_posting_total" : st.column_config.NumberColumn(format="$%.2f"),
                "bob_with_duplicate_payment_posting" : st.column_config.NumberColumn(format="%d"),
                "ledger_id" : st.column_config.NumberColumn(format="%d"),
                "ledger_transaction_date" : st.column_config.DateColumn(format="YYYY-MM-DD"),
                "settlement_debit" : st.column_config.NumberColumn(format="$%.2f"),
                "settlement_debit_usd" : st.column_config.NumberColumn(format="$%.2f"),
            }
        )
if __name__ == "__page__":
    render_bob_assessment_monitoring()