"""
Music Source Separation Backend - Flask API Starter

Usage:
    python app.py

Environment variables:
    FLASK_ENV=development
    DATABASE_URL=postgresql://user:pass@localhost/music_separation
    GCS_BUCKET=music-separation-bucket
    JWT_SECRET=your-secret-key
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Tuple, Optional

from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
import jwt
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import SimpleConnectionPool

load_dotenv()

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Database connection pool
db_pool = None

def get_db():
    """Get database connection from pool"""
    global db_pool
    if db_pool is None:
        db_pool = SimpleConnectionPool(
            1, 20,
            os.getenv('DATABASE_URL', 'postgresql://localhost/music_separation')
        )
    return db_pool.getconn()

def return_db(conn):
    """Return connection to pool"""
    db_pool.putconn(conn)

# ============================================================================
# UTILITIES
# ============================================================================

def mock_response(data: Dict[str, Any], status: int = 200) -> Tuple[Dict, int]:
    """Return mock response with proper formatting"""
    return jsonify(data), status

def require_auth(f):
    """Decorator to verify JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = request.headers.get('X-User-ID')
        
        if not token or not user_id:
            return mock_response({'error': 'Unauthorized'}, 401)
        
        try:
            # In mock mode, just validate format
            if not is_valid_uuid(user_id):
                return mock_response({'error': 'Invalid user_id'}, 401)
        except Exception as e:
            return mock_response({'error': str(e)}, 401)
        
        # Pass user_id to endpoint
        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated

