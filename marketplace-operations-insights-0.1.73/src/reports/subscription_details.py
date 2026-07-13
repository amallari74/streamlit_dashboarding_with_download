import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import db_util, auth_util
from router.roles import REPORTS_ROLES as ROLES
from config import DEFAULT_PAGE_SIZE
import plotly.graph_objects as go
from queries.queries import Queries
import plotly.express as px



def load_subscriptions_by_invoice(invoice_id=None, subscription_id=None):
    try:
        query = Queries.load_subscriptions_by_invoice(invoice_id=invoice_id, subscription_id=subscription_id)
        params = {}
        if invoice_id is not None:
            params["invoice_id"] = invoice_id
        if subscription_id is not None:
            params["subscription_id"] = subscription_id
        return db_util.query(query, params)
    except ValueError as e:
        raise e

def load_related_subscriptions(original_subscription_id):
    query = Queries.load_related_subscriptions(original_subscription_id)
    return db_util.query(query, {"original_subscription_id": original_subscription_id})

def load_subscription_metrics(subscription_id):
    query = Queries.load_subscription_metrics(subscription_id)
    return db_util.query(query, {"subscription_id": subscription_id})

def load_subscription_arrears_tasks(subscription_id):
    query = Queries.load_subscription_arrears_tasks(subscription_id)
    return db_util.query(query, {"subscription_id": subscription_id})

def load_subscription_arrears_errors(subscription_id):
    query = Queries.load_subscription_arrears_errors(subscription_id)
    return db_util.query(query, {"subscription_id": subscription_id})

def calculate_revenue_variance(subscription_id):
    query = Queries.calculate_revenue_variance(subscription_id)
    return db_util.query(query, {"subscription_id": subscription_id})


# TODO(MOA-585): Define a function to load average changes for comparison.
def load_average_changes(subscription_id):
    # TODO(MOA-585): Implement logic to load average changes for partners, vendors, and products.
    pass

# TODO(MOA-585): Implement revenue percentile calculation
def calculate_revenue_percentile(subscription_id):
    """Calculate where this subscription stands in terms of revenue compared to:
    - Other subscriptions from the same partner
    - Other subscriptions for the same product
    - Other subscriptions in the same business unit
    """
    pass

# TODO(MOA-585): Implement subscription health analysis
def analyze_subscription_health(subscription_id):
    """Analyze subscription health based on:
    - Frequency of failed arrears tasks
    - Support ticket volume
    - Billing issues
    - Usage pattern anomalies
    - Payment history
    """
    pass

# TODO(MOA-585): Implement change pattern analysis
def analyze_change_patterns(subscription_id):
    """Analyze patterns in subscription changes:
    - Frequency of quantity changes
    - Seasonal patterns in usage??
    - Compare against similar subscriptions
    - Detect unusual spikes or drops
    """
    pass

# TODO(MOA-585): Implement related entity analysis
def analyze_related_entities(subscription_id):
    """Analyze related entities and their impact:
    - Other subscriptions from same partner
    - Other products used by partner
    - Partner tier and status
    - Company relationships
    """
    pass

def highlight_error_rows(df):
    today = datetime.now()
    first_of_this_month = today.replace(day=1)
    first_of_last_month = (first_of_this_month - timedelta(days=1)).replace(day=1)
    def highlight(row):
        if "status" in row and row["status"] == "error":
            return ['background-color: #e36877'] * len(row)
        elif "rate_plan_start_date" in row and row["rate_plan_start_date"] >= first_of_last_month:
            return ['background-color: #ebe54d'] * len(row)
        else:
            return [''] * len(row)

    return df.style.apply(highlight, axis=1)


def render_subscription_overview(subscription_data):
    if subscription_data.empty:
        return

    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        st.metric("Days Active", subscription_data.iloc[0]['days_active'])
        
        # Check if subscription is expired and show appropriate status
        status = subscription_data.iloc[0]['status']
        end_date = pd.to_datetime(subscription_data.iloc[0]['end_date'])
        
        if end_date and end_date < pd.Timestamp.now():
            st.metric("Expired", f"Expired ({status})")
            if subscription_data.iloc[0]['original_subscription_id']:
                # TODO(MOA-585): Improve the check above by passing in related_subscriptions dataframe
                st.info("This subscription has been replaced. See the Related Subscriptions table below for any current subscription.")
        else:
            st.metric("Status", status)
    
    with col2:
        st.metric("Monthly Revenue", f"${subscription_data.iloc[0]['monthly_revenue']:.2f}")
        st.metric("Quantity", subscription_data.iloc[0]['quantity'])
    
    with col3:
        st.metric("Partner", subscription_data.iloc[0]['partner_name'])
        if subscription_data.iloc[0].get('company_name') and subscription_data.iloc[0]['company_name'] != subscription_data.iloc[0]['partner_name']:
            st.metric("Company", subscription_data.iloc[0]['company_name'])
        st.metric("Product", subscription_data.iloc[0]['product_name'])

