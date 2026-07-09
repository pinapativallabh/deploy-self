FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# In python, running -m app.main starts the module correctly.
CMD ["python", "-m", "app.main"]
