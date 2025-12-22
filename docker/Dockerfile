FROM registry.company.app/base-images/python:3.10.4

ARG ARTIFACT_ID

RUN mkdir -p /opt/company/${ARTIFACT_ID}

WORKDIR /opt/company/${ARTIFACT_ID}

COPY --chown=company:company . .

RUN pip install --no-cache-dir -r requirements.txt

# RUN apt-get update && apt-get install -y supervisor

# Set the entry point to the custom Python script
ENTRYPOINT ["python3", "-m", "main"]
