FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# 复制源码
COPY smile_harness/ smile_harness/
COPY README.md .

# 暴露端口（Web 前端）
EXPOSE 8000

# 默认命令（CLI 模式）
# Web 部署时通过 docker-compose command 覆盖为 uvicorn
CMD ["minicc", "--help"]