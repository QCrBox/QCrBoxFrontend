FROM python:3.11

ENV LANG=C.UTF-8

# prevents python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE 1

# prevents python from buffering stdout and stderr
ENV PYTHONUNBUFFERED 1

RUN apt update -y
RUN apt install libgl1-mesa-glx -y python3-dev gcc libc-dev

WORKDIR /app

RUN pip install --upgrade pip
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY ./qcrbox_frontend /app/qcrbox_frontend
COPY ./docker /app/docker

ENV PYTHONPATH "${PYTHONPATH}:/app/qcrbox_frontend"

RUN chmod +x /app/docker/server-entrypoint.sh
