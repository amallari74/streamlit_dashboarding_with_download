import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta, date
from utils import db_util, auth_util
from router.roles import DIAGNOSTICS_ROLES as ROLES
from diagnostics.models.transaction_model import fetch_duplicate_cira_line_items, fetch_missing_subscriptions_invoice_line_items, fetch_missing_subscription_invoice_line_summary
from diagnostics.components.ledger_file_generator import generate_ledger_data
from diagnostics.components.order_manager_file_generator import generate_order_manager_file
from diagnostics.components.file_batch_processor import batch_process_dataframe, save_df_as_xls
import os
import io
import zipfile
from pathlib import Path


def process_date(input_date, get_first_day=True):
    if get_first_day:
        input_date = input_date.replace(day=1)
    return input_date.strftime('%Y-%m-%d')

@st.cache_data(ttl=3600) 
def duplicate_invoice_line_items(input_date):
    try:
        if isinstance(input_date, str):
            input_date = datetime.strptime(input_date, '%Y-%m-%d').date()
            
        with st.spinner("🔄 Fetching duplicate invoices..."):
            invoice_duplicates_df = fetch_duplicate_cira_line_items(input_date)
        
        if invoice_duplicates_df.empty:
            return invoice_duplicates_df

        st.balloons()
        return invoice_duplicates_df
        
    except Exception as e:
        st.error(f"Error fetching duplicate CIRA line items: {str(e)}")
        return pd.DataFrame()
    
@st.cache_data(ttl=3600)
def missing_subscriptions_invoice_line_items(input_date, cira_status, prorate_status=None, ledger_status=None, omt_subscription_match_status=None, omt_prorate_match_status=None, mt_subscription_match_status=None, mt_prorate_match_status=None):
    """
    Fetch and process missing subscriptions invoice line items for the given date range
    """
    try:
        with st.spinner("🔄 Fetching missing subscription data..."):
            invoice_missing_df = fetch_missing_subscriptions_invoice_line_items(input_date, cira_status, prorate_status, ledger_status, omt_subscription_match_status, omt_prorate_match_status, mt_subscription_match_status, mt_prorate_match_status)
        
        if invoice_missing_df.empty:
            st.warning(f"No missing subscription data found for the selected date with Subscription status: {cira_status}, Prorate Status: {prorate_status}, Ledger Status: {ledger_status}")
            return pd.DataFrame()
        return invoice_missing_df
        
    except Exception as e:
        st.error(f"❌ Error fetching missing subscription data: {str(e)}")
        raise Exception(f"Failed to load missing subscription data: {str(e)}")
    
@st.cache_data(ttl=3600)
def missing_subscription_invoice_line_summary(input_date):
    """
    Fetch and process missing subscription invoice line summary for the given date range
    """
    try:
        with st.spinner("🔄 Fetching missing subscription summary data..."):
            missing_subscription_invoice_summary = fetch_missing_subscription_invoice_line_summary(input_date)
    
        if missing_subscription_invoice_summary.empty:
            st.warning(f"No missing subscription summary data found for the selected date: {input_date}")
            return pd.DataFrame()
        return missing_subscription_invoice_summary
    except Exception as e:
        st.error(f"❌ Error fetching missing subscription summary data: {str(e)}")
        raise Exception(f"Failed to load missing subscription summary data: {str(e)}")


def render_flow_chart():
    """Render the duplicate invoice flow chart using Graphviz"""
    graphviz_chart = """
    digraph {
        rankdir=TB;
        node [shape=box, style="rounded,filled", fillcolor=white, fontname=Arial];
        edge [fontname=Arial];

        A [label="Fact Subscription Modification", fillcolor="#03b1fc", fontcolor=white];
        B [label="Order Manager Transaction (Raw)", fillcolor="#03b1fc", fontcolor=white];
        C [label="Fact Order Manager Transaction", fillcolor="#03b1fc", fontcolor=white];
        D [label="Fact CSV Invoice Row Archive", fillcolor="#03b1fc", fontcolor=white];
        E [label="Fact Order Manager Transaction CIRA Duplicates", fillcolor="#19b521", fontcolor=white];
        F [label="Is There a Duplicate?", shape=diamond];

        D -> E [label="Combine Fact Order Manager with Fact CIRA by completed_line_item_id"];
        A -> C [label="Combine Subscription/CLI Data with Order Manager Transaction"];
        B -> C ;
        
        C -> E [label="CSV Invoice Row Archive"];
        E -> F [label="Is There a Duplicate?"];
        F -> H [label="No"];
        F -> G [label="Yes"];
        G [label="Create Ledger Upload File", fillcolor="#19b521", fontcolor=white];
        H [label="Not Pulled Back in the Report", fillcolor="#19b521", fontcolor=white];


    }
    """
    return st.graphviz_chart(graphviz_chart)

def render_missing_subscriptions_on_invoice_chart():
    invoice_subscription_chart = """
    digraph {
        rankdir=TB;
        nodesep=0.9;  // More spacing between nodes horizontally
        ranksep=0.7;  // More spacing between ranks vertically
        node [shape=box, style="rounded,filled", fillcolor=white, fontname=Arial, fontsize=11];
        edge [fontname=Arial, fontsize=10, penwidth=1.2];

        // Blue boxes - standalone fact/staging tables
        A [label="Agg Subscription Monthly", fillcolor="#03b1fc", fontcolor=white];
        B [label="Fact Subscription Modification", fillcolor="#03b1fc", fontcolor=white];
        C [label="Fact CSV Invoice Row Archive", fillcolor="#03b1fc", fontcolor=white];
        M [label="Int Subscription Joined", fillcolor="#03b1fc", fontcolor=white];

        // Green boxes - joined models
        L [label="Agg Subscription Monthly Projection", fillcolor="#19b521", fontcolor=white];
        K [label="Fact Subscription Monthly Projection", fillcolor="#19b521", fontcolor=white];

        
        // Diamonds - decision points - with adjusted width/height to match screenshot
        H [label="Subscription Info\\nper Month", shape=diamond, width=2.0, height=1.0, style="filled"];
        I [label="Aggregates Prorates\\nby Subscription and Invoice Month", shape=diamond, width=2.3, height=1.2, style="filled"];
        J [label="Aggregates Full Term\\ncharges by Subscription and Invoice Month", shape=diamond, width=2.3, height=1.2, style="filled"];

        // Organize nodes into ranks for proper layout matching screenshot
        { rank=same; A M}
        { rank=same; B C}
        { rank=same; H I J}
      
        // Flow connections - modified to remove E and F
        A -> B
        B -> H [label="Calculate estimated billing renewal (transaction_month)"]
        H -> K
        M -> C
        C -> I 
        C -> J
        I -> K
        J -> K
        K -> L
    }
    """
    return st.graphviz_chart(invoice_subscription_chart)

