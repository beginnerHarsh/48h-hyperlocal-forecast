import os
import pandas as pd
from datetime import datetime
import config
from knn_engine import generate_48h_forecast, calculate_current_bias

print("\n--- Validating Standalone 48-Hour Pipeline ---\n")

# 1. Validate Data Ingestion
print("1. Validating Data Ingestion...")
if not os.path.exists(config.LOCAL_CSV):
    print("❌ ERROR: local CSV data file is missing!")
else:
    try:
        df = pd.read_csv(config.LOCAL_CSV)
        print(f"✅ Found CSV with {len(df)} records.")
        print(f"   Latest record: {df.iloc[-1]['TimeStamp']} - Temp: {df.iloc[-1]['CurrentTemperature']}°C")
    except Exception as e:
        print(f"❌ ERROR reading CSV: {e}")

# 2. Validate Bias Calculation
print("\n2. Validating IMD Bias Calculation...")
# Redirecting stdout temporarily to capture the print statement from calculate_current_bias
import sys
from io import StringIO
captured_output = StringIO()
sys.stdout = captured_output
try:
    bias = calculate_current_bias()
    sys.stdout = sys.__stdout__
    print(captured_output.getvalue().strip() or "   No new bias update (using historical info).")
    print(f"✅ Calculated Bias: {bias:+.2f}°C")
except Exception as e:
    sys.stdout = sys.__stdout__
    print(f"❌ ERROR calculating bias: {e}")

# 3. Validate Forecasting Engine
print("\n3. Validating 48-Hour KNN Inference...")
try:
    df_forecast = generate_48h_forecast()
    if df_forecast is not None and not df_forecast.empty:
        print(f"✅ Successfully generated {len(df_forecast)} hours of forecast.")
        print("   First 3 hours:")
        for _, row in df_forecast.head(3).iterrows():
            print(f"      {row['DateTime'].strftime('%Y-%m-%d %H:%M')}: {row['Corrected_Temp']}°C")
    else:
        print("❌ ERROR: Forecast engine returned None or empty DataFrame.")
except Exception as e:
    sys.stdout = sys.__stdout__
    print(f"❌ ERROR running forecast engine: {e}")

print("\n--- Validation Complete ---")
