# The Hugging Face Space: the web app and the API from one image over a database
# shipped in the image, with online retrieval off (docs/content/deployments-and-approval.md 1.2).
FROM node:22-slim AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
COPY packs/library.sqlite public/library.sqlite
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY lifekit/ lifekit/
COPY packs/library.sqlite packs/library.sqlite
COPY packs/sections.tsv packs/questions.tsv packs/profile-questions.json packs/pull_rules.tsv packs/source-rules.tsv packs/
COPY --from=web /src/web/dist web/dist
COPY --from=web /src/web/public/fonts web/public/fonts
ENV LIFEKIT_ONLINE_RETRIEVAL=off LIFEKIT_QUEUE_WORKER=off LIFEKIT_MODEL_SMALL=hf:meta-llama/Llama-3.1-8B-Instruct PORT=7860
EXPOSE 7860
CMD ["uv", "run", "--no-sync", "uvicorn", "lifekit.api:app", "--host", "0.0.0.0", "--port", "7860"]
