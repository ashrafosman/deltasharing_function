import azure.functions as func
import delta_sharing
import pandas as pd
import tempfile
import os
import json
import logging
from io import StringIO

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="metadata", methods=["POST"])
def get_metadata(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing metadata request')
    
    try:
        # Get the config file content from request body
        config_content = req.get_body()
        
        if not config_content:
            return func.HttpResponse(
                json.dumps({"error": "No config file provided"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Save config temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".share") as temp_config:
            temp_config.write(config_content)
            temp_config_path = temp_config.name
        
        try:
            # Create Delta Sharing client
            client = delta_sharing.SharingClient(temp_config_path)
            
            # Get all available tables
            all_tables = client.list_all_tables()
            
            # Organize data by share -> schema -> tables
            metadata = {}
            for table in all_tables:
                share_name = table.share
                schema_name = table.schema
                table_name = table.name
                
                if share_name not in metadata:
                    metadata[share_name] = {}
                if schema_name not in metadata[share_name]:
                    metadata[share_name][schema_name] = []
                
                metadata[share_name][schema_name].append(table_name)
            
            return func.HttpResponse(
                json.dumps(metadata),
                status_code=200,
                mimetype="application/json"
            )
            
        finally:
            # Clean up temp file
            os.remove(temp_config_path)
            
    except Exception as e:
        logging.error(f"Error processing metadata request: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="download", methods=["POST"])
def download_data(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing download request')
    
    try:
        # Parse request JSON
        req_json = req.get_json()
        
        if not req_json:
            return func.HttpResponse(
                json.dumps({"error": "Invalid request body"}),
                status_code=400,
                mimetype="application/json"
            )
        
        config_content = req_json.get('config')
        share = req_json.get('share')
        schema = req_json.get('schema')
        table = req_json.get('table')
        
        if not all([config_content, share, schema, table]):
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameters: config, share, schema, table"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Save config temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".share") as temp_config:
            temp_config.write(config_content.encode())
            temp_config_path = temp_config.name
        
        try:
            # Construct table URL
            table_url = f"{temp_config_path}#{share}.{schema}.{table}"
            
            # Load data as pandas DataFrame
            df = delta_sharing.load_as_pandas(table_url)
            
            # Convert to CSV
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()
            
            return func.HttpResponse(
                csv_content,
                status_code=200,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={table}.csv"
                }
            )
            
        finally:
            # Clean up temp file
            os.remove(temp_config_path)
            
    except Exception as e:
        logging.error(f"Error processing download request: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"status": "healthy", "message": "Azure Functions is running"}),
        status_code=200,
        mimetype="application/json"
    )

@app.route(route="web_interface", methods=["GET"])
def web_interface(req: func.HttpRequest) -> func.HttpResponse:
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Delta Sharing Data Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            max-width: 900px; 
            margin: 0 auto; 
            padding: 20px; 
            background: #f8f9fa;
        }
        .container { 
            background: white; 
            padding: 40px; 
            border-radius: 12px; 
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #2c3e50; 
            text-align: center; 
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
        }
        button { 
            background: #3498db; 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 14px;
            font-weight: 500;
            transition: background 0.2s;
        }
        button:hover { background: #2980b9; }
        button:disabled { background: #bdc3c7; cursor: not-allowed; }
        select, input[type="file"] { 
            width: 100%; 
            padding: 12px; 
            margin: 10px 0; 
            border: 2px solid #e1e8ed; 
            border-radius: 8px; 
            font-size: 14px;
            box-sizing: border-box;
        }
        select:focus, input:focus {
            outline: none;
            border-color: #3498db;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #2c3e50;
        }
        .result { 
            margin-top: 25px; 
            padding: 20px; 
            border-radius: 8px; 
            font-weight: 500;
        }
        .success { background: #d5f4e6; color: #2d7d32; border-left: 4px solid #4caf50; }
        .error { background: #ffebee; color: #c62828; border-left: 4px solid #f44336; }
        .info { background: #e3f2fd; color: #1565c0; border-left: 4px solid #2196f3; }
        .step {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #3498db;
        }
        .step h3 {
            margin-top: 0;
            color: #2c3e50;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .note {
            background: #fff3cd;
            color: #856404;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔄 Delta Sharing Data Downloader</h1>
        <p class="subtitle">Upload your config.share file to browse and download Delta tables</p>
        
        <div class="note">
            <strong>🔥 Production Version:</strong> This version connects to real Delta Sharing endpoints. Upload your actual .share configuration file to access your data.
        </div>
        
        <div class="step">
            <h3>Step 1: Upload Configuration</h3>
            <div class="form-group">
                <label for="configFile">Choose your config.share file:</label>
                <input type="file" id="configFile" accept=".share" />
            </div>
            <button onclick="loadMetadata()" id="loadBtn">Load Available Tables</button>
        </div>
        
        <div id="tablesStep" class="step" style="display:none;">
            <h3>Step 2: Select Table</h3>
            <div class="form-group">
                <label for="shareSelect">Share:</label>
                <select id="shareSelect" onchange="updateSchemas()">
                    <option>Select Share...</option>
                </select>
            </div>
            <div class="form-group">
                <label for="schemaSelect">Schema:</label>
                <select id="schemaSelect" onchange="updateTables()">
                    <option>Select Schema...</option>
                </select>
            </div>
            <div class="form-group">
                <label for="tableSelect">Table:</label>
                <select id="tableSelect">
                    <option>Select Table...</option>
                </select>
            </div>
            <button onclick="downloadData()" id="downloadBtn">Download CSV</button>
        </div>
        
        <div id="result" class="result" style="display:none;"></div>
    </div>

    <script>
        let metadata = {};
        const functionKey = 'YOUR_FUNCTION_KEY_HERE';
        
        async function loadMetadata() {
            const fileInput = document.getElementById('configFile');
            const file = fileInput.files[0];
            const loadBtn = document.getElementById('loadBtn');
            const resultDiv = document.getElementById('result');
            
            if (!file) {
                resultDiv.className = 'result error';
                resultDiv.innerHTML = '❌ Please select a config.share file';
                resultDiv.style.display = 'block';
                return;
            }
            
            loadBtn.innerHTML = '<div class="loading"></div>Loading...';
            loadBtn.disabled = true;
            
            try {
                const response = await fetch(`/api/metadata?code=${functionKey}`, {
                    method: 'POST',
                    body: await file.arrayBuffer()
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                    try {
                        const errorJson = JSON.parse(errorText);
                        if (errorJson.error) {
                            errorMessage = errorJson.error;
                        }
                    } catch (e) {
                        // Use default error message
                    }
                    throw new Error(errorMessage);
                }
                
                metadata = await response.json();
                populateShares();
                document.getElementById('tablesStep').style.display = 'block';
                
                resultDiv.className = 'result success';
                resultDiv.innerHTML = '✅ Configuration loaded successfully! Select a table below to download.';
                resultDiv.style.display = 'block';
                
            } catch (error) {
                resultDiv.className = 'result error';
                resultDiv.innerHTML = `❌ Error loading configuration: ${error.message}`;
                resultDiv.style.display = 'block';
            } finally {
                loadBtn.innerHTML = 'Load Available Tables';
                loadBtn.disabled = false;
            }
        }
        
        function populateShares() {
            const shareSelect = document.getElementById('shareSelect');
            shareSelect.innerHTML = '<option>Select Share...</option>';
            
            Object.keys(metadata).forEach(share => {
                const option = document.createElement('option');
                option.value = share;
                option.textContent = share;
                shareSelect.appendChild(option);
            });
        }
        
        function updateSchemas() {
            const shareSelect = document.getElementById('shareSelect');
            const schemaSelect = document.getElementById('schemaSelect');
            const share = shareSelect.value;
            
            schemaSelect.innerHTML = '<option>Select Schema...</option>';
            document.getElementById('tableSelect').innerHTML = '<option>Select Table...</option>';
            
            if (share && share !== 'Select Share...' && metadata[share]) {
                Object.keys(metadata[share]).forEach(schema => {
                    const option = document.createElement('option');
                    option.value = schema;
                    option.textContent = schema;
                    schemaSelect.appendChild(option);
                });
            }
        }
        
        function updateTables() {
            const shareSelect = document.getElementById('shareSelect');
            const schemaSelect = document.getElementById('schemaSelect');
            const tableSelect = document.getElementById('tableSelect');
            const share = shareSelect.value;
            const schema = schemaSelect.value;
            
            tableSelect.innerHTML = '<option>Select Table...</option>';
            
            if (share && schema && share !== 'Select Share...' && schema !== 'Select Schema...' 
                && metadata[share] && metadata[share][schema]) {
                metadata[share][schema].forEach(table => {
                    const option = document.createElement('option');
                    option.value = table;
                    option.textContent = table;
                    tableSelect.appendChild(option);
                });
            }
        }
        
        async function downloadData() {
            const share = document.getElementById('shareSelect').value;
            const schema = document.getElementById('schemaSelect').value;
            const table = document.getElementById('tableSelect').value;
            const fileInput = document.getElementById('configFile');
            const file = fileInput.files[0];
            const downloadBtn = document.getElementById('downloadBtn');
            const resultDiv = document.getElementById('result');
            
            if (!share || !schema || !table || !file || 
                share === 'Select Share...' || schema === 'Select Schema...' || table === 'Select Table...') {
                resultDiv.className = 'result error';
                resultDiv.innerHTML = '❌ Please select share, schema, table and ensure config file is uploaded';
                resultDiv.style.display = 'block';
                return;
            }
            
            downloadBtn.innerHTML = '<div class="loading"></div>Downloading...';
            downloadBtn.disabled = true;
            
            try {
                const config = await file.text();
                
                const response = await fetch(`/api/download?code=${functionKey}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        config: config,
                        share: share,
                        schema: schema,
                        table: table
                    })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${table}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    
                    resultDiv.className = 'result success';
                    resultDiv.innerHTML = `✅ Successfully downloaded ${table}.csv!`;
                } else {
                    const errorText = await response.text();
                    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                    try {
                        const errorJson = JSON.parse(errorText);
                        if (errorJson.error) {
                            errorMessage = errorJson.error;
                        }
                    } catch (e) {
                        // Use default error message
                    }
                    throw new Error(errorMessage);
                }
            } catch (error) {
                resultDiv.className = 'result error';
                resultDiv.innerHTML = `❌ Download failed: ${error.message}`;
            } finally {
                downloadBtn.innerHTML = 'Download CSV';
                downloadBtn.disabled = false;
                resultDiv.style.display = 'block';
            }
        }
    </script>
</body>
</html>
    """
    
    return func.HttpResponse(html_content, mimetype="text/html")