def create_subscription_treemap(df):
    """
    Create a hierarchical treemap visualization for subscription invoice line items
    that drills down from partner to company to product
    """
    if df.empty:
        return None
    treemap_df = df.copy()
    
    agg_df = treemap_df.groupby(
        ['partner_name', 'company_name', 'product_name']
    ).agg(
        total_amount=('missed_revenue_usd', 'sum'),
        count=('original_subscription_id', 'count')
    ).reset_index()
    
    agg_df['partner_label'] = agg_df['partner_name'] + '<br>($' + agg_df.groupby('partner_name')['total_amount'].transform('sum').round(2).astype(str) + ')'
    agg_df['company_label'] = agg_df['company_name'] + '<br>($' + agg_df.groupby(['partner_name', 'company_name'])['total_amount'].transform('sum').round(2).astype(str) + ')'
    agg_df['product_label'] = agg_df['product_name'] + '<br>($' + agg_df['total_amount'].round(2).astype(str) + ', ' + agg_df['count'].astype(str) + ' subs)'
    
    fig = px.treemap(
        agg_df,
        path=['partner_label', 'company_label', 'product_label'],
        values='total_amount',
        color='total_amount',
        color_continuous_scale='Plasma', # Different color scheme to distinguish from duplicate treemap
        hover_data=['count'],
        title=f'Subscription Data by Partner → Company → Product',
    )
    
    fig.update_layout(
        margin=dict(t=50, l=25, r=25, b=25),
        coloraxis_colorbar=dict(
            title="Revenue Impact ($)",
            thicknessmode="pixels", thickness=15,
            lenmode="pixels", len=300,
        ),
        height=600
    )
    
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>💰 Revenue Impact: $%{value:,.2f}<br>🔢 Subscriptions: %{customdata[0]}<extra></extra>'
    )
    
    return fig

