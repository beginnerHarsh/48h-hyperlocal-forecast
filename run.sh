#!/bin/bash
echo "Starting 48-Hour Forecast Lightsail Container..."

# Start the continuous ingestion loop in the background
python ingest_live.py &

# Start the fast API to serve JSON
uvicorn api:app --host 0.0.0.0 --port 8000 &

# Start the Streamlit Dashboard
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
