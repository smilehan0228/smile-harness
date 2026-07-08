"""T18: 云部署测试 — 验证部署配置文件存在且格式正确。"""

import yaml
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_DIR = PROJECT_ROOT / "deploy"


def test_docker_compose_exists():
    """docker-compose.yml 存在。"""
    compose_file = DEPLOY_DIR / "docker-compose.yml"
    assert compose_file.exists(), f"{compose_file} not found"


def test_docker_compose_valid_yaml():
    """docker-compose.yml 是有效 YAML 且包含 web 服务。"""
    compose_file = DEPLOY_DIR / "docker-compose.yml"
    with open(compose_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data is not None, "docker-compose.yml is empty or invalid"
    assert "services" in data, "docker-compose.yml missing 'services' key"
    assert "web" in data["services"], "docker-compose.yml missing 'web' service"

    web = data["services"]["web"]
    assert "ports" in web, "web service missing 'ports'"
    assert "8000:8000" in web["ports"], "web service missing port mapping 8000:8000"


def test_deploy_readme_exists():
    """deploy/README.md 存在。"""
    readme_file = DEPLOY_DIR / "README.md"
    assert readme_file.exists(), f"{readme_file} not found"


def test_deploy_readme_has_content():
    """deploy/README.md 包含部署相关内容。"""
    readme_file = DEPLOY_DIR / "README.md"
    content = readme_file.read_text(encoding="utf-8")
    assert "部署" in content or "deploy" in content.lower(), "README.md missing deployment content"
    assert "docker" in content.lower(), "README.md missing Docker instructions"


def test_nginx_conf_exists():
    """nginx.conf 存在（可选但推荐）。"""
    nginx_file = DEPLOY_DIR / "nginx.conf"
    assert nginx_file.exists(), f"{nginx_file} not found"


def test_nginx_conf_valid():
    """nginx.conf 包含必要配置。"""
    nginx_file = DEPLOY_DIR / "nginx.conf"
    content = nginx_file.read_text(encoding="utf-8")
    assert "proxy_pass" in content, "nginx.conf missing proxy_pass directive"
    assert "upstream" in content, "nginx.conf missing upstream block"


def test_dockerfile_exists():
    """Dockerfile 存在于项目根目录。"""
    dockerfile = PROJECT_ROOT / "Dockerfile"
    assert dockerfile.exists(), f"{dockerfile} not found"


def test_dockerfile_valid():
    """Dockerfile 包含必要指令。"""
    dockerfile = PROJECT_ROOT / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")
    assert "FROM python" in content, "Dockerfile missing FROM python base image"
    assert "EXPOSE" in content, "Dockerfile missing EXPOSE directive"
    assert "minicc" in content, "Dockerfile missing minicc command"
    # Web 部署通过 docker-compose command 覆盖，不要求 Dockerfile 含 uvicorn