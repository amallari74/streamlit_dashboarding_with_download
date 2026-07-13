import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

from utils import db_util, auth_util
from router.roles import REPORTS_ROLES as ROLES
from config import DEFAULT_PAGE_SIZE

from billing_run.models.invoice_model import (
    fetch_invoice_count, 
    fetch_invoice_balance, 
    fetch_ledger_health, 
    fetch_invoice_line_details, 
    fetch_credits_information, 
    fetch_invoice_release_status,
    fetch_invoice_health,
    fetch_line_item_count
)

from billing_run.models.billing_task_model import fetch_tax_billing_tasks

from billing_run.models.arrears_task_model import (
    fetch_manual_arrears_tasks,
    fetch_arrears_error_totals,
    fetch_error_categories,
    fetch_arrears_tasks
)

def format_currency(value, currency_code='USD'):
    """Format currency values with appropriate symbols"""
    if pd.isna(value):
        return ''
    
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'CAD': 'C$',
        'AUD': 'A$',
        'SEK': 'kr'
    }
    
    symbol = currency_symbols.get(currency_code, '')
    return f"{symbol}{value:,.2f}"

def load_billing_data(selected_invoice_month):
    """Load invoice related data from the database using invoice_model functions"""
    data = {
        'invoice_count': fetch_invoice_count(selected_invoice_month),
        'balance': fetch_invoice_balance(selected_invoice_month),
        'ledger_health': fetch_ledger_health(selected_invoice_month),
        'line_details': fetch_invoice_line_details(selected_invoice_month),
        'credits': fetch_credits_information(selected_invoice_month),
        'release_status': fetch_invoice_release_status(selected_invoice_month),
        'invoice_health': fetch_invoice_health(selected_invoice_month),
        'tax_tasks': fetch_tax_billing_tasks(selected_invoice_month),
        'arrears': fetch_manual_arrears_tasks(selected_invoice_month),
        'error_categories': fetch_error_categories(selected_invoice_month),
        'errors': fetch_arrears_error_totals(selected_invoice_month),
        'arrears_tasks': fetch_arrears_tasks(selected_invoice_month), 
        'line_item_count': fetch_line_item_count(selected_invoice_month)
    }
    return data

def render_overview_metrics(data):
    """Render the key performance metrics at the top of the page"""
    st.header("Key Performance Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Invoices", 
            f"{int(data['invoice_count']['month_0'].iloc[0]):,}",
            f"{int(data['invoice_count']['variance'].iloc[0]):+,}"
        )
    
    with col2:
        st.metric(
            "Invoice Balance",
            f"${int(data['balance']['month_0'].sum()):,}",
            f"${int(data['balance']['variance'].sum()):+,}"
        )
    
    with col3:
        st.metric(
            "Invoice Health", 
            f"{data['invoice_health']['month_0'].iloc[0]:.1%}",
            f"{data['invoice_health']['variance'].iloc[0]:.1%}"
        )
    
    with col4:
        st.metric(
            "Ledger Health", 
            f"{data['ledger_health']['month_0'].iloc[0]:.1%}",
            f"{data['ledger_health']['variance'].iloc[0]:.1%}"
        )

def render_balance_by_region(df_balance):
    """Render the invoice balances by region visualization"""
    st.header("Invoice Balances by Region")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Current Month",
        x=df_balance['region'],
        y=df_balance['month_0'],
        text=df_balance['month_0'].apply(lambda x: format_currency(x)),
        textposition='auto',
    ))
    fig.add_trace(go.Bar(
        name="Previous Month",
        x=df_balance['region'],
        y=df_balance['month_1'],
        text=df_balance['month_1'].apply(lambda x: format_currency(x)),
        textposition='auto',
    ))
    fig.update_layout(barmode='group')
    st.plotly_chart(fig)

def render_arrears_and_credits(df_arrears, df_credits):
    """Render the manual arrears and service credits section"""
    st.header("Manual Arrears & Service Credits")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top Manual Arrears Vendors")
        st.dataframe(
            df_arrears[['vendor', 'month_0', 'variance']]
            .rename(columns={
                'month_0': 'Current Month',
                'variance': 'MoM Change'
            })
            .assign(
                **{
                    'Current Month': lambda x: x['Current Month'].apply(format_currency),
                    'MoM Change': lambda x: x['MoM Change'].apply(format_currency)
                }
            ), 
            use_container_width=True
        )
    
    with col2:
        st.subheader("Top Service Credits")
        st.dataframe(
            df_credits[['vendor', 'month_0', 'variance']]
            .rename(columns={
                'month_0': 'Current Month',
                'variance': 'MoM Change'
            })
            .assign(
                **{
                    'Current Month': lambda x: x['Current Month'].apply(format_currency),
                    'MoM Change': lambda x: x['MoM Change'].apply(format_currency)
                }
            ), 
            use_container_width=True
        )

