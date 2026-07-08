# smile-harness 部署文档

## 概述

smile-harness 提供 WebUI（FastAPI + 极简聊天页），可通过以下方式部署到云服务器。

## 部署架构

```
用户浏览器
    |
  [公网 IP:80/8000]
    |
  [Nginx 反向代理]（可选）
    |
  [uvicorn :8000] — FastAPI 应用
    |
  [smile_harness 内核] — AgentLoop + MockLLM
```

## 方式一：Docker 部署（推荐）

### 前置条件

- 服务器安装 Docker 和 Docker Compose
- 开放防火墙端口 8000（或 80）

### 步骤

1. **克隆仓库**

```bash
git clone <repo-url> /opt/smile-harness
cd /opt/smile-harness
```

2. **启动服务**

```bash
cd deploy
docker-compose up -d
```

3. **验证**

```bash
curl http://localhost:8000/
```

应返回 HTML 聊天页面。

4. **查看日志**

```bash
docker-compose logs -f
```

5. **停止服务**

```bash
docker-compose down
```

## 方式二：阿里云 ECS 部署

### 前置条件

- 阿里云 ECS 实例（建议 CentOS 7+ / Ubuntu 20.04+）
- 安全组开放端口 8000（或 80）
- Python 3.11+

### 步骤

1. **连接 ECS**

```bash
ssh root@<your-ecs-public-ip>
```

2. **安装依赖**

```bash
# Ubuntu
apt update && apt install -y python3.11 python3.11-venv git nginx

# CentOS
yum install -y python3.11 git nginx
```

3. **克隆并安装**

```bash
git clone <repo-url> /opt/smile-harness
cd /opt/smile-harness
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

4. **配置 systemd 服务**

创建 `/etc/systemd/system/smile-harness.service`：

```ini
[Unit]
Description=smile-harness WebUI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/smile-harness
ExecStart=/opt/smile-harness/.venv/bin/uvicorn smile_harness.web.server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

5. **启动服务**

```bash
systemctl daemon-reload
systemctl enable smile-harness
systemctl start smile-harness
systemctl status smile-harness
```

6. **（可选）配置 Nginx 反向代理**

```bash
cp /opt/smile-harness/deploy/nginx.conf /etc/nginx/conf.d/smile-harness.conf
# 修改 server_name 为你的域名或公网 IP
nginx -t
systemctl reload nginx
```

## 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SMILE_HARNESS_PORT` | 服务端口 | `8000` |
| `SMILE_HARNESS_HOST` | 绑定地址 | `0.0.0.0` |
| `SMILE_HARNESS_WORKSPACE` | 工作目录 | `.` |

可通过 docker-compose.yml 的 `environment` 字段或 systemd 的 `Environment` 字段设置。

## 健康检查

Docker 部署已内置健康检查（每 30s 检测 `/` 端点）。

手动检查：

```bash
curl -f http://<your-server-ip>:8000/
```

预期返回 HTTP 200 和 HTML 聊天页面。

## 公网访问

部署完成后，通过以下地址访问：

- 直接访问：`http://<your-server-ip>:8000/`
- 通过 Nginx：`http://<your-server-ip>/` 或 `http://<your-domain>/`

## 注意事项

1. **安全组 / 防火墙**：确保云服务商安全组和服务器防火墙开放对应端口。
2. **HTTPS**：生产环境建议配置 SSL 证书（可通过 Let's Encrypt + Certbot 免费获取）。
3. **真实 LLM 接入**：当前使用 MockLLM 演示，接入真实 LLM 后需配置 API Key 等环境变量。