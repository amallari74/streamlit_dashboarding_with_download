#!/bin/bash

# Exit on error
set -e

echo "Setting up Marketplace Operations Insights..."

# Check if Python 3.11 is installed (via Homebrew)
if ! command -v /opt/homebrew/opt/python@3.11/bin/python3.11 &> /dev/null; then
    echo "Python 3.11 not found. Please install it with: brew install python@3.11"
    exit 1
fi

# Create virtual environment with Python 3.11
echo "Creating virtual environment with Python 3.11..."
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install psycopg2  # Ensure both psycopg2 and psycopg2-binary are installed

# Set up secrets
echo "Setting up secrets..."
mkdir -p .streamlit
cp secrets.toml.example .streamlit/secrets.toml

echo ""
echo "Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Configure database connections in .streamlit/secrets.toml:"
echo ""
echo "   For PostgreSQL read replica (RECOMMENDED):"
echo "   [connections.postgresql]"
echo "   type = \"sql\""
echo "   url = \"postgresql://<user>:<password>@<read_replica_host>:5432/<database>?sslmode=require\""
echo ""
echo "   For Redshift (fallback):"
echo "   Format: redshift+redshift_connector://<user>:<password>@<db_url>:5439/pax8dw?sslmode=prefer"
echo ""
echo "2. Set the app password in .streamlit/secrets.toml under [auth] -> app_password"
echo ""
echo "3. Configure Auth0 and Jira credentials in .streamlit/secrets.toml"
echo ""
echo "4. Start the application with: streamlit run src/app.py"
echo ""
echo "💡 TIP: The app will automatically prefer PostgreSQL over Redshift when both are configured."
echo "📖 See LOCAL_SETUP_GUIDE.md for detailed setup instructions." 