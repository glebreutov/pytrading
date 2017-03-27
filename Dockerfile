FROM ubuntu:16.10
RUN apt-get update && apt-get install -y python3.6 python3-pip

ADD config_prod.json home/pytading/
RUN mkdir home/pytading/logs/
ADD . home/pytading/mm/
RUN python3.6 -m pip install --upgrade pip
RUN python3.6 -m pip install -r home/pytading/mm/requirements.txt
EXPOSE 5678
WORKDIR /home/pytading
ENTRYPOINT python3.6 -m mm.run
#CMD["python3", "/home/pytading/bootstrap.py"]