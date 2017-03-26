FROM ubuntu:16.10
RUN apt-get update && apt-get install -y python3.6 python3-pip
RUN python3.6 -c 'print(12345)'
ADD . home/pytading
RUN python3.6 -m pip install --upgrade pip
RUN python3.6 -m pip install -r home/pytading/requirements.txt
EXPOSE 5678
WORKDIR /home/pytading
RUN python3.6 /home/pytading/run.py
#CMD["python3", "/home/pytading/bootstrap.py"]