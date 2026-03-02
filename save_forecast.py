import os
import shutil
from datetime import datetime
import pandas as pd
import config

def save_forecasting_data():
    """
    Creates a permanent, timestamped snapshot of the current 48-hour forecast CSV.
    Useful for looking back at what the model predicted at a specific time.
    """
    source_file = os.path.join(config.BASE_DIR, "forecast_48h.csv")
    archive_dir = os.path.join(config.BASE_DIR, "forecast_archives")
    
    if not os.path.exists(source_file):
        print(f"[Error] The file {source_file} does not exist yet. Please run the forecast engine first.")
        return

    # Create the archive directory if it doesn't exist
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)

    # Generate a unique timestamped filename
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archive_filename = f"forecast_48h_snapshot_{now_str}.csv"
    archive_filepath = os.path.join(archive_dir, archive_filename)
    
    # Read, append the generated timestamp so it's baked into the data, and save
    df = pd.read_csv(source_file)
    df['Snapshot_Taken_At'] = datetime.now()
    
    df.to_csv(archive_filepath, index=False)
    print(f"✅ Successfully saved a permanent snapshot of the forecast data to:")
    print(f"   -> {archive_filepath}")

if __name__ == "__main__":
    print("=" * 50)
    print("Forecast Archival Tool")
    print("=" * 50)
    save_forecasting_data()
