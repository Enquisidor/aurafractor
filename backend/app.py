"""
Music Source Separation Backend - Flask application factory.

Routes live in routes/; business logic in services/; DB queries in database/models/.
"""

import os
import logging
from datetime import datetime

from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()

from utils.logging import setup_logging
from utils.monitoring import get_metrics_snapshot
from database.connection import health_check

setup_logging()
logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False

    # Register blueprints
    from routes.auth import bp as auth_bp
    from routes.upload import bp as upload_bp
    from routes.extraction import bp as extraction_bp
    from routes.user import bp as user_bp
    from routes.webhooks import bp as webhooks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(extraction_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(webhooks_bp)

    # Health + metrics
    @app.route('/health')
    def health():
        db_ok = health_check() if not MOCK_MODE else True
        return jsonify({
            'status': 'ok' if db_ok else 'degraded',
            'db': 'ok' if db_ok else 'unavailable',
            'mock_mode': MOCK_MODE,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 200 if db_ok else 503

    @app.route('/metrics')
    def metrics():
        return jsonify(get_metrics_snapshot())

    # Error handlers
    @app.errorhandler(400)
    def bad_request(_e):
        return jsonify({'error': 'Bad request'}), 400

    @app.errorhandler(401)
    def unauthorized(_e):
        return jsonify({'error': 'Unauthorized'}), 401

    @app.errorhandler(403)
    def forbidden(_e):
        return jsonify({'error': 'Forbidden'}), 403

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(_e):
        logger.error('Unhandled 500: %s', _e)
        return jsonify({'error': 'Internal server error'}), 500

    return app


app = create_app()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development',
    )
