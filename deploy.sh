#!/bin/bash

# Azure Functions Deployment Script for Delta Share
set -e

# Configuration
RESOURCE_GROUP="deltashare-rg"
LOCATION="westus"
STORAGE_NAME="deltashare$(date +%s)"
FUNCTION_APP_NAME="deltashare-functions-$(date +%s)"

echo "🚀 Starting Azure Functions deployment..."
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Storage Account: $STORAGE_NAME"
echo "Function App: $FUNCTION_APP_NAME"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first:"
    echo "macOS: brew install azure-cli"
    echo "Windows: Download from https://aka.ms/installazurecliwindows"
    echo "Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run: az login"
    exit 1
fi

echo "✅ Azure CLI found and logged in"
echo ""

# Create resource group
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION --output table
echo ""

# Create storage account
echo "💾 Creating storage account..."
az storage account create \
    --name $STORAGE_NAME \
    --location $LOCATION \
    --resource-group $RESOURCE_GROUP \
    --sku Standard_LRS \
    --output table
echo ""

# Create function app
echo "⚡ Creating function app with Flex Consumption..."
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --storage-account $STORAGE_NAME \
    --runtime python \
    --runtime-version 3.11 \
    --functions-version 4 \
    --os-type linux \
    --sku FC1 \
    --location $LOCATION \
    --output table
echo ""

# Wait for function app to be ready
echo "⏳ Waiting for function app to be ready..."
sleep 30

# Deploy function code
echo "🚀 Deploying function code..."
if command -v func &> /dev/null; then
    func azure functionapp publish $FUNCTION_APP_NAME --python
else
    echo "❌ Azure Functions Core Tools not found. Please install it:"
    echo "npm install -g azure-functions-core-tools@4 --unsafe-perm true"
    exit 1
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Summary:"
echo "  • Resource Group: $RESOURCE_GROUP"
echo "  • Function App: $FUNCTION_APP_NAME"
echo "  • URL: https://$FUNCTION_APP_NAME.azurewebsites.net"
echo ""
echo "🔗 Available endpoints:"
echo "  • Health: https://$FUNCTION_APP_NAME.azurewebsites.net/api/health"
echo "  • Metadata: https://$FUNCTION_APP_NAME.azurewebsites.net/api/metadata"
echo "  • Download: https://$FUNCTION_APP_NAME.azurewebsites.net/api/download"
echo ""
echo "🧪 Test with:"
echo "curl https://$FUNCTION_APP_NAME.azurewebsites.net/api/health"