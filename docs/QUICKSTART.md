# Backend Quick Start Guide

## Prerequisites
- Docker & Docker Compose
- Python 3.10+ (for local development)
- PostgreSQL client (`psql`) - optional but helpful

## Setup (5 minutes)

### 1. Clone & Install
```bash
cd music-separation-backend
cp .env.example .env
pip install -r requirements.txt
```

### 2. Start Services
```bash
docker-compose up -d
```

This starts:
- PostgreSQL on port 5432
- Flask API on port 5001
- pgAdmin on port 5050 (optional)

### 3. Verify Setup
```bash
# Check if API is running
curl http://localhost:5001/health

# Expected response:
# {"status": "ok", "timestamp": "...", "version": "1.0.0"}
```

---

## Testing the API

### Register a User
```bash
curl -X POST http://localhost:5001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device-123",
    "app_version": "1.0.0"
  }'

# Save the user_id and session_token from response
export USER_ID="<user_id_from_response>"
export SESSION_TOKEN="<session_token_from_response>"
```

### Upload Audio
```bash
curl -X POST http://localhost:5001/upload \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "X-User-ID: $USER_ID" \
  -F "file=@sample.mp3" \
  -F "metadata={}"

# Save the track_id from response
export TRACK_ID="<track_id_from_response>"
```

### Get Label Suggestions
```bash
curl -X POST http://localhost:5001/extraction/suggest-labels \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"track_id\": \"$TRACK_ID\"}"
```

### Extract Sources
```bash
curl -X POST http://localhost:5001/extraction/extract \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"track_id\": \"$TRACK_ID\",
    \"sources\": [
      {\"label\": \"vocals\", \"model\": \"demucs\"},
      {\"label\": \"drums\", \"model\": \"demucs\"},
      {\"label\": \"bass\", \"model\": \"spleeter\"}
    ]
  }"

# Save the extraction_id from response
export EXTRACTION_ID="<extraction_id_from_response>"
```

### Check Extraction Status
```bash
curl -X GET http://localhost:5001/extraction/$EXTRACTION_ID \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "X-User-ID: $USER_ID"
```

### Submit Feedback
```bash
curl -X POST http://localhost:5001/extraction/$EXTRACTION_ID/feedback \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"segment\": {
      \"start_seconds\": 30,
      \"end_seconds\": 60,
      \"label\": \"vocals\"
    },
    \"feedback_type\": \"good\",
    \"refined_label\": null
  }"
```

### Get User Credits
```bash
curl -X GET http://localhost:5001/user/credits \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "X-User-ID: $USER_ID"
```

### Get User History
```bash
curl -X GET http://localhost:5001/user/history?limit=10 \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "X-User-ID: $USER_ID"
```

---

## Database Access

### Using psql
```bash
psql postgresql://postgres:postgres@localhost:5432/music_separation
```

### Useful Queries
```sql
-- View users
SELECT user_id, subscription_tier, credits_balance FROM users;

-- View recent extractions
SELECT * FROM extractions ORDER BY created_at DESC LIMIT 10;

-- View feedback
SELECT * FROM feedback ORDER BY created_at DESC LIMIT 10;

-- View training data
SELECT * FROM training_data WHERE opt_in = true LIMIT 10;
```

### Using pgAdmin
- URL: http://localhost:5050
- Email: admin@example.com
- Password: admin
- Add Server: host=postgres, user=postgres, password=postgres

---

## Development Workflow

### 1. Make Changes
Edit `app.py`, `services/*.py`, or `models/*.py`

### 2. Restart API
```bash
docker-compose restart api
```

Or if running locally without Docker:
```bash
FLASK_ENV=development flask run
```

### 3. Run Tests
```bash
pytest tests/ -v
```

### 4. Check Logs
```bash
docker-compose logs -f api
```

---

## Common Issues

### Database Connection Refused
```bash
# Make sure postgres is running
docker-compose ps

# If not, start it
docker-compose up -d postgres
```

### Port Already in Use
```bash
# Change port in docker-compose.yml or stop conflicting service
lsof -i :5001  # Find what's using port 5001
```

### Schema Not Applied
```bash
# Manually run schema
docker exec music-separation-db psql -U postgres -d music_separation < schema.sql
```

---

## NLP Testing

### Test Label Parsing
```bash
python -c "
from app import parse_label_to_params, compute_ambiguity_score

# Test parsing
print(parse_label_to_params('lead vocals without reverb'))
# Output: {'source': 'vocal', 'vocal_type': 'lead', ...}

# Test ambiguity
print(compute_ambiguity_score('vocals'))  # 0.1 (clear)
print(compute_ambiguity_score('thing'))   # 0.95 (ambiguous)
"
```

---

## Cloud Deployment (Later)

When ready to deploy to production:

1. Set environment variables (GCP credentials, prod DB URL)
2. Run Terraform:
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

3. CI/CD will handle docker builds & deployments

---

## Next Steps

1. Implement real database queries (replace mocks in app.py)
2. Add Cloud Tasks integration
3. Implement model wrappers (Demucs + Spleeter)
4. Build instrument classifier
5. Add comprehensive tests
6. Deploy to Cloud Run

See `BACKEND_INITIAL_PROMPT.md` for detailed implementation roadmap.

---

## Resources

- [Flask Docs](https://flask.palletsprojects.com/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Google Cloud Tasks](https://cloud.google.com/tasks/docs)
- [Demucs Docs](https://github.com/facebookresearch/demucs)
- [Spleeter Docs](https://github.com/deezer/spleeter)

---

## Questions?

If something doesn't work:
1. Check logs: `docker-compose logs`
2. Verify database: `docker exec music-separation-db psql -U postgres -l`
3. Restart everything: `docker-compose down && docker-compose up -d`
