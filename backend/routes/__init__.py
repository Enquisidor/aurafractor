"""Flask route blueprints."""

from routes.auth import bp as auth_bp
from routes.upload import bp as upload_bp
from routes.extraction import bp as extraction_bp
from routes.user import bp as user_bp
from routes.webhooks import bp as webhooks_bp

__all__ = ['auth_bp', 'upload_bp', 'extraction_bp', 'user_bp', 'webhooks_bp']
