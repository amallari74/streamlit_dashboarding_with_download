import sys
import os
from datetime import datetime
import streamlit as st
import pandas as pd

# Set up PYTHONPATH to include src directory
os.environ['PYTHONPATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.jira_service import JiraService

def test_create_basic_ticket():
    """Test creating a basic Jira ticket without custom fields"""
    jira_service = JiraService()
    
    # Basic ticket info
    ticket_url = jira_service.create_ticket(
        project_key="MOG",
        summary="Test Ticket - Basic Creation",
        description="This is a test ticket created by the automated test script",
        issue_type="Task",
        labels=["test", "automated_test"],
        components=["Billing"]
    )
    
    print(f"Basic ticket creation {'succeeded' if ticket_url else 'failed'}")
    if ticket_url:
        print(f"Ticket URL: {ticket_url}")

def test_create_ticket_with_custom_fields():
    """Test creating a Jira ticket with custom fields"""
    jira_service = JiraService()
    
    # Create test data
    test_data = pd.DataFrame({
        'partner_info': ['Partner1', 'Partner2'],
        'subscription_id': [123, 456]
    })
    
    # Get counts for custom fields
    unique_partners = test_data['partner_info'].nunique()
    unique_subscriptions = test_data['subscription_id'].nunique()
    
    # Create ticket with custom fields
    ticket_url = jira_service.create_ticket(
        project_key="MOG",
        summary=f"Test Ticket - Custom Fields - {datetime.now().strftime('%Y-%m-%d')}",
        description="Test ticket with custom fields",
        issue_type="Task",
        labels=["test", "automated_test"],
        components=["Billing"],
        customfield_10371=["TestVendor"],  # Vendor field
        customfield_10372=unique_partners,  # Partners Impacted
        customfield_10373=unique_subscriptions  # Subscriptions Impacted
    )
    
    print(f"Custom fields ticket creation {'succeeded' if ticket_url else 'failed'}")
    if ticket_url:
        print(f"Ticket URL: {ticket_url}")

def test_create_ticket_with_table():
    """Test creating a Jira ticket with a table in the description"""
    jira_service = JiraService()
    
    # Create test data
    test_data = pd.DataFrame({
        'Region': ['NA', 'EU'],
        'Partner': ['Partner1', 'Partner2'],
        'Error': ['Test Error 1', 'Test Error 2']
    })
    
    # Convert DataFrame to Jira table format
    headers = "||" + "||".join(test_data.columns) + "||"
    rows = []
    for _, row in test_data.iterrows():
        row_str = "|" + "|".join(str(val) for val in row) + "|"
        rows.append(row_str)
    
    table = f"{headers}\n{chr(10).join(rows)}"
    
    # Create description with table
    description = f"""
h2. Test Table
{table}

h2. Additional Information
* Test Date: {datetime.now().strftime('%Y-%m-%d')}
* Test Type: Automated Test
"""
    
    # Create ticket
    ticket_url = jira_service.create_ticket(
        project_key="MOG",
        summary=f"Test Ticket - Table Format - {datetime.now().strftime('%Y-%m-%d')}",
        description=description,
        issue_type="Task",
        labels=["test", "automated_test"],
        components=["Billing"]
    )
    
    print(f"Table format ticket creation {'succeeded' if ticket_url else 'failed'}")
    if ticket_url:
        print(f"Ticket URL: {ticket_url}")

def run_all_tests():
    """Run all test cases"""
    print("Starting Jira ticket creation tests...")
    print("\n1. Testing basic ticket creation:")
    test_create_basic_ticket()
    
    print("\n2. Testing ticket creation with custom fields:")
    test_create_ticket_with_custom_fields()
    
    print("\n3. Testing ticket creation with table format:")
    test_create_ticket_with_table()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    run_all_tests()