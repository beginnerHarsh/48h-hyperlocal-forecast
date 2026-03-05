# Amazon Lightsail Deployment Guide
## 48-Hour Hyperlocal Forecasting Microservice

This guide covers the exact steps to take the `docker_48h_forecast` folder from your local machine and deploy it as a fully autonomous, 24/7 background service on an Amazon Lightsail Virtual Private Server (VPS). 

Because we built the architecture specifically for Docker, this process is incredibly streamlined.

---

## Phase 1: Provisioning the Server

1. **Log in to AWS Lightsail:** Navigate to [lightsail.aws.amazon.com](https://lightsail.aws.amazon.com/).
2. **Create Instance:**
   - Click **Create instance**.
   - **Instance location:** Select the region closest to your users (e.g., `ap-south-1` Mumbai).
   - **Pick your instance image:** Select **Linux/Unix** -> **OS Only** -> **Ubuntu 22.04 LTS** (or 24.04).
   - **Choose your instance plan:** The **$5/mo or $10/mo** plan (1GB - 2GB RAM) is more than enough for this lightweight AI script.
   - **Identify your instance:** Name it something like `hyperlocal-forecast-engine`.
   - Click **Create instance**.
3. **Open Firewall Ports:**
   - Once the instance is "Running", click on its name to open its management page.
   - Go to the **Networking** tab.
   - Under **IPv4 Firewall**, click **Add rule**. Provide the following:
     - Custom Rule -> TCP -> Port **`8501`** (This exposes the Streamlit Dashboard).
     - Custom Rule -> TCP -> Port **`8000`** (This exposes the FastAPI raw JSON data).
   - Save the rules.

---

## Phase 2: Cloning the Repository

We will use Git to securely download the code onto the Linux server.

1. **SSH into the Server:**
   - On the Lightsail Instance Connect tab, click "Connect using SSH" to open a browser terminal.
2. **Clone the Project:**
   - Run the following command in the Ubuntu terminal, replacing `<YOUR_GITHUB_REPO_URL>` with your actual repository link:
     ```bash
     git clone <YOUR_GITHUB_REPO_URL>
     ```
   - *Note: If your repo is private, GitHub will prompt you for your Username and a Personal Access Token (PAT) as the password.*

---

## Phase 3: Building and Running the Container

Once the folder is on the Ubuntu server, SSH into it (either via the browser "Connect" button or your local terminal).

**1. Update Ubuntu and Install Docker:**
Copy and paste this into the remote console:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu
```
*(You may need to log out and log back in for the `usermod` user privileges to apply).*

**2. Enable Swap Space (Crucial for $5 / 512MB RAM Plan):**
Heavy data-science libraries like `pandas` and `scikit-learn` require more than 512MB of RAM to install. We must allocate a 1GB "Virtual RAM" swap file to prevent the server from crashing during the build:
```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
sudo sh -c 'echo "/swapfile none swap sw 0 0" >> /etc/fstab'
```

**3. Navigate into the Project Folder:**
```bash
cd ~/48h-hyperlocal-forecast
```

**4. Build the Docker Image:**
This tells Docker to download Python, install `pandas/scikit-learn/fastapi`, and securely package the entire microservice.
```bash
sudo docker build -t 48h-forecast-engine .
```

**5. Run the Container in the Background:**
This single command Boots the background `ingest_live.py` daemon, the `api.py` endpoint, and the `app.py` stream-lit dashboard entirely headless.
```bash
docker run -d --name forecast-active -p 8501:8501 -p 8000:8000 --restart unless-stopped 48h-forecast-engine
```

**What those flags mean:**
* `-d`: Run perfectly in the background (detached), so it stays alive 24/7 even if you close the terminal.
* `-p 8501:8501`: Maps the Streamlit port from the container to the actual Internet.
* `-p 8000:8000`: Maps the FastAPI port to the Internet.
* `--restart unless-stopped`: If the AWS server reboots for maintenance, your python scripts will automatically awake and resume mathematical forecasting the millisecond the server boots back up!

---

## Phase 4: Accessing the Live Service

That's it! Your microservice is now live on the internet.

*   **View the Visual Dashboard:** Open your browser and navigate to:
    `http://<YOUR_LIGHTSAIL_PUBLIC_IP>:8501`
*   **Access the API JSON Payload:**
    `http://<YOUR_LIGHTSAIL_PUBLIC_IP>:8000/api/v1/forecast`

---

## Phase 5 (Optional): Securing the API Gateway (HTTPS)
As the User requested earlier, if you wish to serve the raw API Data securely:
1. Go to AWS **API Gateway**.
2. Create an **HTTP API**.
3. Create an integration pointing exactly to `http://<YOUR_LIGHTSAIL_PUBLIC_IP>:8000`.
4. AWS will issue you a secure `https://...` URL that safely proxies your Lightsail data and acts as the secure middleman for mobile apps or external integrations.
