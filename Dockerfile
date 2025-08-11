FROM python:3.10-bookworm

ENV JAVA_HOME=/opt/java/openjdk
COPY --from=eclipse-temurin:21 $JAVA_HOME $JAVA_HOME
ENV PATH="${JAVA_HOME}/bin:${PATH}"

COPY binaries/ ./binaries/

# Set the working directory inside the container
WORKDIR /app

# Copy your Python script into the container
COPY . .

# If you have dependencies, copy requirements.txt and install them
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "run_all.py"]
CMD ["--help"]