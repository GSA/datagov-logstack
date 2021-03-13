FROM python:3.8-alpine

RUN pip install --upgrade pipenv
RUN mkdir /app

WORKDIR /app
COPY Pipfile Pipfile.lock  /app/

RUN pipenv install --dev

ENTRYPOINT ["pipenv", "run"]
CMD ["python", "-m", "unittest"]
