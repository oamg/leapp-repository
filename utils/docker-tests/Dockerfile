FROM registry.centos.org/centos:7

VOLUME /payload

RUN yum update -y && \
    yum install python-virtualenv python-setuptools make git -y

# NOTE(ivasilev,pstodulk) We need at least pip v10.0.1, however centos:7
# provides just v8.1.2 (via EPEL). So do this: install epel repos -> install
# python2-pip -> use pip to update to specific pip version we require. period
# NOTE(pstodulk) I see we take care about pip for py3 inside the Makefile,
# however I am afraid of additional possible troubles in future because of the
# archaic pip3 version (v9.0.1). As we want to run tests for Py2 and Py3 in ci
# always anyway, let's put py3 installation here as well..

RUN yum -y install epel-release && \
    yum -y install python2-pip python3-pip && \
    python2 -m pip install --upgrade pip==20.3.4 && \
    python3 -m pip install --upgrade pip==20.3.4

WORKDIR /payload
ENTRYPOINT make install-deps && make test
