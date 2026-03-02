import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta
import config
from knn_engine import generate_48h_forecast
from save_forecast import save_forecasting_data

def fetch_api_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch data from the live AWS API for a date range."""
    params = {
        'deviceid': config.DEVICE_ID,
        'startdate': start_date,
        'enddate': end_date,
    }
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching sensor DB: {start_date} to {end_date}...")
    try:
        resp = requests.get(config.AWS_SENSOR_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get('items', [])
        
        if not items:
            return pd.DataFrame()
            
        df = pd.DataFrame(items)
        df['TimeStamp'] = pd.to_datetime(df['TimeStamp'])
        return df
    except Exception as e:
        print(f"[API Error] Fetch failed: {e}")
        return pd.DataFrame()

def run_single_ingest():
    """Performs one single API fetch and CSV update cycle."""
    today = datetime.now()
    if os.path.exists(config.LOCAL_CSV):
        df_live = pd.read_csv(config.LOCAL_CSV)
        df_live['TimeStamp'] = pd.to_datetime(df_live['TimeStamp'])
        last_ts = df_live['TimeStamp'].max()
        start_date = (today - timedelta(days=1)).strftime("%d-%m-%Y")
    else:
        print("No CSV found. Bootstrapping the last 15 days of live data...")
        df_live = pd.DataFrame()
        last_ts = today - timedelta(days=15)  # bootstrap last 15 days
        start_date = last_ts.strftime("%d-%m-%Y")

    end_date = today.strftime("%d-%m-%Y")
    
    df_api = fetch_api_data(
        start_date=start_date,
        end_date=end_date,
    )

    if not df_api.empty:
        # Align columns if combining
        if not df_live.empty:
            keep_cols = [c for c in df_live.columns if c in df_api.columns]
            if 'TimeStamp' not in keep_cols:
                keep_cols = ['TimeStamp'] + keep_cols
            df_api = df_api[keep_cols]

        # Extract ONLY new rows
        if not df_live.empty:
            df_new = df_api[df_api['TimeStamp'] > last_ts]
        else:
            df_new = df_api

        if not df_new.empty:
            print(f"-> Appending {len(df_new)} new records.")
            df_final = pd.concat([df_live, df_new], ignore_index=True)
            df_final.sort_values('TimeStamp', inplace=True)
            df_final.drop_duplicates(subset='TimeStamp', keep='last', inplace=True)
            df_final.reset_index(drop=True, inplace=True)
            
            df_final.to_csv(config.LOCAL_CSV, index=False)
            return True # Indicates new data was fetched
        else:
            print("-> Up to date. No new records.")
            return False
    return False

def ingest_loop():
    """Continuous loop to keep the local CSV perfectly synced."""
    print("=" * 50)
    print("Starting Continuous Local Sensor Ingestion Service")
    print("=" * 50)
    
    while True:
        try:
            # 1. Fetch live data
            new_data_found = run_single_ingest()
            
            # 2. If we got new data, auto-run the AI engine and archive it!
            if new_data_found:
                print("-> Triggering background AI forecast update...")
                generate_48h_forecast()
                save_forecasting_data()
                
        except Exception as e:
            print(f"[Fatal] Loop crashed but restarting: {e}")
        # Sleep exactly 5 minutes before checking AWS again
        time.sleep(300)

if __name__ == '__main__':
    ingest_loop()
