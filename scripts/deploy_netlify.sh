#!/bin/bash
# Deploy React app to Netlify
# Usage: ./deploy_netlify.sh

set -e

echo "🚀 Deploying React app to Netlify..."

# Check if Netlify CLI is installed
if ! command -v netlify &> /dev/null; then
    echo "❌ Netlify CLI not found. Install with: npm install -g netlify-cli"
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

# Build the app
echo "🔨 Building the application..."
npm run build

# Deploy to Netlify
echo "📦 Deploying to Netlify..."
netlify deploy --prod --dir=dist

echo "✅ Deployment complete!"
echo "🌐 Check your Netlify dashboard for the deployment URL"