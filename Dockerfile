FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY ./app /app
WORKDIR /app

RUN pip install -r requirements.txt

CMD ["python3", "main.py"]
