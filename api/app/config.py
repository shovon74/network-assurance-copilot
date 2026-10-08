from psycopg.conninfo import make_conninfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    @property
    def db_conninfo(self) -> str:
        return make_conninfo(
            host=self.postgres_host,
            port=self.postgres_port,
            dbname=self.postgres_db,
            user=self.postgres_user,
            password=self.postgres_password,
        )


settings = Settings()
