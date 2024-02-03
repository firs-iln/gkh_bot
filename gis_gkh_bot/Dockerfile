FROM python:3.11

ENV PYTHONUNBUFFERED=1

WORKDIR /gis_gkh_bot

RUN pip install --upgrade pip

COPY requirements.txt /gis_gkh_bot/

RUN pip install -r requirements.txt
#
#RUN pip install poetry
#
#COPY poetry.lock pyproject.toml ./
#
#RUN poetry config virtualenvs.create false \
#    && poetry install --no-interaction --no-ansi

#RUN playwright install
##
#RUN playwright install-deps

COPY .. .

RUN chmod +x main.py