def is_valid_uuid(val):
    """Check if string is valid UUID"""
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def generate_jwt_token(user_id: str, expires_in_hours: int = 24) -> str:
    """Generate JWT token (mock)"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, os.getenv('JWT_SECRET', 'dev-secret'), algorithm='HS256')

def hash_user_id_for_training(user_id: str) -> str:
    """Create non-reversible hash of user_id for training data"""
    return hashlib.sha256(user_id.encode()).hexdigest()[:8]

def compute_ambiguity_score(label: str) -> float:
    """
    Score label ambiguity: 0.0 = clear, 1.0 = very ambiguous
    
    Allows 1-word labels. Only flags vague or incomplete inputs.
    """
    label_lower = label.lower().strip()
    
    # Empty or too short
    if len(label_lower) == 0:
        return 1.0
    
    # Single very generic word
    vague_words = ['thing', 'stuff', 'sound', 'whatever', 'music', 'audio']
    if label_lower in vague_words:
        return 0.95
    
    # Contains vague language
    if any(vague in label_lower for vague in vague_words):
        return 0.8
    
    # Single instrument word: "vocals", "drums", "bass" - perfectly fine
    common_instruments = [
        'vocals', 'drums', 'bass', 'guitar', 'synth', 'pad', 'kick', 
        'snare', 'hi-hat', 'cymbals', 'strings', 'piano', 'keys'
    ]
    if label_lower in common_instruments:
        return 0.1  # Very clear
    
    # Multi-word with descriptors: "lead vocals", "kick drum" - clear
    if len(label_lower.split()) > 1:
        return 0.2
    
    # Unknown single word: could go either way
    return 0.4

# ============================================================================
# NLP RULE ENGINE
# ============================================================================

NLP_RULES = {
    # Vocal sources
    'vocals': {
        'source': 'vocal',
        'isolation_level': 0.7,
        'dryness': 0.5,
        'preserve_reverb': True,
    },
    'lead vocals': {
        'source': 'vocal',
        'vocal_type': 'lead',
        'isolation_level': 0.85,
        'dryness': 0.5,
        'preserve_reverb': True,
    },
    'lead vocals without reverb': {
        'source': 'vocal',
        'vocal_type': 'lead',
        'isolation_level': 0.9,
        'dryness': 0.95,
        'preserve_reverb': False,
    },
    'isolated vocals': {
        'source': 'vocal',
        'isolation_level': 0.95,
        'dryness': 0.8,
        'separation_aggression': 0.9,
    },
    
    # Drum sources
    'drums': {
        'source': 'drum',
        'isolation_level': 0.7,
        'attack_preservation': 0.8,
    },
    'kick': {
        'source': 'drum',
        'drum_type': 'kick',
        'isolation_level': 0.85,
        'frequency_range': [20, 100],
    },
    'kick drum': {
        'source': 'drum',
        'drum_type': 'kick',
        'isolation_level': 0.85,
        'frequency_range': [20, 100],
    },
    'tight kick': {
        'source': 'drum',
        'drum_type': 'kick',
        'isolation_level': 0.9,
        'attack_preservation': 1.0,
        'bleed_suppression': 0.95,
    },
    'snare': {
        'source': 'drum',
        'drum_type': 'snare',
        'isolation_level': 0.75,
        'frequency_range': [100, 5000],
    },
    'hi-hats': {
        'source': 'drum',
        'drum_type': 'hi_hat',
        'isolation_level': 0.8,
        'frequency_range': [4000, 16000],
    },
    
    # Bass sources
    'bass': {
        'source': 'bass',
        'isolation_level': 0.75,
        'frequency_range': [20, 250],
    },
    'bass guitar': {
        'source': 'bass',
        'bass_type': 'guitar',
        'isolation_level': 0.75,
    },
    'bass synth': {
        'source': 'bass',
        'bass_type': 'synth',
        'isolation_level': 0.75,
    },
    
    # Other sources
    'synth': {
        'source': 'other',
        'synth_type': 'synth',
        'isolation_level': 0.7,
    },
    'pad': {
        'source': 'other',
        'synth_type': 'pad',
        'isolation_level': 0.7,
    },
    'guitar': {
        'source': 'other',
        'instrument_type': 'guitar',
        'isolation_level': 0.7,
    },
    'strings': {
        'source': 'other',
        'instrument_type': 'strings',
        'isolation_level': 0.7,
    },
    'piano': {
        'source': 'other',
        'instrument_type': 'piano',
        'isolation_level': 0.7,
    },
}

DESCRIPTORS = {
    'dry': {'dryness': 0.3},
    'wet': {'dryness': -0.3},
    'tight': {'isolation_level': 0.2, 'attack_preservation': 0.2},
    'loose': {'isolation_level': -0.2},
    'isolated': {'isolation_level': 0.25},
    'with': {'preserve_context': True},
    'without': {'suppress_context': True},
    'just': {'mask_everything_else': True},
    'only': {'mask_everything_else': True},
}

def parse_label_to_params(label: str) -> Dict[str, Any]:
    """
    Convert user label to NLP parameters.
    Returns: {source, isolation_level, ...} or {ambiguous: True}
    """
    label_lower = label.lower().strip()
    
    # Try exact match first
    if label_lower in NLP_RULES:
        params = NLP_RULES[label_lower].copy()
        return params
    
    # Try partial match (check if label contains rule key)
    for rule_label, rule_params in NLP_RULES.items():
        if rule_label in label_lower:
            params = rule_params.copy()
            
            # Apply descriptors
            for descriptor, modifier in DESCRIPTORS.items():
                if descriptor in label_lower:
                    for key, value in modifier.items():
                        if isinstance(value, (int, float)):
                            # Additive for numeric values
                            params[key] = params.get(key, 0.5) + value
                        else:
                            params[key] = value
            
            return params
    
    # No match: ambiguous
    return {
        'ambiguous': True,
        'user_label': label,
        'confidence': 0.0,
        'requires_clarification': True,
    }

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return mock_response({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    })

@app.route('/auth/register', methods=['POST'])
def register():
    """Register/initialize user (anonymous)"""
    data = request.get_json()
    device_id = data.get('device_id')
    app_version = data.get('app_version')
    
    if not device_id:
        return mock_response({'error': 'device_id required'}, 400)
    
    # Mock: generate IDs
    user_id = str(uuid.uuid4())
    session_token = generate_jwt_token(user_id, expires_in_hours=24)
    refresh_token = generate_jwt_token(user_id, expires_in_hours=30*24)
    
    return mock_response({
        'user_id': user_id,
        'session_token': session_token,
        'refresh_token': refresh_token,
        'expires_in': 86400,
        'subscription_tier': 'free',
        'credits_remaining': 100,
        'timestamp': datetime.utcnow().isoformat(),
    }, 201)

@app.route('/auth/refresh', methods=['POST'])
def refresh():
    """Refresh session token"""
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return mock_response({'error': 'refresh_token required'}, 400)
    
    # Mock: generate new session token
    # In production, verify refresh_token is valid first
    try:
        payload = jwt.decode(refresh_token, os.getenv('JWT_SECRET', 'dev-secret'), algorithms=['HS256'])
        user_id = payload['user_id']
    except:
        return mock_response({'error': 'Invalid refresh_token'}, 401)
    
    session_token = generate_jwt_token(user_id, expires_in_hours=24)
    
    return mock_response({
        'session_token': session_token,
        'expires_in': 86400,
    })

@app.route('/upload', methods=['POST'])
@require_auth
def upload():
    """Upload audio file"""
    if 'file' not in request.files:
        return mock_response({'error': 'file required'}, 400)
    
    file = request.files['file']
    metadata = request.form.get('metadata')
    
    if not file.filename:
        return mock_response({'error': 'filename required'}, 400)
    
    # Mock: generate track ID
    track_id = str(uuid.uuid4())
    gcs_path = f'gs://bucket/tracks/{track_id}/original.wav'
    audio_url = f'https://storage.googleapis.com/bucket/tracks/{track_id}/original.wav'
    
    return mock_response({
        'track_id': track_id,
        'uploaded_at': datetime.utcnow().isoformat(),
        'duration_seconds': 180,  # Mock
        'file_size_mb': 8.5,
        'audio_url': audio_url,
        'status': 'ready',
    }, 201)

@app.route('/extraction/suggest-labels', methods=['POST'])
@require_auth
def suggest_labels():
    """Get AI-suggested instrument labels"""
    data = request.get_json()
    track_id = data.get('track_id')
    
    if not track_id:
        return mock_response({'error': 'track_id required'}, 400)
    
    # Mock: return generic suggestions
    suggestions = [
        {
            'label': 'lead vocals',
            'confidence': 0.94,
            'frequency_range': [85, 255],
            'recommended': True,
        },
        {
            'label': 'kick drum',
            'confidence': 0.89,
            'frequency_range': [20, 100],
            'recommended': True,
        },
        {
            'label': 'snare',
            'confidence': 0.81,
            'frequency_range': [100, 5000],
            'recommended': False,
        },
        {
            'label': 'bass',
            'confidence': 0.76,
            'frequency_range': [30, 250],
            'recommended': True,
        },
        {
            'label': 'synth pad',
            'confidence': 0.68,
            'frequency_range': [200, 8000],
            'recommended': True,
        },
    ]
    
    return mock_response({
        'track_id': track_id,
        'suggested_labels': suggestions,
        'genre': 'indie_rock',
        'tempo': 94,
        'user_history_suggestions': ['vocal harmonies', 'isolated bass'],
    })

@app.route('/extraction/extract', methods=['POST'])
@require_auth
def extract():
    """Initiate extraction job"""
    data = request.get_json()
    track_id = data.get('track_id')
    sources = data.get('sources', [])
    
    if not track_id:
        return mock_response({'error': 'track_id required'}, 400)
    
    if not sources:
        return mock_response({'error': 'sources required'}, 400)
    
    # Process labels through NLP
    processed_sources = []
    ambiguous_labels = []
    
    for source in sources:
        label = source.get('label')
        model = source.get('model', 'demucs')
        
        nlp_params = parse_label_to_params(label)
        ambiguity = compute_ambiguity_score(label)
        
        if ambiguity > 0.6:
            ambiguous_labels.append({
                'label': label,
                'ambiguity_score': ambiguity,
                'suggestion': 'Consider refining this label for better results',
            })
        
        processed_sources.append({
            'label': label,
            'model': model,
            'nlp_params': nlp_params,
            'ambiguous': ambiguity > 0.6,
        })
    
    # Calculate cost
    base_cost = 5
    ambiguity_penalty = len(ambiguous_labels)
    total_cost = base_cost + ambiguity_penalty
    
    extraction_id = str(uuid.uuid4())
    job_id = f'job-{extraction_id[:8]}'
    
    return mock_response({
        'extraction_id': extraction_id,
        'track_id': track_id,
        'job_id': job_id,
        'status': 'queued',
        'sources_requested': len(sources),
        'models_used': list(set(s.get('model', 'demucs') for s in sources)),
        'estimated_time_seconds': 120,
        'cost_credits': total_cost,
        'ambiguous_labels': ambiguous_labels,
        'queue_position': 3,
        'created_at': datetime.utcnow().isoformat(),
    }, 201)

@app.route('/extraction/<extraction_id>', methods=['GET'])
@require_auth
def get_extraction_status(extraction_id):
    """Poll extraction job status"""
    # Mock: return completed status
    if not is_valid_uuid(extraction_id):
        return mock_response({'error': 'Invalid extraction_id'}, 400)
    
    # Randomly return processing or completed
    import random
    status = random.choice(['queued', 'processing', 'completed'])
    
    response = {
        'extraction_id': extraction_id,
        'status': status,
        'progress_percent': 0 if status == 'queued' else (45 if status == 'processing' else 100),
        'processing_started_at': datetime.utcnow().isoformat() if status != 'queued' else None,
    }
    
    if status == 'completed':
        response['completed_at'] = datetime.utcnow().isoformat()
        response['results'] = {
            'sources': [
                {
                    'label': 'lead vocals',
                    'model_used': 'demucs',
                    'duration_seconds': 180,
                    'audio_url': 'gs://bucket/extractions/{extraction_id}/lead_vocals.wav',
                    'waveform_url': 'gs://bucket/extractions/{extraction_id}/lead_vocals_waveform.json',
                },
                {
                    'label': 'drums',
                    'model_used': 'demucs',
                    'audio_url': 'gs://bucket/extractions/{extraction_id}/drums.wav',
                    'waveform_url': 'gs://bucket/extractions/{extraction_id}/drums_waveform.json',
                },
            ]
        }
    
    return mock_response(response)

@app.route('/extraction/<extraction_id>/feedback', methods=['POST'])
@require_auth
def submit_feedback(extraction_id):
    """Submit feedback on extraction"""
    data = request.get_json()
    feedback_type = data.get('feedback_type')
    
    if not feedback_type or feedback_type not in ['too_much', 'too_little', 'artifacts', 'good']:
        return mock_response({'error': 'Invalid feedback_type'}, 400)
    
    feedback_id = str(uuid.uuid4())
    reextraction_id = None
    cost = 0
    
    # If user provided refined label, queue re-extraction
    refined_label = data.get('refined_label')
    if refined_label and feedback_type != 'good':
        reextraction_id = str(uuid.uuid4())
        cost = 5
    
    return mock_response({
        'feedback_id': feedback_id,
        'extraction_id': extraction_id,
        'status': 'recorded' if feedback_type == 'good' else 'queued_for_reextraction',
        'reextraction_queued': reextraction_id is not None,
        'new_extraction_id': reextraction_id,
        'cost_credits': cost,
    }, 201)

@app.route('/user/history', methods=['GET'])
@require_auth
def user_history():
    """Get extraction history"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Mock: return sample history
    tracks = [
        {
            'track_id': str(uuid.uuid4()),
            'filename': 'song_1.mp3',
            'uploaded_at': (datetime.utcnow() - timedelta(days=1)).isoformat(),
            'extractions_count': 3,
            'latest_extraction': {
                'extraction_id': str(uuid.uuid4()),
                'status': 'completed',
                'sources_extracted': ['lead vocals', 'drums', 'bass'],
                'completed_at': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            },
        },
        {
            'track_id': str(uuid.uuid4()),
            'filename': 'song_2.mp3',
            'uploaded_at': (datetime.utcnow() - timedelta(days=3)).isoformat(),
            'extractions_count': 1,
            'latest_extraction': {
                'extraction_id': str(uuid.uuid4()),
                'status': 'completed',
                'sources_extracted': ['vocals', 'drums'],
                'completed_at': (datetime.utcnow() - timedelta(days=2)).isoformat(),
            },
        },
    ]
    
    return mock_response({
        'total_tracks': 47,
        'tracks': tracks,
        'pagination': {
            'limit': limit,
            'offset': offset,
            'has_more': True,
        },
    })

