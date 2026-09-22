from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Salon AutoZone"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/salon_autozone"


settings = Settings()
