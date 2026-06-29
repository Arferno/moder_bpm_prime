#!/bin/bash
# Deploy script for Oracle Cloud VPS
# Usage: ./scripts/deploy.sh

set -e

VPS_HOST="ubuntu@your-vps-ip"  # Change this to your VPS IP
VPS_PATH="/opt/moder_bpm_prime"
REPO_URL="https://github.com/yourusername/moder_bpm_prime.git"  # Change this

echo "🚀 Starting deployment..."

# If running locally, deploy to VPS
if [ "$1" == "remote" ]; then
    echo "📦 Deploying to VPS..."
    ssh $VPS_HOST << EOF
        cd $VPS_PATH
        git pull origin main
        docker compose -f docker-compose.prod.yml down
        docker compose -f docker-compose.prod.yml up -d --build
        docker system prune -f
        echo "✅ Deployment complete!"
EOF
else
    # Local deployment
    echo "📦 Building and starting locally..."
    docker compose -f docker-compose.prod.yml down
    docker compose -f docker-compose.prod.yml up -d --build
    docker system prune -f
    echo "✅ Local deployment complete!"
fi