@st.fragment
def render_missing_subscriptions_info(selected_date, formatted_date):
    st.markdown(f'*__Missing Subscriptions on Invoices for {formatted_date}__*')
    st.warning("This is the first iteration of this model only capturing full term charges (no prorates). Please verify this data before any final reporting or actions are decided If you find issues please escalate to the OIA Support channel in Slack")

    missing_subscription_filter_dictionary = {
            "Missing Subscriptions in OMT (No Prorates and No Service Charges)": {
                "cira_status": "Missing",
                "prorate_status": "No Prorates",
                "ledger_status": "No Service Charges",
                "omt_subscription_match_status": "False",
                "omt_prorate_match_status": "False",
                "mt_subscription_match_status": "False",
                "mt_prorate_match_status": "False"
            }, 
            "Missing Subscriptions in OMT (With Prorates but No Service Charges)": {
                "cira_status": "Missing",
                "prorate_status": "Matched Prorate",
                "ledger_status": "No Service Charges",
                "omt_subscription_match_status": "False",
                "omt_prorate_match_status": "True",
                "mt_subscription_match_status": "False",
                "mt_prorate_match_status": "False"
            }, 
            "Missing Subscriptions in CIRA but Matched in OMT (No Prorates and No Service Charges)": {
                "cira_status": "Missing",
                "prorate_status": "No Prorates",
                "ledger_status": "No Service Charges",
                "omt_subscription_match_status": "True",
                "omt_prorate_match_status": "False",
                "mt_subscription_match_status": "False",
                "mt_prorate_match_status": "False"
            }, 
            "Missing Subscriptions in CIRA but Matched to OMT (With Prorates but No Service Charges)": {
                "cira_status": "Missing",
                "prorate_status": "Matched Prorate",
                "ledger_status": "No Service Charges",
                "omt_subscription_match_status": "True",
                "omt_prorate_match_status": "True",
                "mt_subscription_match_status": "False",
                "mt_prorate_match_status": "False"
            }
        }

    filter_column1, filter_column2 = st.columns(2)
    with filter_column1:
        missing_subscription_filter_options = st.selectbox("Subscription Filter Options", options=list(missing_subscription_filter_dictionary.keys()), index=0)
    with filter_column2: 
        st.markdown("""
                <style>
                /* Match st.download_button styles for all buttons */
                div[data-testid="stButton"] > button,
                div[data-testid="stDownloadButton"] > button {
                width: 100%;
                background-color: #058ef0;   /* same as your download button */
                color: #000305;
                border: 1px solid #000305;
                border-radius: 4px;
                height: 38px;
                font-weight: 700;
                }
                div[data-testid="stButton"] > button:hover,
                div[data-testid="stDownloadButton"] > button:hover {
                background-color: #058ef0;
                color: #00070a;
                border-color: #64b5f6;
                }
                </style>
                """, unsafe_allow_html=True)
        run_clicked = st.button("Run Report", type="primary")
    if run_clicked:
        try: 
            missing_subs_filter_dict = missing_subscription_filter_dictionary[missing_subscription_filter_options]
            sub_cira_missing_df = missing_subscriptions_invoice_line_items(selected_date, 
                missing_subs_filter_dict["cira_status"], 
                missing_subs_filter_dict["prorate_status"], 
                missing_subs_filter_dict["ledger_status"], 
                missing_subs_filter_dict["omt_subscription_match_status"], 
                missing_subs_filter_dict["omt_prorate_match_status"], 
                missing_subs_filter_dict["mt_subscription_match_status"], 
                missing_subs_filter_dict["mt_prorate_match_status"])

            if not sub_cira_missing_df.empty:
                with st.expander("**Additional Filters**"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        partners = ["All"] + sorted(list(sub_cira_missing_df['partner_name'].unique()))
                        selected_partner = st.selectbox("Partner", partners, key="tab1_partner")
                    with col2:
                        companies = ["All"] + sorted(list(sub_cira_missing_df['company_name'].unique()))
                        selected_company = st.selectbox("Company", companies, key="tab1_company")
                    with col3:
                        products = ["All"] + sorted(list(sub_cira_missing_df['product_name'].unique()))
                        selected_product = st.selectbox("Product", products, key="tab1_product")
                    col4, col5, col6 = st.columns(3)
                    with col4:
                        terms = ["All"] + sorted(list(sub_cira_missing_df['successor_term'].unique()))
                        selected_term = st.multiselect("Term", terms, key="tab1_term") # Changed name from selected_status
                    with col5:
                        vendors = ["All"] + sorted(list(sub_cira_missing_df['vendor'].unique()))
                        select_vendor = st.selectbox("Vendor", vendors, key="tab1_vendor")
                    with col6:
                        segments = ["All"] + sorted(list(sub_cira_missing_df['partner_segment'].unique()))
                        selected_partner_segment = st.selectbox("Partner Segment", segments, key="tab1_segment")
                    col7, col8, col9 = st.columns(3)                    
                    with col7:
                        countries = ["All"] + sorted(list(sub_cira_missing_df['partner_country'].unique()))
                        selected_partner_country = st.selectbox("Partner Country", countries, key="tab1_country")
                    with col8:
                        regions = ["All"] + sorted(list(sub_cira_missing_df['partner_region'].unique()))
                        selected_region = st.selectbox("Filter by Region", regions, key="tab1_region")
                    with col9:
                        revenue_options = ["All", "No Revenue Impact", "Revenue Impact"]
                        selected_revenue_filter = st.selectbox("Filter by Revenue Impact", revenue_options, key="tab1_revenue")

                    col10, col11, col12 = st.columns(3)
                    with col10:
                        modified_users = ["All"] + sorted(list(sub_cira_missing_df['modified_by_pax8'].unique()))
                        selected_modified_user = st.selectbox("Modified by Pax8 User", modified_users, key="tab1_modified_user")
                    with col11:
                        account_types = ["All"] + sorted(list(sub_cira_missing_df['impacted_audience'].unique()))
                        selected_account_type = st.selectbox("Partner vs BOB", account_types, key="tab1_account_type")

                filtered_df = sub_cira_missing_df.copy()
                if selected_partner != "All":
                    filtered_df = filtered_df[filtered_df['partner_name'] == selected_partner]
                if selected_company != "All":
                    filtered_df = filtered_df[filtered_df['company_name'] == selected_company]
                if selected_product != "All":
                    filtered_df = filtered_df[filtered_df['product_name'] == selected_product]
                # Term multiselect: when empty or contains "All", skip filtering
                if isinstance(selected_term, list) and selected_term:
                    terms_to_filter = [t for t in selected_term if t != "All"]
                    if terms_to_filter:
                        filtered_df = filtered_df[filtered_df['successor_term'].isin(terms_to_filter)]
                if select_vendor != "All":
                    filtered_df = filtered_df[filtered_df['vendor'] == select_vendor]
                if selected_partner_segment != "All":
                    filtered_df = filtered_df[filtered_df['partner_segment'] == selected_partner_segment]
                if selected_partner_country != "All":
                    filtered_df = filtered_df[filtered_df['partner_country'] == selected_partner_country]
                if selected_region != "All":
                    filtered_df = filtered_df[filtered_df['partner_region'] == selected_region]
                if selected_revenue_filter != "All":
                    if selected_revenue_filter == "No Revenue Impact":
                        filtered_df = filtered_df[filtered_df['missed_revenue_usd'] == 0]
                    elif selected_revenue_filter == "Revenue Impact":
                        filtered_df = filtered_df[filtered_df['missed_revenue_usd'] != 0]
                if selected_modified_user != "All":
                    filtered_df = filtered_df[filtered_df['modified_by_pax8'] == selected_modified_user]
                if selected_account_type != "All":
                    filtered_df = filtered_df[filtered_df['impacted_audience'] == selected_account_type]



                if not filtered_df.empty:
                    ledger_description = st.text_input("Enter the description that will show up on the ledger upload. This will show up as (Description) for Company: (company_name) and Product: (product_name) at a quantity of (quantity),",
                                                       placeholder=f"Missing subscription charges for {selected_date} invoice",
                                                       key="tab1_ledger_desc")
                else:
                    ledger_description = "" 

                report1, report2, report3 = st.columns(3)

                with report1:
                    st.download_button(
                        label="Download Detailed Report",
                        data=filtered_df.to_csv(index=False),
                        file_name=f"missing_subscriptions_on_invoices_{selected_date}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        help="Click to download the filtered data below",
                        key="tab1_download_detail"
                    )

                with report2:
                    if not filtered_df.empty:
                        order_manager_upload_df = generate_order_manager_file(df=filtered_df)
                        if not order_manager_upload_df.empty:

                             # Get the default downloads directory using pathlib
                            downloads_dir = str(Path.home() / "Downloads")
                            output_dir = os.path.join(downloads_dir, "Order_Manager_Upload_Files")
                            base_filename = f"Order_Manager_File_{formatted_date}"
                            
                            with st.expander("Order Manager File Options", expanded=True):
                                col1, col2 = st.columns(2)
                                with col1:
                                    split_files = st.checkbox("Split into multiple files", value=True, 
                                                             help="When checked, will split the data into multiple files with the specified rows per file")
                                with col2:
                                    max_rows = len(order_manager_upload_df) if not order_manager_upload_df.empty else 10000
                                    # Set min_value to 1 and default_rows to at most max_rows to prevent the error
                                    min_value = 1
                                    default_rows = min(1000, max_rows)  # Default to 1000 or max_rows if smaller
                                    
                                    # Ensure the value is never greater than max_rows
                                    rows_per_file = st.number_input(
                                        "Rows per file", 
                                        min_value=min_value, 
                                        max_value=min(10000, max_rows), 
                                        value=default_rows,
                                        step=100,  # Use a fixed step value for clarity and simplicity
                                        help="Number of rows to include in each file when splitting",
                                        disabled=not split_files
                                    )
                            
                            if not order_manager_upload_df.empty:
                                try:
                                    files = batch_process_dataframe(
                                        df=order_manager_upload_df,
                                        base_filename=base_filename,
                                        batch_size=rows_per_file if split_files else len(order_manager_upload_df)
                                    )
                                    
                                    if files:
                                        zip_buffer = io.BytesIO()
                                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                            for filename, file_data in files:
                                                zip_file.writestr(f"Order_Manager_Upload_Files/{filename}", file_data)
                                        
                                        # Reset buffer position
                                        zip_buffer.seek(0)
                                        
                                        button_label = "📥 Generate & Download Order Manager Files"
                                        if split_files:
                                            button_help = f"Click to download {len(files)} files split into batches of {rows_per_file} rows"
                                        else:
                                            button_help = "Click to download the Order Manager file"
                                        
                                        if st.download_button(
                                            label=button_label,
                                            data=zip_buffer.getvalue(),
                                            file_name=f"Order_Manager_Files_{datetime.now().strftime('%Y-%m-%d')}.zip",
                                            mime="application/zip",
                                            help=button_help,
                                            use_container_width=True,
                                            key="download_batch_files_button"
                                        ):
                                            st.success(f"✅ Successfully generated and downloaded {len(files)} files!")
                                    else:
                                        st.error("❌ No files were generated. Check the logs for details.")
                                except Exception as e:
                                    st.error(f"❌ Failed to generate files: {str(e)}")

                with report3:
                    if ledger_description and not filtered_df.empty: 
                        try:
                            missing_subscriptions_ledger_formatted_df = generate_ledger_data(
                                df=filtered_df,
                                type_column='impacted_audience',
                                partner_identifier='Partner',
                                company_identifier='Bill on Behalf',
                                partner_id_col='partner_id', 
                                company_id_col='company_id', 
                                subscription_id_col='max_subscription_id_transaction_month',
                                partner_cost_col='missed_revenue_non_usd',
                                company_cost_col='missed_revenue_non_usd',
                                company_name_col='company_name',
                                product_name_col='product_name',
                                quantity_col='quantity',
                                start_period_col='estimated_billing_start_period',
                                end_period_col='estimated_billing_end_period',
                                product_id_col='product_id', 
                                description_col=ledger_description,
                                calculation_method='missed_billing'
                            )

                            if not missing_subscriptions_ledger_formatted_df.empty:
                                ledger_csv_data = missing_subscriptions_ledger_formatted_df.to_csv(index=False).encode('utf-8')

                                st.download_button(
                                    label="Download Ledger File",
                                    data=ledger_csv_data,
                                    file_name=f"Missing Subscriptions on Invoices for {formatted_date}.csv",
                                    mime="text/csv",
                                    use_container_width=True,
                                    key="download_missing_subscriptions_ledger_button_tab1", 
                                    help="Click to download the generated ledger file for missing subscriptions"
                                )
                            else:
                                st.warning("Ledger file could not be generated (empty result).")

                        except Exception as e:
                            st.error(f"Error generating ledger file: {e}")
                    elif ledger_description and filtered_df.empty:
                        st.warning("No data selected to generate ledger file.")

                st.divider()

                if filtered_df.empty:
                    ledger_description = None
                    st.warning("No data available to display in the table. Please adjust your filters to include some data.")
                else:
                    st.dataframe(
                        filtered_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "partner_id": st.column_config.NumberColumn(format="%d"),
                            "company_id": st.column_config.NumberColumn(format="%d"),
                            "product_id": st.column_config.NumberColumn(format="%d"),
                            "original_subscription_id": st.column_config.NumberColumn(format="%d"),
                            "original_subscription_guid": st.column_config.TextColumn(),
                            "max_subscription_id_transaction_month": st.column_config.NumberColumn(format="%d"),
                            "min_subscription_id_transaction_month": st.column_config.NumberColumn(format="%d"),
                            "successor_completed_line_item_id": st.column_config.NumberColumn(format="%d"),
                            "prior_completed_line_item_id": st.column_config.NumberColumn(format="%d"),
                            "cira_record_id": st.column_config.NumberColumn(format="%d"),
                            "cira_invoice_id": st.column_config.NumberColumn(format="%d"),
                            "cira_completed_line_item_id": st.column_config.NumberColumn(format="%d"),
                            "cira_invoice_date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                            "cira_invoice_number": st.column_config.TextColumn(),
                            "cira_invoice_type": st.column_config.TextColumn(),
                            "partner_buy_rate": st.column_config.NumberColumn(format="$%.2f"),
                            "actual_retail_price": st.column_config.NumberColumn(format="$%.2f"),
                            "wholesale_buy_rate": st.column_config.NumberColumn(format="$%.2f"),
                            "cira_partner_unit_cost": st.column_config.NumberColumn(format="$%.2f"),
                            "cira_partner_cost_total": st.column_config.NumberColumn(format="$%.2f"),
                            "cira_customer_unit_cost": st.column_config.NumberColumn(format="$%.2f"),
                            "cira_customer_cost_total": st.column_config.NumberColumn(format="$%.2f"),
                            "missed_revenue_non_usd": st.column_config.NumberColumn(format="$%.2f"),
                            "missed_revenue_usd": st.column_config.NumberColumn(format="$%.2f"),
                            "estimated_billing_renewal_date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                            "cira_prorate_total": st.column_config.NumberColumn(format="$%.2f"),
                            "cira_prorate_count": st.column_config.NumberColumn(format="%d"),
                            "cira_prorate_match_status": st.column_config.TextColumn(),
                            "net_subscription_and_prorate_non_usd": st.column_config.NumberColumn(format="$%.2f"),
                            "net_subscription_and_prorate_usd": st.column_config.NumberColumn(format="$%.2f"),
                            "app_user_partner_id": st.column_config.NumberColumn(format="%d"),
                            "app_user_company_id": st.column_config.NumberColumn(format="%d"),
                            "app_user_name": st.column_config.TextColumn(),
                            "impacted_audience": st.column_config.TextColumn(),
                            "ledger_charge_match_status": st.column_config.TextColumn(),
                            "service_charge_amount": st.column_config.NumberColumn(format="$%.2f"),
                            "service_charge_amount_usd": st.column_config.NumberColumn(format="$%.2f"),
                            "estimated_billing_start_period": st.column_config.DateColumn(format="YYYY-MM-DD"),
                            "estimated_billing_end_period": st.column_config.DateColumn(format="YYYY-MM-DD")
                    }
                )
                st.success(f"📋 Found {len(sub_cira_missing_df):,} total missing subscription records" +
                          (f" (Filtered: {len(filtered_df):,})" if len(filtered_df) != len(sub_cira_missing_df) else ""))
            else:
                st.info("No missing subscription data found for the selected date.")
        except Exception as e:
            st.error(f"❌ Error processing data for tab 1: {str(e)}") # More specific error
    else:
        st.info("👆 Select a status above to view subscription data")

