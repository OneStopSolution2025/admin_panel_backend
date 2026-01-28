"""
Configuration Management - Production Grade
Secure, validated, zero-error configuration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application Settings - Production Grade
    
    All sensitive values MUST be in environment variables
    No default secrets allowed
    """
    
    # ============================================
    # APPLICATION
    # ============================================
    APP_NAME: str = "RapidReportz"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # ============================================
    # SECURITY - NO DEFAULTS ALLOWED
    # ============================================
    SECRET_KEY: str 
    JWT_SECRET_KEY: str 
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ============================================
    # DATABASE
    # ============================================
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    
    # ============================================
    # CORS
    # ============================================
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    
    # ============================================
    # PAYMENT GATEWAY
    # ============================================
    BILLPLZ_API_KEY: Optional[str] = None
    BILLPLZ_COLLECTION_ID: Optional[str] = None
    BILLPLZ_X_SIGNATURE: Optional[str] = None
    BILLPLZ_API_URL: str = "https://www.billplz-sandbox.com/api/v3"
    
    # ============================================
    # SMS (Optional)
    # ============================================
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    
    # ============================================
    # REDIS (Optional - for caching)
    # ============================================
    REDIS_URL: Optional[str] = None
    REDIS_PASSWORD: Optional[str] = None
    
    # ============================================
    # MONITORING
    # ============================================
    SENTRY_DSN: Optional[str] = None
    
    # ============================================
    # RATE LIMITING
    # ============================================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_LOGIN: int = 5  # Login attempts per minute
    
    # ============================================
    # FILE UPLOAD
    # ============================================
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: list = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            # Prioritize environment variables over .env file
            return env_settings, file_secret_settings, init_settings
    
    def __init__(self, **kwargs):
        """
        Initialize settings with validation
        Raises ValueError if critical configs are missing
        """
        super().__init__(**kwargs)
        
        # Validate critical security settings
        self._validate_security()
        self._validate_database()
    
    def _validate_security(self):
        """Validate security configuration"""
        
        # SECRET_KEY validation
        if not self.SECRET_KEY:
            raise ValueError(
                "❌ CRITICAL: SECRET_KEY environment variable is required!\n"
                "Generate a secure key: openssl rand -hex 32\n"
                "Then set: export SECRET_KEY='your-generated-key'"
            )
        
        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                "❌ CRITICAL: SECRET_KEY must be at least 32 characters long!\n"
                "Generate a secure key: openssl rand -hex 32"
            )
        
        if self.SECRET_KEY in ["your-secret-key", "changeme", "secret", "test"]:
            raise ValueError(
                "❌ CRITICAL: SECRET_KEY contains an insecure default value!\n"
                "Generate a secure key: openssl rand -hex 32"
            )
        
        # JWT_SECRET_KEY validation
        if not self.JWT_SECRET_KEY:
            raise ValueError(
                "❌ CRITICAL: JWT_SECRET_KEY environment variable is required!\n"
                "Generate a secure key: openssl rand -hex 32\n"
                "Then set: export JWT_SECRET_KEY='your-generated-key'"
            )
        
        if len(self.JWT_SECRET_KEY) < 32:
            raise ValueError(
                "❌ CRITICAL: JWT_SECRET_KEY must be at least 32 characters long!\n"
                "Generate a secure key: openssl rand -hex 32"
            )
        
        if self.JWT_SECRET_KEY in ["your-jwt-secret", "changeme", "secret", "test"]:
            raise ValueError(
                "❌ CRITICAL: JWT_SECRET_KEY contains an insecure default value!\n"
                "Generate a secure key: openssl rand -hex 32"
            )
        
        # Ensure different keys
        if self.SECRET_KEY == self.JWT_SECRET_KEY:
            logger.warning(
                "⚠️  WARNING: SECRET_KEY and JWT_SECRET_KEY should be different!\n"
                "Using the same key for both reduces security."
            )
    
    def _validate_database(self):
        """Validate database configuration"""
        if not self.DATABASE_URL:
            raise ValueError(
                "❌ CRITICAL: DATABASE_URL environment variable is required!\n"
                "Example: postgresql://user:password@host:port/database"
            )
        
        if "postgresql://" not in self.DATABASE_URL and "postgres://" not in self.DATABASE_URL:
            raise ValueError(
                "❌ CRITICAL: DATABASE_URL must be a PostgreSQL connection string!\n"
                "Example: postgresql://user:password@host:port/database"
            )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() in ["development", "dev", "local"]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Singleton pattern for performance
    """
    return Settings()


# Global settings instance
settings = get_settings()


# ============================================
# CONFIGURATION SUMMARY
# ============================================

def print_config_summary():
    """Print configuration summary (safe - no secrets)"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("📋 CONFIGURATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"Database: {'✅ Configured' if settings.DATABASE_URL else '❌ Missing'}")
    logger.info(f"Secret Keys: {'✅ Configured' if settings.SECRET_KEY and settings.JWT_SECRET_KEY else '❌ Missing'}")
    logger.info(f"Payment Gateway: {'✅ Billplz Configured' if settings.BILLPLZ_API_KEY else '⚠️  Not Configured'}")
    logger.info(f"SMS Service: {'✅ Twilio Configured' if settings.TWILIO_ACCOUNT_SID else '⚠️  Not Configured'}")
    logger.info(f"Redis Cache: {'✅ Configured' if settings.REDIS_URL else '⚠️  Not Configured'}")
    logger.info(f"Monitoring: {'✅ Sentry Configured' if settings.SENTRY_DSN else '⚠️  Not Configured'}")
    logger.info("=" * 60)
    logger.info("")


# Print configuration on import
if __name__ != "__main__":
    print_config_summary()
