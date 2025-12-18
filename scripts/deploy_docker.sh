#!/bin/bash
# Deploy React app using Docker
# Usage: ./deploy_docker.sh

set -e

echo "🚀 Deploying React app using Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Navigate to React app directory
cd submodules/capital-trades

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "⚠️  .env.production not found. Copying from template..."
    cp .env.production.example .env.production
    echo "✏️  Please edit .env.production with your production values before deploying."
    exit 1
fi

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t politician-trading-frontend .

# Run the container (for testing)
echo "🐳 Running container for testing..."
docker run -d --name politician-trading-test -p 9090:80 politician-trading-frontend

echo "✅ Docker deployment complete!"
echo "🌐 Test your app at http://localhost:9090"
echo "🛑 To stop the test container: docker stop politician-trading-test && docker rm politician-trading-test"
echo ""
echo "📦 For production deployment, push the image to a registry:"
echo "   docker tag politician-trading-frontend your-registry/politician-trading-frontend:latest"
echo "   docker push your-registry/politician-trading-frontend:latest"