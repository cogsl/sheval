FROM python:3.10-slim-trixie

ENV JAVA_HOME=/opt/java/openjdk
COPY --from=eclipse-temurin:21 $JAVA_HOME $JAVA_HOME
ENV PATH="${JAVA_HOME}/bin:${PATH}"

COPY binaries/ ./binaries/

# Setup environment variables
ENV SHACL_HOME=./binaries/shacl-1.4.4

# Set the working directory inside the container
WORKDIR /app

# Copy the Python scripts into the container
COPY . .

# Copy requirements.txt and install them
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "src/sheval.py"]
CMD ["--help"]