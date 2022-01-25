FROM cloudfoundry/cflinuxfs3:latest
WORKDIR /home/vcap/app
COPY --chown=vcap:vcap . ./
USER vcap:vcap
ENV HOME=$WORKDIR
CMD ["/bin/bash", "-c", "./.profile && ./start.sh"]