def render_billing_tasks(df_tax, df_arrears_tasks):
    """Render the billing tasks status section"""
    st.header("Billing Tasks Status")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Tax Calculation Tasks")
        tax_pivot = pd.pivot_table(
            df_tax,
            values='count',
            index='method',
            columns='status',
            fill_value=0
        )
        st.dataframe(tax_pivot, use_container_width=True)
    
    with col2:
        st.subheader("Arrears Processing Tasks")
        arrears_pivot = pd.pivot_table(
            df_arrears_tasks,
            values='count',
            index='run_on',
            columns='status',
            fill_value=0
        )
        st.dataframe(arrears_pivot, use_container_width=True)

def render_release_status(df_release):
    """Render the invoice release status visualization"""
    st.header("Invoice Release Status")
    
    # Create the stacked bar chart
    release_fig = px.bar(
        df_release,
        x='region',
        y='value',
        color='release_status',
        title="Invoice Release Status by Region",
        barmode='group',
        color_discrete_map={
            'Held - Not Approved': '#FF9999',
            'Held - Approved': '#FFB366',
            'Released': '#99FF99'
        }
    )
    
    # Customize the layout
    release_fig.update_layout(
        xaxis_title="Region",
        yaxis_title="Count",
        legend_title="Status",
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(release_fig, use_container_width=True)

def render_invoice_line_details(df_line_details):
    """Render the invoice line item details visualization"""
    st.header("Invoice Line Item Details")
    
    # Create the bar chart for each region
    fig = px.bar(
        df_line_details,
        x='cira_type',
        y='total_usd',
        color='region',
        barmode='stack',
        title="Invoice Line Items by Type and Region",
        labels={
            'cira_type': 'Charge Type',
            'total_usd': 'Amount (USD)',
            'region': 'Region'
        }
    )
    
    # Customize the layout
    fig.update_layout(
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        yaxis=dict(
            title="Amount (USD)",
            tickformat="$,.0f"
        )
    )
    
    # Add value labels on the bars
    fig.update_traces(
        texttemplate='%{y:$,.0f}',
        textposition='auto'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_line_item_count(df_line_item_count):
    """Render the line item count visualization"""
    st.header("Invoice Line Item Count")

    line_item_count_df = pd.pivot_table(
            df_line_item_count,
            index='invoice_month',
            columns='term_type',
            values='line_item_count',
            aggfunc='sum',
            fill_value=0,
        ).sort_index()

    if line_item_count_df is not None and not line_item_count_df.empty:
        line_item_count_fig = px.bar(
            line_item_count_df,
            x=line_item_count_df.index,
            y=line_item_count_df.columns,
            labels={"index": "Invoice Month", "columns": "Term Type"},
            barmode='stack',
            color_discrete_map={
                'term_type': 'term_type'
            }
        )
        st.plotly_chart(line_item_count_fig, use_container_width=True)
        with st.expander("View Line Item Count by Term and Type"):
            st.dataframe(line_item_count_df, use_container_width=True)
    else:
        st.warning("No line item count data available.")



def show_monthly_billing_summary():
    """Main function to display the monthly billing summary report"""

    
    st.title("Monthly Billing Summary")
    st.markdown(f"Report for {datetime.now().strftime('%B %Y')}")
    

    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_invoice_month = st.date_input(
            "Invoice Month",
            value=(datetime.now().replace(day=1)),
            min_value=datetime(2024, 11, 1).date(),
            max_value=datetime.now().replace(day=1),
            format="YYYY-MM-DD"
        )
    

    data = None
    if selected_invoice_month is not None:
        data = load_billing_data(selected_invoice_month)
        if any(df.empty for df in data.values()):
            st.warning("Some billing data is not available.")
            return
    else:
        st.warning("Please select an invoice month.")
        

    with col2:
        if data is not None:
            selected_regions = st.multiselect(
                "Region",
                options=['All'] + sorted(data['balance']['region'].unique().tolist()),
                default=['All']
            )
        else:
            st.empty()

    with col3:
        if data is not None:
            selected_vendors = st.multiselect(
                "Vendor",
                options=['All'] + sorted(set(data['arrears']['vendor'].unique().tolist() + 
                                        data['credits']['vendor'].unique().tolist())),
                default=['All']
            )
        else:
            st.empty()
    

    filtered_data = data.copy()
    
    if 'All' not in selected_regions:
        for key in ['balance', 'release_status', 'line_details']:
            if key in filtered_data:
                filtered_data[key] = filtered_data[key][
                    filtered_data[key]['region'].isin(selected_regions)
                ]
    
    if 'All' not in selected_vendors:
        for key in ['arrears', 'credits']:
            if key in filtered_data:
                filtered_data[key] = filtered_data[key][
                    filtered_data[key]['vendor'].isin(selected_vendors)
                ]
    
    # Render report sections
    render_overview_metrics(filtered_data)
    render_balance_by_region(filtered_data['balance'])
    st.divider()
    render_release_status(filtered_data['release_status'])
    st.divider()
    render_invoice_line_details(filtered_data['line_details'])
    st.divider()
    render_line_item_count(filtered_data['line_item_count'])
    st.divider()
    render_arrears_and_credits(filtered_data['arrears'], filtered_data['credits'])
    st.divider()
    render_billing_tasks(filtered_data['tax_tasks'], filtered_data['arrears_tasks'])

if __name__ == "__page__":
    show_monthly_billing_summary() 