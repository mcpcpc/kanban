FROM python:3.11

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir .[prod]

ENV UVICORN_HOST 0.0.0.0                                     
ENV UVICORN_PORT 8080

EXPOSE 8080

CMD [ -f /app/instance/kanban.sqlite ] || quart --app kanban init-db ; uvicorn --factory kanban:create_app
