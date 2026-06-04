from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LaTeXTrans Backend"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    environment: str = "development"

    backend_database_url: str | None = Field(default=None, alias="BACKEND_DATABASE_URL")
    mysql_username: str = Field(default="root", alias="MYSQL_USERNAME")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")
    mysql_host: str = Field(default="127.0.0.1", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_database: str = Field(default="latex_trans", alias="MYSQL_DATABASE")
    mysql_pool_recycle: int = Field(default=1800, alias="MYSQL_POOL_RECYCLE")
    sql_echo: bool = False

    minio_url: str = Field(default="127.0.0.1:9000", alias="MINIO_URL")
    minio_access_key: str = Field(default="", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="", alias="MINIO_SECRET_KEY")
    minio_bucket_tasks: str = "latex-trans-tasks"
    minio_secure: bool = False
    artifact_download_url_expire_seconds: int = Field(default=600, alias="ARTIFACT_DOWNLOAD_URL_EXPIRE_SECONDS")

    openai_model: str = Field(default="", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    babeldoc_bin: str = Field(default="babeldoc", alias="BABELDOC_BIN")
    babeldoc_qps: int = Field(default=20, alias="BABELDOC_QPS")
    babeldoc_pool_max_workers: int = Field(default=20, alias="BABELDOC_POOL_MAX_WORKERS")
    babeldoc_output_subdir: str = Field(default="babeldoc", alias="BABELDOC_OUTPUT_SUBDIR")
    task_timeout_seconds: int = Field(default=20 * 60, alias="TASK_TIMEOUT_SECONDS")

    task_workspace_root: str = "runtime/tasks"
    upload_tmp_root: str = "runtime/uploads"
    max_upload_bytes: int = 250 * 1024 * 1024
    upload_stream_chunk_bytes: int = Field(default=1024 * 1024, alias="UPLOAD_STREAM_CHUNK_BYTES")
    default_source_language: str = "en"
    default_target_language: str = "ch"
    default_created_by: str = "internal-user"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # JWT Auth
    jwt_secret_key: str = Field(default="dev-insecure-local-jwt-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=10080, alias="JWT_EXPIRE_MINUTES")  # 7 days
    auth_cookie_name: str = Field(default="latextrans_session", alias="AUTH_COOKIE_NAME")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")
    auth_cookie_samesite: str = Field(default="lax", alias="AUTH_COOKIE_SAMESITE")

    # User defaults
    default_user_translation_quota: int = Field(default=0, alias="DEFAULT_USER_TRANSLATION_QUOTA")
    auth_register_enabled: bool = Field(default=False, alias="AUTH_REGISTER_ENABLED")

    # Admin bootstrap
    admin_bootstrap_enabled: bool = Field(default=False, alias="ADMIN_BOOTSTRAP_ENABLED")
    admin_bootstrap_username: str = Field(default="", alias="ADMIN_BOOTSTRAP_USERNAME")
    admin_bootstrap_password: str = Field(default="", alias="ADMIN_BOOTSTRAP_PASSWORD")
    admin_tasks_bypass_quota: bool = Field(default=True, alias="ADMIN_TASKS_BYPASS_QUOTA")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_login_limit: int = Field(default=10, alias="RATE_LIMIT_LOGIN_LIMIT")
    rate_limit_login_window_seconds: int = Field(default=300, alias="RATE_LIMIT_LOGIN_WINDOW_SECONDS")
    rate_limit_register_limit: int = Field(default=5, alias="RATE_LIMIT_REGISTER_LIMIT")
    rate_limit_register_window_seconds: int = Field(default=3600, alias="RATE_LIMIT_REGISTER_WINDOW_SECONDS")
    rate_limit_task_create_limit: int = Field(default=20, alias="RATE_LIMIT_TASK_CREATE_LIMIT")
    rate_limit_task_create_window_seconds: int = Field(default=3600, alias="RATE_LIMIT_TASK_CREATE_WINDOW_SECONDS")

    # Cache
    cache_enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    cache_version: int = Field(default=1, alias="CACHE_VERSION")
    cache_build_stale_minutes: int = Field(default=60, alias="CACHE_BUILD_STALE_MINUTES")

    # Discovery / Huey
    redis_url: str = Field(default="redis://127.0.0.1:6379/1", alias="REDIS_URL")
    discovery_timezone: str = Field(default="Asia/Shanghai", alias="DISCOVERY_TIMEZONE")
    discovery_schedule_hour: int = Field(default=9, alias="DISCOVERY_SCHEDULE_HOUR")
    discovery_schedule_minute: int = Field(default=0, alias="DISCOVERY_SCHEDULE_MINUTE")
    discovery_huey_enabled: bool = Field(default=False, alias="DISCOVERY_HUEY_ENABLED")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def database_url(self) -> str:
        if self.backend_database_url:
            return self.backend_database_url

        return (
            f"mysql+pymysql://{self.mysql_username}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        insecure_jwt_values = {
            "",
            "changeme",
            "changeme-please-set-in-env",
            "dev-insecure-local-jwt-secret",
            "secret",
            "test",
        }
        if self.auth_cookie_samesite.lower() not in {"lax", "strict", "none"}:
            raise ValueError("AUTH_COOKIE_SAMESITE must be one of: lax, strict, none.")
        if self.upload_stream_chunk_bytes <= 0:
            raise ValueError("UPLOAD_STREAM_CHUNK_BYTES must be greater than 0.")
        if self.task_timeout_seconds <= 0:
            raise ValueError("TASK_TIMEOUT_SECONDS must be greater than 0.")
        if self.max_upload_bytes <= 0:
            raise ValueError("MAX_UPLOAD_BYTES must be greater than 0.")
        if self.artifact_download_url_expire_seconds <= 0:
            raise ValueError("ARTIFACT_DOWNLOAD_URL_EXPIRE_SECONDS must be greater than 0.")
        if not (0 <= self.discovery_schedule_hour <= 23):
            raise ValueError("DISCOVERY_SCHEDULE_HOUR must be between 0 and 23.")
        if not (0 <= self.discovery_schedule_minute <= 59):
            raise ValueError("DISCOVERY_SCHEDULE_MINUTE must be between 0 and 59.")

        if self.is_production:
            if self.jwt_secret_key in insecure_jwt_values or len(self.jwt_secret_key) < 32:
                raise ValueError("Production requires a strong JWT_SECRET_KEY with at least 32 characters.")
            if not self.cors_origins or any(origin == "*" for origin in self.cors_origins):
                raise ValueError("Production requires explicit CORS_ORIGINS; wildcard origins are not allowed.")
            if self.admin_bootstrap_enabled:
                raise ValueError("ADMIN_BOOTSTRAP_ENABLED must be false in production.")
            if self.auth_register_enabled:
                raise ValueError("AUTH_REGISTER_ENABLED must be false in production unless you add stronger controls.")
            if not self.auth_cookie_secure:
                raise ValueError("AUTH_COOKIE_SECURE must be true in production.")
            minio_url = self.minio_url.lower()
            is_local_minio = minio_url.startswith(("127.0.0.1", "localhost"))
            if not is_local_minio and not (self.minio_secure or minio_url.startswith("https://")):
                raise ValueError("Production MinIO endpoints must use TLS or set MINIO_SECURE=true.")

        if self.admin_bootstrap_enabled:
            if not self.admin_bootstrap_username or not self.admin_bootstrap_password:
                raise ValueError(
                    "ADMIN_BOOTSTRAP_USERNAME and ADMIN_BOOTSTRAP_PASSWORD are required when admin bootstrap is enabled."
                )
            insecure_admin_passwords = {"admin123", "password", "changeme", self.admin_bootstrap_username}
            if self.admin_bootstrap_password in insecure_admin_passwords or len(self.admin_bootstrap_password) < 12:
                raise ValueError("Admin bootstrap password must be at least 12 characters and not use weak defaults.")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
