FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install uv
COPY . .
RUN uv venv
RUN uv sync --dev --all-extras

#RUN uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
CMD ["uv", "run", "examples/aip_trader_agents/trader_agent_gradio.py"]