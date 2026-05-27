from functools import lru_cache

from pydantic import Field
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

    openai_model: str = Field(default="", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    babeldoc_bin: str = Field(default="babeldoc", alias="BABELDOC_BIN")
    babeldoc_qps: int = Field(default=20, alias="BABELDOC_QPS")
    babeldoc_pool_max_workers: int = Field(default=20, alias="BABELDOC_POOL_MAX_WORKERS")
    babeldoc_output_subdir: str = Field(default="babeldoc", alias="BABELDOC_OUTPUT_SUBDIR")

    task_workspace_root: str = "runtime/tasks"
    upload_tmp_root: str = "runtime/uploads"
    max_upload_bytes: int = 250 * 1024 * 1024
    default_source_language: str = "en"
    default_target_language: str = "ch"
    default_created_by: str = "internal-user"
    cors_origins: list[str] = ["*"]

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
