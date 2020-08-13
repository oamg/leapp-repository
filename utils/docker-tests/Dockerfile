FROM centos:7

VOLUME /payload

RUN yum update -y && \
    yum install python-virtualenv make git -y

WORKDIR /payload
ENTRYPOINT ["/bin/bash"]
