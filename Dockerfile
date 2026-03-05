FROM python:3.11-slim

WORKDIR /app



# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make entrypoint executable
RUN chmod +x run.sh

# Expose Streamlit port
EXPOSE 8501

CMD ["./run.sh"]
