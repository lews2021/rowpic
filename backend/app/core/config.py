"""Application configuration."""
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        env_prefix="ROWPIC_",
        extra="ignore",
    )

    # Server
    host: str = "127.0.0.1"
    port: int = 8765
    reload: bool = False
    workers: int = 1

    # Caching / thumbnails
    thumb_cache_dir: Path = BASE_DIR / "cache" / "thumbs"
    preview_cache_dir: Path = BASE_DIR / "cache" / "previews"
    cache_dir: Path = BASE_DIR / "cache"
    max_thumb_size: int = 480
    max_preview_size: int = 2400

    # Scanning
    supported_extensions: List[str] = [
        # Standard
        ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp", ".heic", ".heif",
        # RAW
        ".raw", ".arw", ".sr2", ".srf", ".nef", ".nrw", ".cr2", ".cr3",
        ".dng", ".orf", ".rw2", ".raf", ".pef", ".srw", ".3fr", ".iiq",
        ".x3f", ".mrw", ".mef", ".erf", ".kdc", ".dcr", ".fit", ".fts",
    ]

    # Focus / face analysis
    blur_threshold: float = 60.0
    face_blur_threshold: float = 35.0
    face_min_size: int = 40
    face_detect_confidence: float = 0.5

    # AI color
    enable_ai_color: bool = False
    ai_color_model: str = "auto"

    # Allowed scan roots (security)
    allowed_roots: List[str] = []


settings = Settings()
settings.cache_dir.mkdir(parents=True, exist_ok=True)
settings.thumb_cache_dir.mkdir(parents=True, exist_ok=True)
settings.preview_cache_dir.mkdir(parents=True, exist_ok=True)