@st.fragment
def render_duplicate_invoice_line_items(invoice_duplicates_df, selected_date, formatted_date):
    st.markdown(f'*Duplicate Invoice Line Items for {formatted_date}*')
    st.warning("This is the first iteration of this model, there are instances where Duplicates are not detected. Please verify this data before any final reporting or actions are decided If you find issues please escalate to the OIA Support channel in Slack")

    # Check if there is duplicate data to display/process
    ledger_description = None
    if not invoice_duplicates_df.empty:

        # --- Filters Section ---
        with st.expander("Additional Filters"):
            filter_col1, filter_col2 = st.columns(2)
            filter_col3, filter_col4 = st.columns(2)

            with filter_col1:
                partner_ids = sorted(invoice_duplicates_df['partner_id'].unique())
                partner_options = [f"{pid} - {invoice_duplicates_df[invoice_duplicates_df['partner_id'] == pid]['partner_name'].iloc[0]}"
                                    for pid in partner_ids]
                selected_partner_options = st.multiselect("Filter by Partner", partner_options, key="dup_partner_filter_tab2") # Key added
                selected_partners = [int(option.split(' - ')[0]) for option in selected_partner_options]

            with filter_col2:
                company_ids = sorted(invoice_duplicates_df['company_id'].unique())
                company_options = [f"{cid} - {invoice_duplicates_df[invoice_duplicates_df['company_id'] == cid]['company_name'].iloc[0]}"
                                    for cid in company_ids]
                selected_company_options = st.multiselect("Filter by Company", company_options, key="dup_company_filter_tab2") # Key added
                selected_companies = [int(option.split(' - ')[0]) for option in selected_company_options]

            with filter_col3:
                product_ids = sorted(invoice_duplicates_df['product_id'].unique())
                product_options = [f"{pid} - {invoice_duplicates_df[invoice_duplicates_df['product_id'] == pid]['product_name'].iloc[0]}"
                                    for pid in product_ids]
                selected_product_options = st.multiselect("Filter by Product", product_options, key="dup_product_filter_tab2") # Key added
                selected_products = [int(option.split(' - ')[0]) for option in selected_product_options]
            with filter_col4:
                if 'region' in invoice_duplicates_df.columns:
                    region_type = sorted(list(invoice_duplicates_df['region'].unique()))
                    selected_region = st.multiselect("Filter by Region", region_type, key="dup_region_filter_tab2")
                else:
                    selected_region = ["All"]
        
        duplicates_display_df = invoice_duplicates_df.copy()
        if selected_partners:
            duplicates_display_df = duplicates_display_df[duplicates_display_df['partner_id'].isin(selected_partners)]
        if selected_companies:
            duplicates_display_df = duplicates_display_df[duplicates_display_df['company_id'].isin(selected_companies)]
        if selected_products:
            duplicates_display_df = duplicates_display_df[duplicates_display_df['product_id'].isin(selected_products)]
        if selected_region and 'region' in duplicates_display_df.columns:
            duplicates_display_df = duplicates_display_df[duplicates_display_df['region'].isin(selected_region)]

        if not duplicates_display_df.empty:
            ledger_description = st.text_input(
                "Enter the description that will show up on the ledger upload. This will show up as (Description) for Company: (company_name) and Product: (product_name) at a quantity of (quantity)",
                key="duplicate_ledger_tab2", # Key added
                help="This will be used as the ledger description.",
                placeholder=f"Duplicated Line items on {selected_date} invoice"
            )
        else:
            st.warning("No data available to generate ledger file. Please adjust your filters to include some data.")


        if ledger_description and not duplicates_display_df.empty:
            try:
                ledger_duplicates_df = generate_ledger_data(
                    df=duplicates_display_df,
                    type_column='invoice_type',
                    partner_identifier='Partner Invoice',
                    company_identifier='Company Invoice', # Changed to match expected value? Check generate_ledger_data
                    partner_id_col='partner_id',
                    company_id_col='company_id',
                    subscription_id_col='subscription_id', # Ensure this col exists
                    partner_cost_col='estimated_credit_amount_non_usd',
                    company_cost_col='estimated_credit_amount_non_usd',
                    company_name_col='company_name',
                    product_name_col='product_name',
                    quantity_col='cira_charge_quantity',
                    start_period_col='effective_start_date',
                    end_period_col='effective_end_date',
                    product_id_col='product_id',
                    description_col=ledger_description,
                    calculation_method='duplicate_billing'
                )

                if not ledger_duplicates_df.empty:
                    ledger_csv_data = ledger_duplicates_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Ledger File",
                        data=ledger_csv_data,
                        file_name=f"Duplicate Invoice Line Items for {formatted_date}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_duplicate_ledger_button_tab2", # Key added
                        help="Click to download the generated ledger file for duplicates"
                    )

                else:
                    st.warning("Duplicate ledger file could not be generated (empty result).")
            except Exception as e:
                st.error(f"Error generating duplicate ledger file: {e}")
        st.divider()
        if not duplicates_display_df.empty:
            st.dataframe(
                duplicates_display_df,
                use_container_width=True,
                hide_index=True,
                # column_config={
                #     "cira_id": st.column_config.NumberColumn(format="%d"),
                #     "cira_record_id": st.column_config.NumberColumn(format="%d"),
                #     "cira_invoice_id": st.column_config.NumberColumn(format="%d"),
                #     "cira_completed_line_item_id": st.column_config.NumberColumn(format="%d"),
                #     "cira_partner_id": st.column_config.NumberColumn(format="%d"),
                #     "cira_company_id": st.column_config.NumberColumn(format="%d"),
                #     "cira_product_id": st.column_config.NumberColumn(format="%d"),
                #     "omt_successor_subscription_id": st.column_config.NumberColumn(format="%d"),
                #     "omt_prior_subscription_id": st.column_config.NumberColumn(format="%d"),
                #     "cira_customer_unit_cost": st.column_config.NumberColumn(format="$%.2f"),
                #     "cira_customer_cost_total": st.column_config.NumberColumn(format="$%.2f"),
                #     "cira_partner_unit_cost": st.column_config.NumberColumn(format="$%.2f"),
                #     "cira_partner_cost_total": st.column_config.NumberColumn(format="$%.2f"),
                #     "cira_invoice_date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                #     "cira_start_period": st.column_config.DateColumn(format="YYYY-MM-DD"),
                #     "cira_end_period": st.column_config.DateColumn(format="YYYY-MM-DD"),
                #     "omt_start_period": st.column_config.DateColumn(format="YYYY-MM-DD"),
                #     "omt_end_period": st.column_config.DateColumn(format="YYYY-MM-DD"),
                #     "omt_successor_subscription_start_date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                #     "omt_successor_subscription_end_date": st.column_config.DateColumn(format="YYYY-MM-DD")
                # }
            )
        st.success(f"Displaying {len(duplicates_display_df):,} duplicate records" +
                    (f" (Filtered from {len(invoice_duplicates_df):,})" if len(duplicates_display_df) != len(invoice_duplicates_df) else ""))


    else:
        st.info("No duplicate line items found for the selected date.")

