import pandas as pd
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_order_manager_file(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Generates a transaction file for the Order Manager.
    Validates required columns and transforms the data into the required format.
    
    Args:
        df (pd.DataFrame): Input DataFrame with required columns
        
    Returns:
        Optional[pd.DataFrame]: Transformed DataFrame with renamed columns and calculations
    """
    try:
        logger.info(f"Starting transformation with DataFrame shape: {df.shape}")
        
        required_columns = [
            'company_name',
            'successor_subscription_start_date',
            'estimated_billing_start_period',
            'estimated_billing_end_period',
            'product_unit_of_measure',
            'successor_rate_plan_type',
            'charge_type',
            'actual_retail_price',
            'partner_buy_rate',
            'wholesale_buy_rate',
            'completed_order_purchase_order_number',
            'currency_guid',
            'completed_line_item_guid',
            'subscription_guid',
            'original_subscription_guid',
            'product_uuid',
            'product_vendor_uuid',
            'product_name',
            'completed_line_item_sku',
            'successor_term',
            'is_flat_rate',
            'current_subscription_quantity',
            'partner_guid',
            'company_guid',
            'transaction_month',
            'successor_commitment_term_end_date'
        ]

        missing_cols = set(required_columns) - set(df.columns)
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            logger.info(f"Available columns: {df.columns.tolist()}")
            raise ValueError(f"Missing required columns: {missing_cols}")

        # format the dataframe from missing subscription to the order manager uploader 
        order_manager_upload_df = pd.DataFrame({
            'companyName': df['company_name'],
            'orderDate': pd.to_datetime(df['successor_subscription_start_date']).dt.strftime('%Y-%m-%d'),
            'serviceStart': pd.to_datetime(df['estimated_billing_start_period']).dt.strftime('%Y-%m-%d'),
            'startPeriod': pd.to_datetime(df['estimated_billing_start_period']).dt.strftime('%Y-%m-%d'),
            'endPeriod': pd.to_datetime(df['estimated_billing_end_period']).dt.strftime('%Y-%m-%d'),
            'unitOfMeasure': df['product_unit_of_measure'],
            'description': df['product_name'],
            'bobDescription': df['product_name'],
            'descriptionExtras': '',
            'rateType': df['successor_rate_plan_type'],
            'chargeType': df['charge_type'],
            'price': pd.to_numeric(df['actual_retail_price'], errors='coerce').round(4),
            'total': (pd.to_numeric(df['actual_retail_price'], errors='coerce') * 
                     pd.to_numeric(df['current_subscription_quantity'], errors='coerce')).round(4),
            'cost': pd.to_numeric(df['partner_buy_rate'], errors='coerce').round(4),
            'costTotal': (pd.to_numeric(df['partner_buy_rate'], errors='coerce') * 
                        pd.to_numeric(df['current_subscription_quantity'], errors='coerce')).round(4),
            'pax8Cost': pd.to_numeric(df['wholesale_buy_rate'], errors='coerce').round(4),
            'pax8CostTotal': (pd.to_numeric(df['wholesale_buy_rate'], errors='coerce') * 
                             pd.to_numeric(df['current_subscription_quantity'], errors='coerce')).round(4),
            'offeredBy': 'Pax8',
            'purchaseOrderNumber': df['completed_order_purchase_order_number'],
            'details': '',
            'currencyId': df['currency_guid'],
            'completedLineItemId': df['completed_line_item_guid'],
            'subscriptionId': df['subscription_guid'],
            'originalSubscriptionGuid': df['original_subscription_guid'],
            'productUUID': df['product_uuid'],
            'productName': df['product_name'],
            'productVendorId': df['product_vendor_uuid'],
            'sku': df['completed_line_item_sku'],
            'term': df['successor_term'],
            'ratePlanType': df['successor_rate_plan_type'],
            'isFlatRate': df['is_flat_rate'],
            'quantity': pd.to_numeric(df['current_subscription_quantity'], errors='coerce'),
            'partnerId': df['partner_guid'],
            'companyId': df['company_guid'],
            'invoiceDate': pd.to_datetime(df['transaction_month']).dt.strftime('%Y-%m-%d'),
            'type': 'subscription',
            'billingRenewal': pd.to_datetime(df['successor_commitment_term_end_date']).dt.strftime('%Y-%m-%d')
        })


        order_manager_upload_df_deduplicated = order_manager_upload_df.drop_duplicates(
                subset=['completedLineItemId', 
                        'subscriptionId', 
                        'originalSubscriptionGuid'], keep='first')
        
        duplicates_removed = len(order_manager_upload_df) - len(order_manager_upload_df_deduplicated)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate records from order manager file")

        return order_manager_upload_df_deduplicated

    except Exception as e:
        logger.error(f"Error in generate_order_manager_file: {str(e)}")
        raise


    
    




