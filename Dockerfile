FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm libmagic1 curl && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

RUN npm ci && npm ci --prefix frontend

RUN cd backend && uv sync --frozen && uv pip install --python .venv torch --index-url https://download.pytorch.org/whl/cpu --reinstall --no-cache-dir && uv pip uninstall --python .venv nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 nvidia-cuda-nvrtc-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 nvidia-cusparselt-cu12 nvidia-nccl-cu12 nvidia-nvjitlink-cu12 nvidia-nvtx-cu12 nvidia-nvshmem-cu12 nvidia-cufile-cu12 triton 2>/dev/null; true

COPY . .

EXPOSE 3000 5001

CMD ["npx", "concurrently", "-n", "backend,frontend", "-c", "yellow,cyan", "npm run backend", "npm run frontend"]
