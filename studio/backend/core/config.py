"""
设计院 (Studio) - 全局配置
"""
import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class StudioSettings:
    """设计院配置"""
    # GitHub
    github_token: str = os.environ.get("GITHUB_TOKEN", "")
    github_repo: str = os.environ.get("GITHUB_REPO", "macaulishchina/GoldenNest")

    # 工作区路径
    workspace_path: str = os.environ.get("WORKSPACE_PATH", "/workspace")

    # 数据存储
    data_path: str = os.environ.get("STUDIO_DATA_PATH", "/data")
    plans_path: str = ""
    db_backups_path: str = ""
    uploads_path: str = ""

    # GitHub Models API
    github_models_endpoint: str = "https://models.inference.ai.azure.com"

    # 部署配置
    health_check_timeout: int = 60
    health_check_retries: int = 3
    health_check_interval: int = 5

    # 受保护的服务 (永远不会被部署流水线触碰)
    protected_services: List[str] = field(default_factory=lambda: ["gateway", "studio"])

    # 设计院认证
    studio_admin_user: str = os.environ.get("STUDIO_ADMIN_USER", "admin")
    studio_admin_pass: str = os.environ.get("STUDIO_ADMIN_PASS", "")
    studio_secret_key: str = os.environ.get("STUDIO_SECRET_KEY", "")
    studio_token_expire_days: int = int(os.environ.get("STUDIO_TOKEN_EXPIRE_DAYS", "7"))

    # 主项目 API (用于验证主项目 token)
    main_api_url: str = os.environ.get("MAIN_API_URL", "http://golden-nest-backend:8000")

    def __post_init__(self):
        self.plans_path = os.path.join(self.data_path, "plans")
        self.db_backups_path = os.path.join(self.data_path, "db-backups")
        self.uploads_path = os.path.join(self.data_path, "uploads")
        os.makedirs(self.plans_path, exist_ok=True)
        os.makedirs(self.db_backups_path, exist_ok=True)
        os.makedirs(self.uploads_path, exist_ok=True)
        # 自动生成 secret key
        if not self.studio_secret_key:
            import secrets
            self.studio_secret_key = secrets.token_urlsafe(32)
        # 自动生成管理员密码 (首次部署)
        if not self.studio_admin_pass:
            import secrets
            self.studio_admin_pass = secrets.token_urlsafe(16)
            import logging
            logger = logging.getLogger("studio.config")
            logger.warning(
                f"\n{'='*60}\n"
                f"⚠️  设计院管理员密码已自动生成:\n"
                f"    用户名: {self.studio_admin_user}\n"
                f"    密码: {self.studio_admin_pass}\n"
                f"    请设置环境变量 STUDIO_ADMIN_PASS 以使用固定密码\n"
                f"{'='*60}"
            )
            # 也输出到 stdout 确保 docker logs 可见
            print(f"\n⚠️  Studio Admin: {self.studio_admin_user} / {self.studio_admin_pass}\n", flush=True)


settings = StudioSettings()