@st.fragment
def render_missing_subscription_graph(selected_date, status_options):
    st.markdown(f'*__Subscription to Invoice Monitoring Visualization__*')
    st.warning("⚠️ This is the first iteration of this model only capturing full term charges (no prorates). Please verify this data before any final reporting or actions are decided. If you find issues please escalate to the OIA Support channel in Slack.")

    control_col1, control_col2, control_col3 = st.columns(3)

    with control_col1:
        tab4_status = st.selectbox("Status", status_options, key="tab4_status_select") # Key added
    with control_col2:
        visualization_type = st.selectbox("Visualization Type", ["Treemap", "Bar Chart"], key="visualization_type_tab4") # Key added
    with control_col3:
        color_scale = st.selectbox(
            "Color Scale",
            ["Viridis", "Plasma", "Inferno", "Magma", "Cividis", "Turbo",
                "Blues", "Greens", "Reds", "Purples", "Oranges",
                "RdBu", "YlGnBu", "YlOrRd", "Spectral"],
            key="color_scale_tab4" # Key added
        )

    if tab4_status != "Select a status":
        try:
            viz_data = missing_subscriptions_invoice_line_items(selected_date, tab4_status)

            if not viz_data.empty and visualization_type == "Treemap":
                with st.spinner("🔄 Loading visualization data..."):
                    missing_billing_product_term = viz_data.groupby(
                    by=['product_name', 'successor_term']
                ).agg(
                        {'missed_revenue_usd':'sum', 'original_subscription_id':'nunique'}
                ).reset_index()

                fig = px.treemap(
                    missing_billing_product_term,
                    path=['product_name', 'successor_term'],
                    values='missed_revenue_usd',
                        color='missed_revenue_usd',
                        color_continuous_scale=color_scale,
                    hover_data=['missed_revenue_usd', 'original_subscription_id'],
                        title=f"Product and Term Analysis - {tab4_status}"
                )

                fig.update_layout(
                    height=600,
                    margin=dict(t=50, l=25, r=25, b=25),
                    coloraxis_colorbar=dict(
                            title="Revenue Impact ($)",
                        thicknessmode="pixels",
                        thickness=15,
                        lenmode="pixels",
                        len=300
                    ),
                    font=dict(
                        family="Arial, sans-serif",
                        size=12
                    ),
                    title=dict(
                        font=dict(
                            family="Arial, sans-serif",
                            size=18,
                            color="#333333"
                        )
                    )
                )

                fig.update_traces(
                    hovertemplate='<b>%{label}</b><br>💰 Revenue Impact: $%{customdata[0]:,.2f}<br>🔢 Subscriptions: %{customdata[1]}<extra></extra>'
                )

                st.plotly_chart(fig, use_container_width=True)
                st.success(f"Found {len(missing_billing_product_term):,} product-term combinations")

            elif not viz_data.empty and visualization_type == "Bar Chart":
                with st.spinner("🔄 Loading visualization data..."):
                    product_term_summary = viz_data.groupby(['product_name', 'successor_term']).agg(
                        revenue_impact=('missed_revenue_usd', 'sum'),
                        subscription_count=('original_subscription_id', 'nunique')
                    ).reset_index()

                    product_summary = product_term_summary.groupby('product_name').agg(
                        total_revenue=('revenue_impact', 'sum')
                    ).reset_index()

                    product_summary = product_summary.sort_values('total_revenue', ascending=False)

                    st.markdown("### Chart Controls")
                    filter_cols = st.columns([1, 1, 1, 1])

                    with filter_cols[0]:
                        available_terms = list(product_term_summary['successor_term'].unique())
                        selected_terms = st.multiselect(
                            "Filter by Term",
                            available_terms,
                            default=available_terms,
                            key="terms_filter_tab4" # Key added
                        )

                    with filter_cols[1]:
                        max_products = len(product_summary)
                        top_n = st.number_input(
                            "Top Products",
                            min_value=3,
                            max_value=min(30, max_products),
                            value=min(10, max_products),
                            key="top_n_products_tab4" # Key added
                        )

                    with filter_cols[2]:
                        chart_type = st.radio(
                            "Chart Type",
                            ["Revenue"],
                            index=0,
                            key="chart_type_select_tab4" # Key added
                        )

                    with filter_cols[3]:
                        show_data = st.checkbox(
                            "Show Data Table",
                            value=False,
                            key="show_data_option_tab4" # Key added
                        )

                    if selected_terms:
                        filtered_term_summary = product_term_summary[product_term_summary['successor_term'].isin(selected_terms)]
                    else:
                        filtered_term_summary = product_term_summary

                    filtered_product_summary = filtered_term_summary.groupby('product_name').agg(
                        total_revenue=('revenue_impact', 'sum'),
                        total_subscriptions=('subscription_count', 'sum')
                    ).reset_index()

                    filtered_product_summary = filtered_product_summary.sort_values('total_revenue', ascending=False).head(int(top_n))

                    top_products_filtered = filtered_product_summary['product_name'].tolist()
                    filtered_term_summary = filtered_term_summary[filtered_term_summary['product_name'].isin(top_products_filtered)]

                    revenue_fig = px.bar(
                        filtered_term_summary,
                        x='product_name',
                        y='revenue_impact',
                        color='successor_term',
                        text='subscription_count',
                        barmode='stack',
                        title=f"Products by Term and Revenue Impact - {tab4_status}",
                        category_orders={"product_name": top_products_filtered},
                        labels={
                            'product_name': 'Product',
                            'revenue_impact': 'Revenue Impact ($)',
                            'subscription_count': 'Subscription Count',
                            'successor_term': 'Term'
                        },
                        color_discrete_sequence=px.colors.qualitative.Bold,
                    )

                    revenue_fig.update_traces(
                        texttemplate='%{text}',
                        textposition='inside',
                        hovertemplate='<b>%{x}</b> - %{fullData.name}<br>💰 Revenue Impact: $%{y:,.2f}<br>🔢 Subscriptions: %{text}<extra></extra>'
                    )

                    for i, product in enumerate(top_products_filtered):
                        total = filtered_product_summary[filtered_product_summary['product_name'] == product]['total_revenue'].values[0]
                        revenue_fig.add_annotation(
                            x=i,
                            y=total,
                            text=f"${total:,.0f}",
                            showarrow=False,
                            yshift=10,
                            font=dict(size=10),
                        )

                    revenue_fig.update_layout(
                        xaxis_title="Product",
                        yaxis_title="Revenue Impact ($)",
                        xaxis_tickangle=-45,
                        height=700,
                        margin=dict(t=50, l=25, r=25, b=100),
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=1.05,
                            xanchor="right",
                            x=1.0
                        ),
                        autosize=True,
                        xaxis=dict(
                            type="category"
                        )
                    )

                    st.plotly_chart(revenue_fig, use_container_width=True)

                if show_data:
                    st.markdown("### Detailed Data")

                    pivot_df = filtered_term_summary.pivot_table(
                        index='product_name',
                        columns='successor_term',
                        values=['revenue_impact', 'subscription_count'],
                        aggfunc='sum',
                        fill_value=0
                    )

                    pivot_df[('revenue_impact', 'Total')] = pivot_df['revenue_impact'].sum(axis=1)
                    pivot_df[('subscription_count', 'Total')] = pivot_df['subscription_count'].sum(axis=1)

                    display_df = pivot_df.copy()
                    for col in display_df.columns:
                        if col[0] == 'revenue_impact':
                            display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")

                    display_df = display_df.reindex(top_products_filtered)

                    st.dataframe(display_df, use_container_width=True)

            else:
                st.info(f"No {tab4_status.lower()} subscription data found for the selected date.")

        except Exception as e:
            st.error(f"Error generating visualization: {str(e)}")

    else:
        st.info("👆 Please select a status in the dropdown above to view visualizations")

