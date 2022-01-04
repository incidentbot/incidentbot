FROM python:3.9

# Copy only the relevant Python files into the container.
COPY ./lib /app/lib
COPY requirements.txt /app
COPY main.py /app
COPY ./templates /app/templates

# Set the work directory to the app folder.
WORKDIR /app

# Install Python dependencies.
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 3000

ENTRYPOINT ["python3", "main.py"]