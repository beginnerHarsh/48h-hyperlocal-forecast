# 48-Hour Hyperlocal Forecasting Microservice
## Documentation & Architecture Overview

This directory (`docker_48h_forecast`) contains a 100% self-contained, Docker-ready microservice. It is designed to run completely autonomously and headless on a server like Amazon Lightsail.

Its singular purpose is to combine **Live Telemetry from a Local AWS Sensor** with **Ground-Truth Calibration from the India Meteorological Department (IMD)** to train a continuous 48-hour Machine Learning forecast using **K-Nearest Neighbors (KNN)**.

*This pipeline purposely excludes broad global APIs like Open-Meteo, relying entirely on the unique thermal signature of your exact physical location.*

---

## 1. System Components

The microservice consists of 5 modular Python scripts, all orchestrated by a central `config.py` file to make updating coordinates and API keys trivial.

### A. The Engine Room: `ingest_live.py`
This is the heart of the background daemon. When the Docker container boots via `run.sh`, this script starts a continuous, unbreakable `while True` loop.
1. Every 5 minutes, it pings the custom AWS endpoint (`gtk47vexob.execute-api.us-east-1.amazonaws.com`) for Device ID `7`.
2. It mathematically aligns the JSON payload and extracts only entirely *new* timestamp rows.
3. It appends these new rows to a local `weather_data_live.csv` file.
4. If new data was found, it **automatically triggers the AI engine** to compute a new 48-hour forecast and archive it, operating entirely headless. 

### B. The AI Brain: `knn_engine.py` & `fetch_imd.py`
Triggered by the Ingester, the KNN script handles all heavy mathematical logic. It trains a fresh Machine Learning pattern array every 5 minutes based on the latest data.
1. **Bias Calibration:** First, it calls `fetch_imd.py` to scrape the absolute latest ground-truth temperature from the official IMD API for Chandigarh. 
   *(Note: The `config.py` allows targeting explicit physical towers. The generic `A0B2D4E6` Chandigarh tower is 11.69km away, whereas the `CGDAC000` DAV School tower is physically closer at 7.24km).*
2. It searches your local `weather_data_live.csv` to find what your sensor read at the *exact same minute* IMD recorded their value. 
3. It calculates the live error "gap" (e.g., your sensor says 30°C, IMD says 31.3°C = -1.30°Bias), and applies an Exponentially Weighted Moving Average (`ALPHA = 0.2`) smoothing off the past 15 days of error history.
4. **Featurization:** It takes the timestamp of all your historical sensor data and turns them into *Sine and Cosine waves* representing the "Hour of Day" and "Day of Year". This translates human time into perfect cyclical geometry that the AI can understand.
5. **Inference:** It trains a `KNeighborsRegressor` (K=5, using Distance Weighting). This means it searches your sensor's history to find the 5 hours that chemically and chronologically "look the most" like the upcoming 48 hours, and predicts the temperature based on what happened back then.
6. **Gap-Decay Smoothing:** It takes the raw output of the AI, applies the calculated IMD Bias error, and finally generates a 4-hour mathematical decay bridge so the starting curve visually connects perfectly out of your live sensor reading without any jagged jumps.
7. It saves the final 48 row output to `forecast_48h.csv`.

### C. The Historian: `save_forecast.py`
Because the system overwrites the `forecast_48h.csv` file automatically every 5 minutes to feed the dashboard, older predictions would be lost forever. 
Whenever the KNN engine finishes a new prediction block, it seamlessly triggers this archiver script.
The script generates a precise timestamp filename (e.g., `forecast_48h_snapshot_2026-02-28_17-32-28.csv`) and creates a permanent cold-storage backup inside the `forecast_archives/` folder.

### D. The Visuals: `app.py`
This is the Streamlit dashboard (`localhost:8501`). It is the only component the human user interacts with.
1. When loaded, it simply reads the `forecast_48h.csv` and `weather_data_live.csv` files that the background daemon maintains.
2. It renders the modern UI, KPI metrics, Bias offset score, and the Plotly interactive temperature curve. 
3. Because the background daemon is 100% autonomous, the dashboard can safely be closed, crashed, or rebooted without affecting the data ingest or prediction systems. Clicking the "Force Refresh" button directly forces the daemon to immediately wake up out of its 5-minute sleep cycle and fetch new data synchronously.

### E. The Endpoints: `api.py`
To route the generated AI data externally (such as to a mobile app or a remote webpage), a very lightweight `FastAPI` instance serves the processed forecast natively over HTTP.
1. It listens on Port **`8000`**.
2. Exposes a clean `GET /api/v1/forecast` endpoint that parses the raw `forecast_48h.csv` into a standard, compressed, programmatic JSON array.
3. Exposes a `GET /api/v1/health` for basic load balancer heartbeats.
*Note: Because Lightsail internal traffic is HTTP, this port should be hooked into Amazon API Gateway or an NGINX reverse-proxy if you wish to expose it to the public web via HTTPS.*

---

## 2. Docker & Lightsail Deployment

The folder includes a `requirements.txt` listing the precise packages needed, a simple `Dockerfile`, and a bash `run.sh` script.

When deployed to Amazon Lightsail, Docker will execute `run.sh`:
```bash
python ingest_live.py &
python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```
This boots the headless daemon natively into the background (`&`), and simultaneously hosts the visual dashboard onto port `8501`, fully replicating the local architecture in the cloud seamlessly.

---

## 3. Validation & Proof of Accuracy Strategy (Lightsail)
To mathematically prove the accuracy of your AI model to stakeholders, you must capture both "What the AI predicted" and "What actually happened" to calculate the delta (Mean Absolute Error). 

Because your Lightsail server will run this pipeline autonomously 24/7, you simply need to ensure the following files are preserved and occasionally downloaded for analysis:

### A. The "Prediction" Evidence
* **`forecast_archives/` (Folder):** This is your holy grail. Every 5 minutes, `save_forecast.py` drops a permanent, timestamped snapshot here. 
  * *Proof Use Case:* If you want to prove your model knew it would be 32°C on Thursday at noon, you can open the archive file from *Tuesday at noon* (48 hours prior) and show the exact row where the KNN algorithm predicted that 32°C spike two days in advance.

### B. The "What Actually Happened" Evidence
* **`weather_data_live.csv` (File):** This grows infinitely, storing every 5-minute telemetry tick from your physical AWS roof sensor.
  * *Proof Use Case:* This is your undeniable Ground Truth. You overlay the telemetry from this file on top of the Prediction curve from the archives.

### C. The "Bias Calibration" Evidence
* **`bias_history.json` (File):** This tracks every single 15-minute sync between your roof sensor and the IMD CGDAC000 tower.
  * *Proof Use Case:* If someone asks "Why did the AI adjust the temperature down by 1.2°C?", this log mathematically proves the exact Exponentially Weighted error drift based on official government data at that exact minute.

### Validation Workflow (Monthly)
1. SSH into Amazon Lightsail at the end of the month.
2. Download `weather_data_live.csv` and a random sampling of files from `forecast_archives/`.
3. In Python/Excel, match the `DateTime` of the 48-hour prediction against the `TimeStamp` of what the actual sensor read 48 hours later.
4. Calculate the **MAE (Mean Absolute Error)**. If the average error margin across the month is under `1.5°C`, you have empirical proof of a highly successful, hyper-local meteorological AI pipeline.
