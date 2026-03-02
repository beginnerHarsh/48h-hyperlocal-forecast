import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data storage
LOCAL_CSV = os.path.join(BASE_DIR, "weather_data_live.csv")

# AWS Sensor Config (Local Station)
AWS_SENSOR_API = "https://gtk47vexob.execute-api.us-east-1.amazonaws.com/ssmet1225data"
DEVICE_ID = "7"
LOCAL_LAT = 30.7403
LOCAL_LON = 76.7305

# IMD Config (Ground Truth via High-Frequency 15-Minute AWS Network)
IMD_API = "https://3xlnx8gixj.execute-api.us-east-1.amazonaws.com/city/api/aws_data_api.php"
IMD_STATION_NAME = "Chandigarh-DAV"
IMD_HARDWARE_ID = "CGDAC000" # Physically closest tower to AWS sensor (7.24km)
IMD_LAT = 30.7403
IMD_LON = 76.7305

# Bias Correction settings
ALPHA = 0.2
HISTORY_WINDOW = 15
BIAS_HISTORY_FILE = os.path.join(BASE_DIR, "bias_history.json")
