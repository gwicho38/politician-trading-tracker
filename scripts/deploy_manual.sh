#!/bin/bash
# Manual deployment script for React app
# Usage: ./deploy_manual.sh

set -e

echo "🚀 Manual deployment of React app..."

# Navigate to React app directory
cd submodules/capital-trades

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "⚠️  .env.production not found. Copying from template..."
    cp .env.production.example .env.production
    echo "✏️  Please edit .env.production with your production values before deploying."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build the app
echo "🔨 Building the application..."
npm run build

# Check if build succeeded
if [ ! -d "dist" ]; then
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

echo "✅ Build complete!"
echo ""
echo "📁 Build output is in: submodules/capital-trades/dist/"
echo ""
echo "🌐 To serve the app, you can:"
echo "   - Upload the 'dist' folder to any static hosting service"
echo "   - Use a web server like nginx or Apache to serve the files"
echo "   - Use 'npx serve dist' for local testing"
echo ""
echo "🔧 Example nginx configuration:"
echo "   server {"
echo "       listen 80;"
echo "       root /path/to/dist;"
echo "       index index.html;"
echo "       location / {"
echo "           try_files \$uri \$uri/ /index.html;"
echo "       }"
echo "   }"