@app.route('/user/credits', methods=['GET'])
@require_auth
def user_credits():
    """Get user credit balance"""
    return mock_response({
        'current_balance': 50,
        'monthly_allowance': 100,
        'subscription_tier': 'free',
        'reset_date': (datetime.utcnow() + timedelta(days=25)).isoformat(),
        'usage_this_month': {
            'extractions': 8,
            'credits_spent': 50,
            'ambiguous_labels_flagged': 2,
        },
    })

@app.route('/track/<track_id>', methods=['DELETE'])
@require_auth
def delete_track(track_id):
    """Delete track (GDPR compliance)"""
    if not is_valid_uuid(track_id):
        return mock_response({'error': 'Invalid track_id'}, 400)
    
    return mock_response({
        'track_id': track_id,
        'deleted_at': datetime.utcnow().isoformat(),
        'files_deleted': 12,
        'feedback_anonymized': True,
    })

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(400)
def bad_request(error):
    return mock_response({'error': 'Bad request'}, 400)

@app.errorhandler(401)
def unauthorized(error):
    return mock_response({'error': 'Unauthorized'}, 401)

@app.errorhandler(404)
def not_found(error):
    return mock_response({'error': 'Not found'}, 404)

@app.errorhandler(500)
def internal_error(error):
    return mock_response({'error': 'Internal server error'}, 500)

# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development',
    )
