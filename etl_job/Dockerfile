FROM python:3.10-slim

WORKDIR /etl

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "etl_load.py"] 