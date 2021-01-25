FROM centos:7

VOLUME /payload

RUN yum update -y && \
    yum install python-virtualenv python-setuptools make git -y

# NOTE(ivasilev) Unless we upgrade pip an obsolete v 9 will be on the system
# and we need at least 10.0.1 to install a not-yet-merged framework pr in case
# it's necessary
RUN easy_install pip

WORKDIR /payload
ENTRYPOINT make install-deps && make test
