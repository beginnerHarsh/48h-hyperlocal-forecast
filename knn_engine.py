import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler

import config
from fetch_imd import get_latest_imd

# ==============================================================================
# 1. BIAS CORRECTION LOGIC
# ==============================================================================
def load_bias_history():
    if os.path.exists(config.BIAS_HISTORY_FILE):
        try:
            with open(config.BIAS_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return []

def save_bias_history(history):
    with open(config.BIAS_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def calculate_current_bias():
    """
    Looks at the most recent local sensor reading, exactly matches its timestamp
    with the delayed IMD reading, and pushes the error delta into history.
    """
    imd_data = get_latest_imd()
    if not imd_data or imd_data['temperature'] is None or imd_data['timestamp_obj'] is None:
        print("[Bias] IMD data unavailable. Skipping bias update.")
        return get_exponential_bias()
        
    imd_time = imd_data['timestamp_obj']
    imd_temp = imd_data['temperature']
    
    # Load Sensor history
    if not os.path.exists(config.LOCAL_CSV):
        return get_exponential_bias()
        
    df = pd.read_csv(config.LOCAL_CSV, parse_dates=['TimeStamp'])
    if df.empty:
        return get_exponential_bias()
        
    # Find the local sensor row whose time is mathematically closest to the IMD time
    df['time_diff'] = (df['TimeStamp'] - imd_time).abs()
    closest_row = df.loc[df['time_diff'].idxmin()]
    local_temp = float(closest_row['CurrentTemperature'])
    
    # Calculate Bias (Error = Forecasted/Local - Actual Ground Truth)
    error = local_temp - imd_temp
    
    # Load and update history
    history = load_bias_history()
    
    # Check if we already recorded a bias for this specific IMD timestamp
    date_str = imd_time.strftime("%Y-%m-%d %H:%M")
    if not any(entry['date'] == date_str for entry in history):
        history.append({
            'date': date_str,
            'error': round(error, 2),
            'local_temp': local_temp,
            'imd_temp': imd_temp
        })
        
        # Enforce rolling window
        if len(history) > config.HISTORY_WINDOW:
            history = history[-config.HISTORY_WINDOW:]
            
        save_bias_history(history)
        print(f"[Bias] Synced with IMD at {date_str}. Added Error offset: {error:.2f}°C")
        
    return get_exponential_bias()

def get_exponential_bias():
    """Calculate Exponentially Weighted Moving Average of recent errors."""
    history = load_bias_history()
    if not history:
        return 0.0
        
    errors = [entry['error'] for entry in history]
    
    # EMA Calculation
    ema = errors[0]
    for current_err in errors[1:]:
        ema = config.ALPHA * current_err + (1 - config.ALPHA) * ema
        
    return round(ema, 2)


# ==============================================================================
# 2. KNN FORECAST ENGINE (48 HOURS)
# ==============================================================================
def generate_48h_forecast():
    """Trains a KNN model on live data and projects exactly 48 hours."""
    
    print("=" * 50)
    print("Starting 48-Hour KNN Inference")
    print("=" * 50)
    
    # Step 1: Calculate new bias immediately before predicting
    bias_offset = calculate_current_bias()
    print(f"[Engine] Applying calculated IMD Bias Offset: {bias_offset:+.2f}°C")
    
    if not os.path.exists(config.LOCAL_CSV):
        print("[Error] No sensor history found. Run ingest_live.py first.")
        return None
        
    df_raw = pd.read_csv(config.LOCAL_CSV, parse_dates=['TimeStamp'])
    if df_raw.empty:
        return None
        
    # Step 2: Featurize Time 
    # Aggregate to hourly average
    df_raw.set_index('TimeStamp', inplace=True)
    df_hourly = df_raw.resample('1H').mean(numeric_only=True).dropna(subset=['CurrentTemperature'])
    
    df_feat = pd.DataFrame(index=df_hourly.index)
    df_feat['temp'] = df_hourly['CurrentTemperature']
    
    df_feat['hour'] = df_feat.index.hour
    df_feat['doy']  = df_feat.index.dayofyear
    
    df_feat['hour_sin'] = np.sin(2 * np.pi * df_feat['hour'] / 24)
    df_feat['hour_cos'] = np.cos(2 * np.pi * df_feat['hour'] / 24)
    df_feat['doy_sin']  = np.sin(2 * np.pi * df_feat['doy'] / 365)
    df_feat['doy_cos']  = np.cos(2 * np.pi * df_feat['doy'] / 365)

    # Step 3: Train KNN (n_neighbors=5, distance-weighted)
    features = ['hour_sin', 'hour_cos', 'doy_sin', 'doy_cos']
    X = df_feat[features].values
    y = df_feat['temp'].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    knn = KNeighborsRegressor(n_neighbors=5, weights='distance')
    knn.fit(X_scaled, y)
    
    # Step 4: Build future 48-hour timeline
    now = datetime.now()
    start_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    future_times = [start_hour + timedelta(hours=i) for i in range(48)]
    
    df_future = pd.DataFrame({'DateTime': future_times})
    df_future['hour'] = df_future['DateTime'].dt.hour
    df_future['doy']  = df_future['DateTime'].dt.dayofyear
    
    df_future['hour_sin'] = np.sin(2 * np.pi * df_future['hour'] / 24)
    df_future['hour_cos'] = np.cos(2 * np.pi * df_future['hour'] / 24)
    df_future['doy_sin']  = np.sin(2 * np.pi * df_future['doy'] / 365)
    df_future['doy_cos']  = np.cos(2 * np.pi * df_future['doy'] / 365)
    
    X_predict = scaler.transform(df_future[features].values)
    
    # Base KNN Predictions
    df_future['Temp_KNN'] = knn.predict(X_predict)
    
    # Step 5: Apply the IMD Ground-Truth Bias Correction first
    # Since we subtracted 'Actual' locally to find error, we must subtract Error from future predictions
    df_future['Corrected_Temp'] = df_future['Temp_KNN'] - bias_offset
    
    # Step 6: Continuity Smoothing to Live Value
    # Preserve the mathematical shape of the KNN model by offsetting it by the gap
    # and gradually decaying that gap back to 0 over 4 hours.
    last_live_val = df_raw.iloc[-1]['CurrentTemperature']
    first_hour_un_smoothed = df_future.iloc[0]['Corrected_Temp']
    gap = last_live_val - first_hour_un_smoothed
    
    for i in range(min(4, len(df_future))):
        weight = (3 - i) / 4.0  # i=0 (+1hr): 75% gap, i=1 (+2hr): 50%, i=2 (+3hr): 25%, i=3 (+4hr): 0%
        df_future.loc[i, 'Corrected_Temp'] = df_future.loc[i, 'Corrected_Temp'] + (gap * weight)
        
    df_future['Corrected_Temp'] = df_future['Corrected_Temp'].round(2)
    
    print(f"[Success] Generated 48 hours. Saving to disk...")
    df_future.to_csv(os.path.join(config.BASE_DIR, "forecast_48h.csv"), index=False)
    
    return df_future

if __name__ == '__main__':
    generate_48h_forecast()
