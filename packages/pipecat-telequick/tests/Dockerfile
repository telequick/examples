# Verification image: real pipecat-ai + the two local packages.
#   docker build -f packages/pipecat-telequick/tests/Dockerfile -t cc-tq-pipecat-test .
#   docker run --rm cc-tq-pipecat-test
FROM python:3.12-slim
RUN pip install --no-cache-dir "pipecat-ai>=1.5,<2" aioquic
WORKDIR /w
COPY packages/telequick-agents /w/telequick-agents
COPY packages/pipecat-telequick /w/pipecat-telequick
ENV PYTHONPATH=/w/telequick-agents:/w/pipecat-telequick
CMD ["python", "/w/pipecat-telequick/tests/smoke.py"]
