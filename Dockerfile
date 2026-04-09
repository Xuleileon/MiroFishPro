FROM python:3.11

RUN apt-get update \n  && apt-get install -y --no-install-recommends nodejs npm \n  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

RUN npm ci \n  && npm ci --prefix frontend \n  && cd backend && uv sync --frozen

COPY . .

EXPOSE 3000 5001

CMD ["npm", "run", "dev"]