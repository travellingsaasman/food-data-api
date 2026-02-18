module.exports = {
  apps: [{
    name: 'food-data-api',
    script: './venv/bin/uvicorn',
    args: 'api.main:app --host 0.0.0.0 --port 8002',
    cwd: '/home/adminadmin/.openclaw/workspace/projects/food-data-api',
    interpreter: 'none',
    autorestart: true,
    max_restarts: 10,
  }]
}