def render_arrears_tasks(arrears_tasks, arrears_errors):
    if arrears_tasks.empty and arrears_errors.empty:
        st.info("No arrears tasks found. This may be an entitlement product or a very new subscription.")
        return

    if arrears_tasks.empty:
        # this is pretty much inconceivable, since it would imply there are arrears errors but no arrears tasks
        st.info("No recent arrears tasks found.")
    else:
        with st.expander("Recent Arrears Tasks"):
            st.dataframe(
                highlight_error_rows(arrears_tasks),
                column_config={
                    "created_dt": st.column_config.DatetimeColumn("Created"),
                    "updated_dt": st.column_config.DatetimeColumn("Updated"),
                    "run_on": st.column_config.DatetimeColumn("Run On"),
                    "status": st.column_config.TextColumn("Status", help="Current status of the task"),
                    "error_count": st.column_config.NumberColumn("Errors", help="Number of errors encountered"),
                    "source_table": st.column_config.TextColumn("Source", help="Origin table of the task"),
                },
                hide_index=True,
            )

    if arrears_errors.empty:
        st.info("No categorized errors found for this subscription.")
    else:
        with st.expander("Error Categories"):
            st.dataframe(
                arrears_errors,
                column_config={
                    "run_on": st.column_config.DatetimeColumn("Run On"),
                    "error_category": st.column_config.TextColumn("Category"),
                    "status": st.column_config.TextColumn("Current Status"),
                    "occurrence_count": st.column_config.NumberColumn("Count"),
                    "error_message": st.column_config.TextColumn("Error Message", help="Full error message text"),
                },
                hide_index=True,
            )

def render_revenue_variance(variance_data):
    if variance_data.empty:
        st.info("No historical revenue data available for variance calculation.")
        return
    
    with st.expander("Revenue Changes"):
        st.dataframe(
            variance_data,
            column_config={
                "invoice_month": st.column_config.DateColumn("Month"),
                "total_revenue": st.column_config.NumberColumn(
                    "Revenue",
                    format="$%.2f",
                    help="Total revenue for the month"
                ),
                "total_quantity": st.column_config.NumberColumn(
                    "Quantity",
                    help="Total quantity for the month"
                ),
                "revenue_variance_pct": st.column_config.NumberColumn(
                    "% Revenue Change",
                    format="%.1f%%",
                    help="Percentage change in revenue from previous month"
                ),
                "quantity_variance_pct": st.column_config.NumberColumn(
                    "% Quantity Change",
                    format="%.1f%%",
                    help="Percentage change in quantity from previous month"
                ),
                "revenue_to_quantity_ratio_variance_pct": st.column_config.NumberColumn(
                    "% Rate Change",
                    format="%.1f%%",
                    help="Percentage change in revenue/quantity ratio from previous month"
                ),
            },
            hide_index=True,
        )
