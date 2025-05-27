FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add debugging
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE ${PORT}

# Use a shell script to start the application
RUN echo "#!/bin/bash" > start.sh
# RUN uvicorn main:app --host 0.0.0.0 --port \$PORT --log-level debug > start.sh
RUN chmod +x start.sh
CMD ["/bin/bash", "start.sh"]
