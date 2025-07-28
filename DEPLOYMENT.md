# Azure Functions Deployment Guide

## Prerequisites

### 1. Install Azure CLI
```bash
# macOS
brew install azure-cli

# Windows (PowerShell)
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi; Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### 2. Login to Azure
```bash
az login
```

### 3. Set your subscription (if you have multiple)
```bash
az account list --output table
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

## Deployment Steps

### 1. Create Resource Group
```bash
az group create --name deltashare-rg --location eastus
```

### 2. Create Storage Account
```bash
az storage account create \
    --name deltasharestorage$(date +%s) \
    --location eastus \
    --resource-group deltashare-rg \
    --sku Standard_LRS
```

### 3. Create Function App
```bash
az functionapp create \
    --resource-group deltashare-rg \
    --consumption-plan-location eastus \
    --runtime python \
    --runtime-version 3.11 \
    --functions-version 4 \
    --name deltashare-functions-$(date +%s) \
    --storage-account deltasharestorage$(date +%s) \
    --os-type linux
```

### 4. Deploy Function Code
```bash
# Make sure you're in the project directory
cd /path/to/your/deltashare/project

# Deploy using Azure Functions Core Tools
func azure functionapp publish deltashare-functions-YOUR_UNIQUE_ID
```

## Alternative: One-Command Deployment

You can also use this automated script that creates everything at once:

```bash
#!/bin/bash

# Set variables
RESOURCE_GROUP="deltashare-rg"
LOCATION="eastus"
STORAGE_NAME="deltashare$(date +%s)"
FUNCTION_APP_NAME="deltashare-functions-$(date +%s)"

echo "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

echo "Creating storage account..."
az storage account create \
    --name $STORAGE_NAME \
    --location $LOCATION \
    --resource-group $RESOURCE_GROUP \
    --sku Standard_LRS

echo "Creating function app..."
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --consumption-plan-location $LOCATION \
    --runtime python \
    --runtime-version 3.11 \
    --functions-version 4 \
    --name $FUNCTION_APP_NAME \
    --storage-account $STORAGE_NAME \
    --os-type linux

echo "Deploying functions..."
func azure functionapp publish $FUNCTION_APP_NAME

echo "Deployment complete!"
echo "Function App URL: https://$FUNCTION_APP_NAME.azurewebsites.net"
```

## Testing Deployed Functions

Once deployed, you need to get your function key and update the web interface:

### 1. Get Function Key
```bash
# Get your function authentication key
az functionapp keys list --name YOUR_FUNCTION_APP --resource-group deltashare-rg
```

### 2. Update Web Interface Function Key
**IMPORTANT**: After deployment, you must update the function key in the web interface:

1. In `function_app.py`, find line ~301:
   ```javascript
   const functionKey = 'YOUR_FUNCTION_KEY_HERE';
   ```

2. Replace `YOUR_FUNCTION_KEY_HERE` with your actual function key from step 1

3. Redeploy the function:
   ```bash
   func azure functionapp publish YOUR_FUNCTION_APP --python
   ```

### 3. Test Endpoints
```bash
# Health check (replace YOUR_FUNCTION_KEY with actual key)
curl "https://YOUR_FUNCTION_APP.azurewebsites.net/api/health?code=YOUR_FUNCTION_KEY"

# Web interface (replace YOUR_FUNCTION_KEY with actual key)
https://YOUR_FUNCTION_APP.azurewebsites.net/api/web_interface?code=YOUR_FUNCTION_KEY

# Metadata endpoint
curl -X POST "https://YOUR_FUNCTION_APP.azurewebsites.net/api/metadata?code=YOUR_FUNCTION_KEY" \
    -H "Content-Type: application/octet-stream" \
    --data-binary "mock config content"

# Download endpoint
curl -X POST "https://YOUR_FUNCTION_APP.azurewebsites.net/api/download?code=YOUR_FUNCTION_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "config": "mock config",
        "share": "delta_sharing", 
        "schema": "default",
        "table": "trips"
    }'
```

## Configuration for Production

### Environment Variables
Set these in the Azure portal under Function App > Configuration:

- `AZURE_STORAGE_CONNECTION_STRING` - For file storage
- `DELTA_SHARING_CONFIG_CONTAINER` - Container name for config files

### Authentication
Enable authentication in Azure portal:
1. Go to Function App > Authentication
2. Add identity provider (Azure AD, etc.)
3. Set authentication level in `function_app.py`

## Cost Optimization

- Use **Consumption Plan** for sporadic usage
- Use **Premium Plan** for consistent traffic
- Monitor costs in Azure Cost Management

## Monitoring

- View logs in Azure Portal > Function App > Monitor
- Set up Application Insights for detailed telemetry
- Create alerts for failures or performance issues

## Security Best Practices

1. **Use Function Keys**: Generate and use function keys for API access
2. **Enable HTTPS Only**: Force HTTPS in Function App settings
3. **Network Security**: Configure VNet integration if needed
4. **Secrets Management**: Use Azure Key Vault for sensitive data
5. **CORS Configuration**: Set up CORS for web applications

## Troubleshooting

### Common Issues:
1. **Deployment fails**: Check Python version compatibility
2. **Functions not loading**: Verify requirements.txt includes all dependencies
3. **Authentication errors**: Check function authorization level
4. **Timeout errors**: Increase function timeout in host.json

### Debug Commands:
```bash
# Check function status
func azure functionapp show deltashare-functions-YOUR_ID

# Stream logs
func azure functionapp logstream deltashare-functions-YOUR_ID

# Check deployment status
az functionapp deployment list --name deltashare-functions-YOUR_ID --resource-group deltashare-rg
```