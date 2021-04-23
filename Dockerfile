FROM ubuntu:20.04

LABEL maintainer="Artem Klopov"

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y python3

COPY ./application /application
ENTRYPOINT /application/novapulsar_task_env/bin/python3 /application/app.py

