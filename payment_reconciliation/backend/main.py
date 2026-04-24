from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import io
import os
import json

from data.generator import generate_datasets
from model.reconciliation import reconcile

app = FastAPI(title="Payment Reconciliation API")

# Configure CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Payment Reconciliation API is running"}

@app.get("/api/generate")
def api_generate_data():
    try:
        df_p, df_b = generate_datasets()
        # Convert to JSON using pandas, which safely handles NaN -> null
        platform_data = json.loads(df_p.to_json(orient="records"))
        bank_data = json.loads(df_b.to_json(orient="records"))
        
        return {
            "platform_data": platform_data,
            "bank_data": bank_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reconcile")
async def api_reconcile(platform_file: UploadFile = File(...), bank_file: UploadFile = File(...)):
    if not platform_file.filename.endswith('.csv') or not bank_file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    try:
        # Read CSV files into pandas DataFrames
        platform_contents = await platform_file.read()
        bank_contents = await bank_file.read()
        
        df_platform = pd.read_csv(io.BytesIO(platform_contents))
        df_bank = pd.read_csv(io.BytesIO(bank_contents))
        
        # Run reconciliation model
        results = reconcile(df_platform, df_bank, target_month="2023-11")
        
        # We need to handle potential NaN values which are not JSON serializable
        # A simple hack is to dump to json with default handler and load back
        import math
        def replace_nan(obj):
            if isinstance(obj, dict):
                return {k: replace_nan(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_nan(v) for v in obj]
            elif isinstance(obj, float) and math.isnan(obj):
                return None
            return obj
            
        clean_results = replace_nan(results)
        return clean_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