def render_transaction_monitoring():
    st.title("Transaction Monitoring") 
    st.markdown("""
    - Missing Subscriptions on Invoices: Instances where we expect full term charges on an invoice but one is not present (looks at partner invoices)
    - Duplicate Invoice Line Items: Scenarios where the same line item is present on an invoice more than once. 
    - Order Manager Transaction: In Progress...
                
    """, unsafe_allow_html=True)

    current_month = date.today().replace(day=1)
        
    date_range = st.date_input(
        "Select Date Range",
        value=(current_month),
            min_value=datetime(2024, 11, 1).date(),
            max_value=date.today(),
            format="YYYY-MM-DD"
        )
    
    if isinstance(date_range, tuple):
        start_date = process_date(date_range[0])
        end_date = process_date(date_range[1], False)
    else:
        selected_date = process_date(date_range)
    st.markdown("""
    <div style="text-align: left; font-size: 0.7em; opacity: 0.5; margin-top: 20px;">Models and Frontend built by Isaac Buck and the OIA Team</div>
    """, unsafe_allow_html=True)

    invoice_duplicates_df = duplicate_invoice_line_items(selected_date)
    

    try:
        missing_subscription_invoice_line_summary = fetch_missing_subscription_invoice_line_summary(selected_date)
        
        if missing_subscription_invoice_line_summary.empty:
            missing_subscription_invoice_line_summary = pd.DataFrame({
                'transaction_month': [selected_date],
                'missing_subscription_count': [0],
                'missing_partner_count': [0],
                'missing_company_count': [0],
                'product_count': [0],
                'missed_revenue_usd': [0.0],
                'missed_partner_revenue_non_usd': [0.0]
            })
    except Exception as e:
        st.error(f"❌ Error loading summary data: {str(e)}")
        missing_subscription_invoice_line_summary = pd.DataFrame({
            'transaction_month': [selected_date],
            'missing_subscription_count': [0],
            'missing_partner_count': [0],
            'missing_company_count': [0],
            'product_count': [0],
            'missed_revenue_usd': [0.0],
            'missed_partner_revenue_non_usd': [0.0]
        })
    
    st.divider()

    formatted_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%B %Y')
    

    st.markdown(f'*__Duplicate Invoice Line Items for {formatted_date}__*')

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Duplicate Invoice Line Items", invoice_duplicates_df['cira_charge_id'].nunique())
    with col2:
        st.metric("Number of Partners", invoice_duplicates_df['partner_id'].nunique())
    with col3:
        st.metric("Number of Companies", invoice_duplicates_df['company_id'].nunique())
    with col4:
        st.metric("Number of Products", invoice_duplicates_df['product_id'].nunique())
    with col5:
        st.metric("Revenue Impact of Duplicates", f"${invoice_duplicates_df['estimated_credit_amount_usd'].sum():,.2f}")
    
    st.markdown(f'*__Missing Subscriptions on Invoices for {formatted_date}__*')
    col6, col7, col8, col9, col10 = st.columns(5)
    with col6:
        st.metric("Number of Subscriptions Missed On Invoice", int(missing_subscription_invoice_line_summary['missing_subscription_count'].iloc[0])) 
    with col7:
        st.metric("Number of Partners", int(missing_subscription_invoice_line_summary['missing_partner_count'].iloc[0]))
    with col8:
        st.metric("Number of Companies", int(missing_subscription_invoice_line_summary['missing_company_count'].iloc[0]))
    with col9:
        try:
            service_charge_value = missing_subscription_invoice_line_summary['service_charges_posted_usd'].iloc[0]
            if pd.notna(service_charge_value):
                service_charge_display = f"${service_charge_value:,.2f}"
            else:
                service_charge_display = "$0.00"
        except (KeyError, IndexError, TypeError):
            service_charge_display = "$0.00"
        st.metric("Service Charges Posted (USD)", service_charge_display)
    with col10:
        st.metric("Revenue Impact of Missing subscriptions (USD)", f"${missing_subscription_invoice_line_summary['missed_revenue_usd'].iloc[0]:,.2f}")


    st.write(""" Additional information about the metrics and models used to pull these metrics""") 
    with st.expander("💰 Missing Subscriptions on Invoices", expanded=False):
        st.markdown("""
            This flow chart shows the process of how we model subscription data in an attempt to catch instances where a full term charge is expected on the invoice but not present. Only full term charges are modeled, mised prorates are not included in this model.

            #### Logic and Description of Models:        
            1. **Agg Subscription Monthly: Aggregates subscription data by the months it's active \
to when it was initially ordered to when it's cancelled. This model also counts \
the number of instances a product upgrade, renewal, price and quantity changes occured \
in addition to net values of the quantity and price changes.**
            
                - This models also gives us the latest subscription ID within that month which is used to join against the fact_subscription_modification table. If a modification does not occur in that month we carry forward the previous months data until a modifications occurs.  
            2. **Fact Subscription Modification**: This model takes the subscription and completed_line_item data and combines it together then flattens it into a table so we can compare the successor subscription metrics against the previous. 
                - Helpful for detecting when subscription modifications occurs, findings quantity deltas, term changes, commitment term changes ect so we can flag these changes in an easier manner. 
            3. **Subscription Info Per Month (Not a model but calculation)**: Joins the agg_subscription_monthly table with the fact_subscription_modification to allow use to see the subscription per month it's active and calculate the estimated billing renewal date which is the month we expect the full term charge on the invoice. 
                - Logic for Estimated Billing Renewal: 
                    - Monthly Subscriptions:
                        - Takes the transaction_month from the Agg Subscription Monthly since we expect monthly to be billed in full each month. 
                    - Annual Subscriptions:
                        - For subscriptions with no commitment term end date:
                            - We use the billing cycle start date but in the current year
                            - Example: A subscription started in July 1st 2022 → Forecast for July 1st 2024
                            - Example: A subscription started on July 15th 2022 → Forecast for August 1st 2024
                        - For commitment term end dates falling on the 1st of a month and commitment term end date:
                            - We use that same month but in the current year. Inclusive of commitment term end dates in the past, current and future years since we expect annuals to bill in full each year. 
                            - Example: Commitment term ending February 1, 2025 → Forecast for February 1, 2024. A subscription that renews on the 1st of the month, we expect to charge the full term on that months invoice. 
                        - For commitment term end dates falling mid-month and commitment term end date:
                            - We forecast for the 1st of the following month in the current year
                            - Example: Commitment term ending June 17, 2025 → Forecast for July 1, 2024
                        - For commitment term end dates falling mid-month and commitment term end date is in the current year or prior year:
                            - We forecast for the 1st of the following month in the current year
                            - Example: Commitment term ending June 17, 2024 → Forecast for July 1, 2024
                        - Everything else: 
                            - Take the billing cycle start date, take the month and set to the current year. 
                - **Additional Filters:**
                    - Only looks at anniversary billed enabled products (Microsoft and Adobe entitlements)
                    - Transaction months starting in December 2024 and forward (cutover to anniversary billing)
                    - Estimated Billing Renewal Date is equal to the transaction month (reduce false positives for annual+ subscriptions)
            4. **Fact CSV Invoice Row Archive/Int Subscription Joined**: modeled from csv_invoice_row_archive table in addition to adding in exchange rates, invoice type (partner vs bill-on-behalf), business unit information and production information. 
                 - To grab the original subscription id we join the CIRA table to the int_subscription table so we can group full term charges, prorates by original_subscription_id and invoice_date. 
                 - Prorates are included to give users context with the missing Full Term Charges due to instances where we've seen close to full term charges that are technically prorates due to the start date being pushed out by a couple of days. 
                    - **Aggregates Proates by Subscription and Invoice Month**
                        - Group prorate charges by original_subscription_id and invoice_date
                        - Sum partner_total and partner_total_usd 
                        - Only looks at partner invoices and direct-company invoice (house accounts under Pax8 as the partner were an invoice is not generated). Bill-on-behalf invoices are not included to reduce duplicates 
                        -  Prorate Data Points: 
                            - cira_prorate_match_status: If prorates are matched to the subscription/invoice month then Matched Prorate, else No Prorates
                            - cira_prorate_total: Sum of prorate charges by subscription and invoice month.
                            - cira_prorate_count: Count of prorate charges by subscription and invoice month
                            - net_subscription_and_prorate_usd: Sum of prorate charges by subscription and invoice month
                            - net_subscription_and_prorate_non_usd: Sum of prorate charges by subscription and invoice month
                    - **Aggregates Full Term Charges by Subscription and Invoice Month**
                        - Group full term charges by original_subscription_id and invoice_date
                        - Sum partner_total and partner_total_usd (bill-on-behalf invoices are not included to reduce duplicates)        
                        - Full Term Data Points: 
                            - cira_partner_cost_total: Sum of full term charges by subscription and invoice month
                            - cira_customer_cost_total: Sum of full term charges by subscription and invoice month
                            - missed_revenue_usd: Sum of full term charges by subscription and invoice month. Partner Buy Rate * Subscription Quantity as missed revenue, if it's a direct company we take the Retail Price * Subscription Quantity. 
                            - missed_revenue_non_usd: Sum of full term charges by subscription and invoice month. Partner Buy Rate * Subscription Quantity as missed revenue, if it's a direct company we take the Retail Price * Subscription Quantity. 
            5. **Fact Subscription Monthly Billing Projection**: Since we have the estimated billing renewal date by subscription, Aggregated prorates and full term charges we can join this data together to get the full picture. 
                - Join the Subscription Info Per Month to the Aggregated Prorates and Full Term Charges tables
                    - Invoice Date equals the transaction month
                    - Original Subscription ID equals the original_subscription_id in the Aggregated Prorates and Full Term Charges tables
                    - Estimated Billing Renewal Date equals the invoice date (this is a left join to find instances where full term or prorates are missing)
            6. **Agg Subscription Monthly Projection**: Groups data in the Fact Subscription Monthly Projection table by transaction and gives the following metrics for instances where the full term charge is missing
                - Product Count: Count of distinct products by transaction month
                - Missing Partner Count: Count of distinct partners by transaction month
                - Missing Company Count: Count of distinct companies by transaction month
                - Missing Subscription Count: Count of distinct subscriptions by transaction month
                - Missed Partner Revenue USD: Sum of missed partner revenue converted to USD
                - Missed Partner Revenue Non-USD: Sum of missed partner revenue
            #### Legend: 
            - Blue Boxes Represent standalone fact or staging tables used later downstream to aggregated data into a single model
            - Green boxes points where two or more models are joined together to give additional context into the data. 
            - Diamonds represent decision points
        """)
        render_missing_subscriptions_on_invoice_chart()
        
    with st.expander("📊 Invoice Duplicate Detection", expanded=False):
        st.markdown("""
            This flow chart shows the process of how invoice line items are detected as duplicates and the upstream models leveraged to coalesce that data together. 
                    
            #### Logic and Description of Models:  
            1. **Fact Subscription Modification**: This model takes the subscription and completed_line_item data and combines it together then flattens it into a table so we can compare the successor subscription metrics against the previous. 
                - Helpful for detecting when subscription modifications occurs, findings quantity deltas, term changes, commitment term changes ect so we can flag these changes in an easier manner. 
            2. **Order Manager Transaction (raw)**: pulled directly from the cc.order_manager_transaction table and rendered in DBT as stg__cc_order_manager_transaction. 
                - This is the raw data set from order_manager_transaction, no other tables are joined or transformations occured.  
            3. **Order Manager Transaction**: This model is joining the fact_subscription_modification table with the order_manager_transaction table on successor_subscription_id and prior_subscription_id. This table give use reference to the subscription/completed line item info against the order_manager_transaction data. 
            4. **Fact CSV Invoice Row Archive**: This model is based on the csv_invoice_row_archive in addition to adding in exchange rates, invoice type and business unit information. 
            5. **Fact Order Manager Transaction CIRA Duplicates**: This model joins the fact_order_manager_transaction table with the fact_csv_invoice_row_archive table on completed_line_item_id. This table gives us the ability to detect duplicate line items in the invoice. The CIRA data is the baseline then joined to the fact_order_manager_transaction data. 
                - Filter CIRA Data for the following: 
                    - invoice_date: Equal or greater than 2024-12-01 (month we cutover to the anniversary billing)
                    - anniversary_billing: True
                    - transaction_type: subscription or prorate (things like service charges, arrears ect... were pulled in which are do not flow through Order Manager)
                    - cira_row_number: Give us positional rank by the following attributes so we can find lin items that are mulitple of these and meet the same criteria. (partiion by invoice_id, completed_line_item_id, invoice_type, transaction_type, quantity, line_item_total) 
                    - cira_duplicate_count: counts the number of instances based on the row_number and criteria above on whether the following lines are duplicates. 
                - Join the filtered CIRA data with the fact_order_manager_transaction data. Anything with cira_ in the column name comes from the CIRA table, anything with omt_ comes from fact_order_manager_transaction. 
                    - Joined CIRA and Order Manager on the following values: completed_line_item_id, transaction_type (subscription or prorate), invoice_date and start_period.
                    -Filter cira line items where cira_row_number>1: meaning these are instances of detected duplicates
             #### Legend:          
            - Blue Boxes Represent standalone fact or staging tables used later downstream to aggregated data into a single model
            - Green boxes points where two or more models are joined together to give additional context into the data. 
            - Diamonds represent decision points
        """)
        render_flow_chart()

    st.divider()

    missing_subscriptions, duplicates, missing_subscriptions_graph = st.tabs(["Missing Subscription Charges", "Duplicate Invoice Line Items","Subscription to Invoice Monitoring (Graphs)"])
    
    with missing_subscriptions:
        # Call the fragment function here
        render_missing_subscriptions_info(selected_date, formatted_date)

    with duplicates:
        # Call the new fragment function here
        render_duplicate_invoice_line_items(invoice_duplicates_df, selected_date, formatted_date)

    with missing_subscriptions_graph:
        # Define status_options here if needed or pass it down
        status_options = ["Select a status", "Missing", "Matched"]
        render_missing_subscription_graph(selected_date, status_options)



if __name__ == "__page__":
    render_transaction_monitoring()