FROM ubuntu:16.04 as suite3270builder
LABEL maintainer "Adam Horsewood <ahorsewood@gdssecurity.com>"

#####
#
# docker run  -it birptest -v  /tmp/.X11-unix:/tmp/.X11-unix /bin/bash
#
#####

RUN mkdir /app
WORKDIR /app

RUN apt-get update && apt-get install -y tree wget build-essential automake libxt-dev libxmu-headers xfonts-utils  xfonts-x3270-misc libxaw7-dev s3270 libncurses-dev tclsh tcl8.6-dev\
 && wget https://sourceforge.net/projects/x3270/files/x3270/3.6ga5/suite3270-3.6ga5-src.tgz/download \
 && tar xzf download

WORKDIR /app/suite3270-3.6

COPY suite3270-full.patch .

RUN patch -p1 < suite3270-full.patch

RUN ./configure --enable-static && make && make install

#FROM python:2.7-alpine as birp

from ubuntu:16.04 as birp

#not need in final image?
RUN apt-get update && apt-get install -y tree python python-pip libxaw7 && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

COPY ["submodules","birp.py","getch.py","py3270wrapper.py","requirements.txt","tn3270.py", "/app/"]

RUN sed -i "s_./x3270_/app/bins/x3270_g" py3270wrapper.py \
 && sed -i "s_'s3270'_'/app/bins/s3270'_g" py3270wrapper.py \
 && cd py3270 \
 && python setup.py install \
 && pip install -r /app/requirements.txt

COPY --from=suite3270builder /usr/local/bin/ /app/bins/

ENV DISPLAY :0.0

ENTRYPOINT ["python", "/app/birp.py"]
