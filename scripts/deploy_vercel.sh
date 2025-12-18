#!/bin/bash
# Deploy React app to Vercel
# Usage: ./deploy_vercel.sh

set -e

echo "🚀 Deploying React app to Vercel..."

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Install with: npm install -g vercel"
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

# Deploy to Vercel
echo "📦 Deploying to Vercel..."
vercel --prod

echo "✅ Deployment complete!"
echo "🌐 Check your Vercel dashboard for the deployment URL"