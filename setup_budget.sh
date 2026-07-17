#!/usr/bin/env zsh

echo "🔍 Identifying active Cloud Billing Account..."
# Automatically fetch the first open Billing Account ID associated with your user
BILLING_ACCOUNT_ID=$(gcloud billing accounts list --filter="open=true" --format="value(name)" | head -n 1 | awk -F'/' '{print $2}')

if [ -z "$BILLING_ACCOUNT_ID" ]; then
    echo "❌ Error: No open Billing Account found. Please check 'gcloud auth login'."
    exit 1
fi

echo "✅ Found Billing Account: $BILLING_ACCOUNT_ID"
echo "⚙️  Creating $5.00 monthly budget with alerts at 50%, 90%, and 100%..."

# Enable the required Billing Budget API
gcloud services enable billingbudgets.googleapis.com

# Create the $5 budget with multi-tier alerts
gcloud billing budgets create \
    --billing-account="$BILLING_ACCOUNT_ID" \
    --display-name="Hard Cap - $5 Monthly Alert" \
    --budget-amount=5.00USD \
    --calendar-period=month \
    --threshold-rule=percent=0.50,basis=current-spend \
    --threshold-rule=percent=0.90,basis=current-spend \
    --threshold-rule=percent=1.00,basis=current-spend

echo "🎉 Success! Budget alert created. You will receive standard email notifications if spending crosses these thresholds."
