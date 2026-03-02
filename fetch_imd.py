import requests
import pandas as pd
import config

def get_latest_imd():
    """Fetch the latest official temperature and humidity from the 15-minute IMD AWS Network."""
    try:
        resp = requests.get(config.IMD_API, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        # The new API returns a massive flat list of dicts for ~3000 stations.
        for record in data:
            if record.get('ID') == config.IMD_HARDWARE_ID:
                # The AWS API provides high-precision strings like "2026-03-02" and "03:45:00"
                dt_str = f"{record.get('DATE', '')} {record.get('TIME', '')}".strip()
                t_val = record.get('CURR_TEMP')
                h_val = record.get('RH')
                
                # Convert to exact datetime object for precise comparison
                import pytz
                try:
                    # The IMD AWS API publishes strictly in UTC time.
                    utc_zone = pytz.utc
                    ist_zone = pytz.timezone('Asia/Kolkata')
                    
                    dt_obj_utc = pd.to_datetime(dt_str)
                    dt_obj_utc = utc_zone.localize(dt_obj_utc)
                    dt_obj = dt_obj_utc.astimezone(ist_zone).replace(tzinfo=None) # Strip timezone info to match local CSV naive format
                    
                    # Update the string to reflect IST for the dashboard
                    dt_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    dt_obj = None
                    
                return {
                    'timestamp_str': dt_str,
                    'timestamp_obj': dt_obj,
                    'temperature': float(t_val) if t_val and str(t_val).lower() != 'none' else None,
                    'humidity': float(h_val) if h_val and str(h_val).lower() != 'none' else None,
                }
    except Exception as e:
        print(f"[Error] Failed to fetch IMD AWS data: {e}")
    return None

if __name__ == '__main__':
    print(get_latest_imd())
