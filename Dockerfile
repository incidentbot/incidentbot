FROM python:3.9 as base

# Copy only the relevant Python files into the container.
COPY ./bot /app/bot
COPY requirements.txt /app
COPY config.py /app
COPY main.py /app
COPY ./templates /app/templates
COPY ./static /app/static

# Set the work directory to the app folder.
WORKDIR /app

# Install Python dependencies.
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 3000

CMD ["python3", "main.py"]

FROM base as production
