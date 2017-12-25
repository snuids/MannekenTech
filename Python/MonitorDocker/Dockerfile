FROM python:3.6
MAINTAINER snuids

RUN pip install docker
RUN pip install elasticsearch

COPY ./*.py /opt/monitordocker/

WORKDIR /opt/monitordocker

CMD ["python", "monitordocker.py"]
