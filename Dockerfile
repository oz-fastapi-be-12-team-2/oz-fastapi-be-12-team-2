# 베이스 이미지
FROM python:3.13-slim

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

# 필수 패키지 설치 (uv 실행 및 빌드 도구 등)
RUN apt-get update && apt-get install -y curl build-essential && apt-get clean && rm -rf /var/lib/apt/lists/*

# uv 설치
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# 작업 디렉토리 설정
WORKDIR /app

# pyproject.toml & uv.lock 복사 및 설치
COPY ./pyproject.toml ./uv.lock ./

RUN uv sync --all-packages

# 애플리케이션 코드 복사
COPY ./app ./app

# 포트 설정
EXPOSE 8000

# 스크립트 복사 및 권한 부여
COPY ./scripts ./scripts
RUN chmod +x ./scripts/run.sh

# run.sh 실행
CMD ["uv","run","sh","/app/scripts/run.sh"]
# "uv", "run","sh", 절대경로 변경 /app