def render_subscription_summary():
    # Add filters at the top
    date_filter, vendor_filter = st.columns(2)
    
    # Set start date to 1st of Jan 2023
    start_date = pd.Timestamp('2023-01-01')
    # Set current date to 1st of current month
    current_date = pd.Timestamp.now().replace(day=1)
    
    billing_periods = pd.date_range(
        start=start_date,
        end=current_date,
        freq='MS'  # Month Start frequency
    )
    
    with date_filter:
        selected_period = st.selectbox(
            "Billing Period",
            options=billing_periods,
            format_func=lambda x: x.strftime('%Y-%m-%d'),
            index=len(billing_periods)-1  # Default to current month
        )
    
    # Get unique vendors first
    try:
        vendor_data = db_util.query(Queries.UNIQUE_VENDORS_SUBSCRIPTION)
        # Filter out None values and convert to list
        vendors = ['All'] + sorted([v for v in vendor_data['vendor'].tolist() if v is not None]) if not vendor_data.empty else ['All']
    except Exception as e:
        if 'SSL' in str(e) or '_ssl' in str(e):
            st.error("Database connection error: Unable to establish a secure connection. Please check your VPN connection and try again.")
        else:
            st.error(f"Error loading vendor data: {str(e)}")
        vendors = ['All']
    
    with vendor_filter:
        selected_vendor = st.selectbox(
            "Vendor",
            options=vendors,
            index=0
        ) 

    try:
        query = Queries.load_subscription_overview_data(billing_period=selected_period, vendor=selected_vendor)
        # Format selected_period as YYYY-MM-DD string
        formatted_date = selected_period.strftime('%Y-%m-%d')
        query_params = {
            "billing_period": formatted_date,
            "vendor": selected_vendor
        }
        overview_data = db_util.query(query, query_params)

    except Exception as e:
        if 'SSL' in str(e) or '_ssl' in str(e):
            st.error("Database connection error: Unable to establish a secure connection. Please check your VPN connection and try again.")
        else:
            st.error(f"Error loading subscription data: {str(e)}")
        overview_data = pd.DataFrame()
    
    # Filter data based on selections
    if not overview_data.empty:
        # Filter by billing period if the column exists
        if 'billing_period' in overview_data.columns:
            overview_data = overview_data[
                overview_data['billing_period'].dt.to_period('M') == selected_period.to_period('M')
            ]
        
        # Filter by vendor if selected and column exists
        if selected_vendor != 'All' and 'vendor' in overview_data.columns:
            overview_data = overview_data[overview_data['vendor'] == selected_vendor]
    
    # Create columns for metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col6, col7, col8, col9, col10 = st.columns(5)
    
    with col1:
        try:
            total_partners = overview_data['partner_count'].iloc[0] if not overview_data.empty else 0
            st.metric("Total Partners", 
                    f"{int(total_partners):,}", 
                    help="Total number of partners in the selected billing period")
        except Exception:
            st.metric("Total Partners", "0", help="Total number of partners in the selected billing period")
    
    with col2:
        try:
            total_companies = overview_data['company_count'].iloc[0] if not overview_data.empty else 0
            st.metric("Total Companies", 
                    f"{int(total_companies):,}", 
                    help="Total number of companies in the selected billing period")
        except Exception:
            st.metric("Total Companies", "0", help="Total number of companies in the selected billing period")

    with col3:
        try:
            active_subs = overview_data['active_subscription_count'].iloc[0] if not overview_data.empty else 0
            st.metric("Active Subscriptions", 
                    f"{int(active_subs):,}", 
                    help="Number of currently active subscriptions in the selected billing period")
        except Exception:
            st.metric("Active Subscriptions", "0", help="Number of currently active subscriptions in the selected billing period")

    with col4:
        try:
            cancelled_subs = overview_data['cancelled_subscription_count'].iloc[0] if not overview_data.empty else 0
            st.metric("Cancelled Subscriptions", 
                    f"{int(cancelled_subs):,}", 
                    help="Number of Cancelled Subscriptions in the selected billing period")
        except Exception:
            st.metric("Cancelled Subscriptions", "0", help="Number of Cancelled Subscriptions in the selected billing period")

    with col5:
        try:
            new_subs = overview_data['net_new_subscription_count'].iloc[0] if not overview_data.empty else 0
            st.metric("Net New Subscriptions", 
                    f"{int(new_subs):,}", 
                    help="Number of new subscriptions in the selected billing period")
        except Exception:
            st.metric("Net New Subscriptions", "0", help="Number of new subscriptions in the selected billing period")

    with col6:
        try:
            renewals = overview_data['total_renewals'].iloc[0] if not overview_data.empty else 0
            st.metric("Renewals", 
                    f"{int(renewals):,}", 
                    help="Number of renewals in the selected billing period")
        except Exception:
            st.metric("Renewals", "0", help="Number of renewals in the selected billing period")

    with col7:
        try:
            product_changes = overview_data['total_product_changes'].iloc[0] if not overview_data.empty else 0
            st.metric("Product Changes", 
                    f"{int(product_changes):,}", 
                    help="Number of product changes in the selected billing period")
        except Exception:
            st.metric("Product Changes", "0", help="Number of product changes in the selected billing period")

    with col8:
        try:
            modifications = overview_data['total_modifications'].iloc[0] if not overview_data.empty else 0
            st.metric("Modifications", 
                    f"{int(modifications):,}", 
                    help="Number of modifications in the selected billing period")
        except Exception:
            st.metric("Modifications", "0", help="Number of modifications in the selected billing period")

    with col9:
        try:
            quantity_changes = overview_data['total_quantity_change'].iloc[0] if not overview_data.empty else 0
            st.metric("Quantity Changes", 
                    f"{int(quantity_changes):,}", 
                    help="Number of quantity changes in the selected billing period")
        except Exception:
            st.metric("Quantity Changes", "0", help="Number of quantity changes in the selected billing period")

    with col10:
        try:
            price_changes = overview_data['total_partner_buy_rate_changes'].iloc[0] if not overview_data.empty else 0
            st.metric("Price Changes", 
                    f"{int(price_changes):,}", 
                    help="Number of partner buy rate changes in the selected billing period")
        except Exception:
            st.metric("Price Changes", "0", help="Number of partner buy rate changes in the selected billing period")

    # Create line chart for subscription metrics over time
    st.subheader("Subscription Trends")
    
    try:
        # Get trend data using the new query
        query = Queries.load_subscription_overview_trends(billing_period=selected_period, vendor=selected_vendor)
        trend_data = db_util.query(query, {"billing_period": selected_period, "vendor": selected_vendor})
        
        if not trend_data.empty:
            # Convert transaction_month to datetime and set to first of month
            if 'transaction_month' in trend_data.columns:
                trend_data['transaction_month'] = pd.to_datetime(trend_data['transaction_month']).dt.to_period('M').dt.to_timestamp()
                trend_data = trend_data.set_index('transaction_month')
            
            # Select the metrics we want to display
            metrics_to_plot = {
                'active_subscription_count': 'Active',
                'net_new_subscription_count': 'New',
                'cancelled_subscription_count': 'Cancelled',
                'total_renewals': 'Renewals'
            }
            
            # Ensure all required columns exist
            available_metrics = {k: v for k, v in metrics_to_plot.items() if k in trend_data.columns}
            if not available_metrics:
                st.warning("No trend metrics available for plotting")
                return
                
            plot_data = trend_data[list(available_metrics.keys())].rename(columns=available_metrics)
            
            # Create tabs for different visualizations
            tab1, tab2, tab3, tab4 = st.tabs(["Line Chart", "Bar Chart", "Treemap", "Animated Bar Chart"])
            
            with tab1:
                # Line chart with log scale
                fig_line = px.line(plot_data, 
                    title="Subscription Metrics Over Time",
                    log_y=True,
                    markers=True,
                    template="plotly_white"
                )
                
                fig_line.update_layout(
                    height=400,
                    xaxis_title="Month",
                    yaxis_title="Count (Log Scale)",
                    legend_title="Metrics",
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                fig_line.update_traces(
                    hovertemplate="<b>%{y:,.0f}</b><br>"
                )
                
                st.plotly_chart(fig_line, use_container_width=True)
            
            with tab2:
                # Bar chart showing monthly values
                fig_bar = px.bar(plot_data,
                    title="Monthly Subscription Metrics",
                    barmode='group',
                    template="plotly_white"
                )
                
                fig_bar.update_layout(
                    height=400,
                    xaxis_title="Month",
                    yaxis_title="Count",
                    legend_title="Metrics",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                fig_bar.update_traces(
                    hovertemplate="<b>%{y:,.0f}</b><br>"
                )
                
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with tab3:
                # Treemap showing relative sizes and changes
                # Prepare data for treemap by melting the dataframe
                treemap_data = plot_data.reset_index().melt(
                    id_vars=['transaction_month'],
                    var_name='Metric',
                    value_name='Count'
                )
                
                # Check if we have any non-zero values and valid data
                total_value = treemap_data['Count'].sum()
                if total_value <= 0 or treemap_data.empty:
                    st.warning("No data available for treemap visualization - all values are zero or no data present")
                else:
                    # Filter out zero values to prevent normalization issues
                    treemap_data = treemap_data[treemap_data['Count'] > 0]
                    
                    if not treemap_data.empty:
                        fig_tree = px.treemap(
                            treemap_data,
                            path=[px.Constant("All"), 'Metric', 'transaction_month'],
                            values='Count',
                            title="Subscription Metrics Distribution",
                            template="plotly_white",
                            color='Count',
                            color_continuous_scale="RdYlBu"
                        )
                        
                        fig_tree.update_layout(
                            height=400,
                            margin=dict(t=50, l=25, r=25, b=25)
                        )
                        
                        fig_tree.update_traces(
                            hovertemplate="""
                            <b>%{label}</b><br>
                            Count: %{value:,.0f}<br>
                            <extra></extra>
                            """
                        )
                        
                        st.plotly_chart(fig_tree, use_container_width=True)
                    else:
                        st.warning("No non-zero values available for treemap visualization")
            
            with tab4:
                # Get historical data using load_subscription_overview_history
                query = Queries.load_subscription_overview_history(vendor=selected_vendor)
                history_data = db_util.query(query, {"vendor": selected_vendor})
                
                if not history_data.empty:
                    # Select metrics for animation
                    metrics_to_plot = {
                        'active_subscription_count': 'Active',
                        'net_new_subscription_count': 'New',
                        'cancelled_subscription_count': 'Cancelled',
                        'total_renewals': 'Renewals'
                    }
                    
                    # Prepare data for animation
                    animation_data = history_data.copy()
                    
                    # Ensure transaction_month is in datetime format and create Month-Year column
                    if 'transaction_month' in animation_data.columns:
                        animation_data['transaction_month'] = pd.to_datetime(animation_data['transaction_month'])
                        animation_data['Month-Year'] = animation_data['transaction_month'].dt.strftime('%Y-%m')
                    else:
                        st.warning("No transaction month data available for animation")
                        return
                    
                    # Select and rename columns for the plot
                    plot_columns = ['Month-Year'] + list(metrics_to_plot.keys())
                    animation_data = animation_data[plot_columns].rename(columns=metrics_to_plot)
                    
                    # Melt the data for animation
                    melted_data = pd.melt(
                        animation_data,
                        id_vars=['Month-Year'],
                        value_vars=['Active', 'New', 'Cancelled', 'Renewals'],
                        var_name='Metric',
                        value_name='Count'
                    )
                    
                    # Sort by Month-Year to ensure proper animation sequence
                    melted_data = melted_data.sort_values(['Month-Year', 'Metric'])
                    
                    # Create animated bar chart
                    fig_animated = px.bar(
                        melted_data,
                        y='Metric',
                        x='Count',
                        color='Metric',
                        animation_frame='Month-Year',
                        title='Subscription Metrics Over Time',
                        template='plotly_white',
                        orientation='h',
                        range_x=[0, melted_data['Count'].max() * 1.1]  # Set fixed range for all frames
                    )
                    
                    # Update layout
                    fig_animated.update_layout(
                        height=400,
                        yaxis_title='',
                        xaxis_title='Count',
                        showlegend=True,
                        legend_title='Metrics',
                        plot_bgcolor='white',
                        legend=dict(
                            orientation='h',
                            yanchor='bottom',
                            y=1.02,
                            xanchor='right',
                            x=1
                        ),
                        xaxis=dict(
                            gridcolor='lightgrey',
                            gridwidth=0.5,
                            showgrid=True,
                            zeroline=False,
                            title_standoff=15
                        ),
                        yaxis=dict(
                            gridcolor='lightgrey',
                            gridwidth=0.5,
                            showgrid=False,
                            autorange=True
                        ),
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    
                    # Update animation settings
                    fig_animated.update_traces(
                        hovertemplate='<b>%{y}</b><br>Count: %{x:,.0f}<br>'
                    )
                    
                    # Configure animation settings
                    fig_animated.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 1000
                    fig_animated.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 500
                    fig_animated.layout.updatemenus[0].buttons[0].args[1]['transition']['easing'] = 'cubic-in-out'
                    
                    # Add slider for manual frame selection
                    fig_animated.layout.sliders[0].update(
                        active=0,
                        yanchor='top',
                        xanchor='left',
                        currentvalue=dict(
                            font=dict(size=12),
                            prefix='Month: ',
                            visible=True,
                            xanchor='right'
                        )
                    )
                    
                    # Display the chart
                    st.plotly_chart(fig_animated, use_container_width=True)
                    
                    # Add animation controls explanation
                    st.caption("""
                    Animation Controls:
                    - Play/Pause: Start or stop the animation
                    - Previous/Next: Move between months manually
                    - Reset: Return to the first month
                    
                    The animation shows how subscription metrics change over time:
                    - Active: Total number of active subscriptions
                    - New: Net new subscriptions in the period
                    - Cancelled: Total cancelled subscriptions
                    - Renewals: Total subscription renewals
                    """)
                else:
                    st.warning("No historical data available for the selected criteria.")
        else:
            st.warning("No trend data available for the selected period.")
            
    except Exception as e:
        if 'SSL' in str(e) or '_ssl' in str(e):
            st.error("Database connection error: Unable to establish a secure connection. Please check your VPN connection and try again.")
        else:
            st.error(f"Error loading trend data: {str(e)}")

    
def show_subscription_details(subscription_id):
    subscription_data = load_subscription_metrics(subscription_id)
    if subscription_data.empty:
        st.error("No subscription found with the provided ID.")
        return

    original_subscription_id = subscription_data.iloc[0]['original_subscription_id']
    related_subscriptions = load_related_subscriptions(original_subscription_id)
    arrears_tasks = load_subscription_arrears_tasks(subscription_id)
    arrears_errors = load_subscription_arrears_errors(subscription_id)
    variance_data = calculate_revenue_variance(subscription_id)

    st.subheader("Subscription Overview")
    render_subscription_overview(subscription_data)

    st.subheader("Health Indicators")
    st.caption('''
        <p style="background-color: #e36877; padding: 10px; border-radius: 5px;">
           <b>Arrears tasks that are highlighted red indicate the usage or billing task error'd for this subscription. Reference the run_on and error_message for further information<b>
        </p>
    ''', unsafe_allow_html=True)
    render_arrears_tasks(arrears_tasks, arrears_errors)

    st.subheader("Revenue Analysis")
    render_revenue_variance(variance_data)

    st.subheader("Related Subscriptions")
    st.dataframe(
        related_subscriptions,
        column_config={
            "id": st.column_config.NumberColumn("subscription_id"),
            "status": st.column_config.TextColumn("Status"),
            "quantity": st.column_config.NumberColumn("Quantity"),
            "start_date": st.column_config.DateColumn("Start Date"),
            "end_date": st.column_config.DateColumn("End Date"),
            "monthly_revenue": st.column_config.NumberColumn(
                "Monthly Revenue",
                format="$%.2f",
                help="Gross revenue divided by term in months"
            ),
        },
        hide_index=True,
    )

def show_subscription_list(invoice_id=None, subscription_id=None):

    if invoice_id is not None:
        if isinstance(invoice_id, str) and invoice_id.isdigit():
            invoice_id = int(invoice_id)
        elif isinstance(invoice_id, str):
            invoice_id = str(invoice_id)
        elif not isinstance(invoice_id, (str, int)):
            st.error("Invalid Invoice ID format. Must be a string or an integer.")
            return

    if subscription_id is not None:
        subscriptions = load_subscriptions_by_invoice(subscription_id)

    try:
        subscriptions = load_subscriptions_by_invoice(invoice_id, subscription_id)
    except ValueError as e:
        st.error(str(e))
        return

    if subscriptions.empty:
        st.error("No subscriptions found for the provided criteria.")
        return

    st.dataframe(
        highlight_error_rows(subscriptions),
        column_config={
            "id": st.column_config.NumberColumn(
                "ID",
                help="Click a subscription ID to view details"
            ),
            "status": st.column_config.TextColumn("Status"),
            "has_arrears": st.column_config.CheckboxColumn(
                "Has Arrears",
                help="Whether this subscription has any arrears tasks"
            ),
            "quantity": st.column_config.NumberColumn("Quantity"),
            "start_date": st.column_config.DateColumn("Start Date"),
            "end_date": st.column_config.DateColumn("End Date"),
            "partner_name": st.column_config.TextColumn("Partner"),
            "product_name": st.column_config.TextColumn("Product"),
            "monthly_revenue": st.column_config.NumberColumn(
                "Monthly Revenue",
                format="$%.2f",
                help="Gross revenue divided by term in months"
            ),
        },
        hide_index=True,
    )
    if subscription_id is not None:
        selected_subscription = subscription_id
    else:
        selected_subscription = st.selectbox(
            "Select a subscription to view details",
            options=subscriptions['id'].tolist(),
            format_func=lambda
                x: f"Subscription {x} ({subscriptions.loc[subscriptions['id'] == x]['product_name'].iloc[0]})"
        )

    if selected_subscription:
        show_subscription_details(selected_subscription)

def render_subscription_overview_tiles(overview_data):
    """Render overview tiles with key subscription metrics"""
    if overview_data.empty:
        st.info("No subscription overview data available.")
        return

    # Calculate metrics with safe defaults for empty data
    total_subs = len(overview_data) if not overview_data.empty else 0
    active_subs = len(overview_data[overview_data['status'] == 'Active']) if not overview_data.empty else 0
    total_revenue = overview_data['monthly_revenue'].sum() if not overview_data.empty else 0
    avg_revenue = overview_data['monthly_revenue'].mean() if not overview_data.empty else 0
    churn_rate = (len(overview_data[overview_data['status'] == 'Cancelled']) / total_subs * 100) if total_subs > 0 else 0

    # Create 5 tiles in a row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Subscriptions",
            f"{total_subs:,}",
            help="Total number of subscriptions"
        )
    
    with col2:
        st.metric(
            "Active Subscriptions",
            f"{active_subs:,}",
            # f"{(active_subs/total_subs*100):.1f}%",
            help="Number of Active Subscriptions"
        )
    
    with col3:
        st.metric(
            "Total Monthly Revenue",
            f"${total_revenue:,.2f}",
            help="Sum of all monthly subscription revenue"
        )
    
    with col4:
        st.metric(
            "Average Revenue",
            f"${avg_revenue:,.2f}",
            help="Average revenue per subscription"
        )
    
    with col5:
        st.metric(
            "Churn Rate",
            f"{churn_rate:.1f}%",
            help="Percentage of cancelled subscriptions"
        )

def show_subscription_details_page():
    auth_util.auth_for(ROLES)

    st.title("Subscription Metrics Overview ")
    st.write("This page can be used to view summary metrics about all subscriptions.")
    
    st.subheader("Requests for Feedback")
    st.write("This product is under construction.")
    
    st.markdown('''
        <p style="background-color: #ebe54d; padding: 10px; border-radius: 5px;">
            <b>For any feedback or feature request on this page or the subscription models, please submit a product request to the MOG OIA channel through Product Assistance</b><br><br>
            <b>Slack Link:</b> <a href="https://pax8.enterprise.slack.com/archives/C07P3HUKG0L" target="_blank">@https://pax8.enterprise.slack.com/archives/C07P3HUKG0L</a>
        </p>
    ''', unsafe_allow_html=True)
    
    render_subscription_summary()
    
    st.write("---")  # Add separator
    st.title("Subscription Details")
    
    st.write("Enter a subscription ID to view its details. Enter an invoice ID to view subscriptions related to that invoice.")

    col1, col2 = st.columns(2)

    with col1:
        subscription_id = st.text_input("Subscription ID", key="subscription_id_input")

    with col2:
        invoice_id = st.text_input("Invoice ID")

    if subscription_id and invoice_id:
        st.subheader("Subscription and Invoice Details")
        st.caption('''
            <p style="background-color: #ebe54d; padding: 10px; border-radius: 5px;">
                <b>Invoice rows that are highlighted yellow indicate a rate plan change occurred for the charge from the first of last month to today.<b>
            </p>
        ''', unsafe_allow_html=True)
        show_subscription_list(invoice_id=invoice_id, subscription_id=int(subscription_id))

    elif subscription_id:
        st.subheader("Subscription and Invoice Details")
        show_subscription_list(subscription_id=int(subscription_id))

    elif invoice_id:
        st.subheader("Subscriptions on Invoice")
        st.caption('''
            <p style="background-color: #ebe54d; padding: 10px; border-radius: 5px;">
                <b>Invoice rows that are highlighted yellow indicate a rate plan change occurred for the charge from the first of last month to today.<b>
            </p>
        ''', unsafe_allow_html=True)

        show_subscription_list(invoice_id=invoice_id)

    
    st.warning("""
               This page is considered a PROTOTYPE and should NOT be expected to work correctly for CORE FUNCTIONALITY.

               This page is considered a PROTOTYPE and should NOT be expected to work correctly in ANY EDGE CASES.
               
               This page is considered a PROTOTYPE and should NOT be expected to work correctly in PRODUCTION ENVIRONMENTS.
               
               This page is considered a PROTOTYPE and should NOT be expected to present a reusable analytics layer.
               """)


if __name__ == "__page__":
    show_subscription_details_page()
