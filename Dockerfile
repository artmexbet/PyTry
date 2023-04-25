FROM ubuntu

RUN apt-get update
RUN apt-get install -y python3-pip python3

WORKDIR /app
COPY requirements.txt requirements.txt
#CMD ["python3.11", "-m venv", "venv"]
RUN #python3 -m venv venv

#CMD ["sudo", "venv/bin/pip"]
RUN pip install --no-cache-dir --upgrade pip
RUN pip install -r requirements.txt

COPY main.py main.py
COPY data data
COPY task_checking.py task_checking.py
COPY config.py config.py
COPY .env .env

# CMD ["pip", "install", "-r requirements.txt"]

ENV DB_PASSWORD=postgrespw
ENV DB_USERNAME=postgres
ENV DB_ADDRESS=db:5432

EXPOSE 5000

CMD ["python3", "main.py"]
