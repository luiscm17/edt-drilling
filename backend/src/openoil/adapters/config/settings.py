"""Environment-backed settings for the local application runtime."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, case_sensitive=True)

    database_path: str = Field(
        default='cases.sqlite3',
        validation_alias='OPENOIL_DB_PATH',
    )
