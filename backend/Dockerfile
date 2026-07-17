FROM python:3.10-slim

WORKDIR /app

# System deps for OpenCV + audio
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender-dev \
    libgomp1 ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download models at build time (faster startup)
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
RUN python -c "import whisper; whisper.load_model('small')"

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]

