#!/usr/bin/env zsh
# @description: Services command
# @version: 1.0.0
# @group: workflows
# @shell: zsh

# services - Services command
#
# This is a shell-based MCLI workflow command with function dispatching.
# Define functions below, then call them via: mcli run services <function> [args...]
# Run without arguments to see available functions.

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# =============================================================================
# Deploy Functions
# =============================================================================

deploy-all() {
    echo "🚀 Deploying all services to Fly.io..."
    deploy-etl
    deploy-server
    deploy-client
    echo "✅ All services deployed!"
}

deploy-etl() {
    echo "🐍 Deploying Python ETL service..."
    cd "$PROJECT_ROOT/python-etl-service"
    fly deploy
    echo "✅ Python ETL deployed: https://politician-trading-etl.fly.dev"
}

deploy-server() {
    echo "🧪 Deploying Elixir server..."
    cd "$PROJECT_ROOT/server"
    fly deploy
    echo "✅ Server deployed: https://politician-trading-server.fly.dev"
}

deploy-client() {
    echo "⚛️  Deploying React client..."
    cd "$PROJECT_ROOT/client"
    fly deploy
    echo "✅ Client deployed: https://govmarket-client.fly.dev"
}

# =============================================================================
# Status Functions
# =============================================================================

status() {
    echo "📊 Fly.io Service Status"
    echo ""
    echo "ETL Service:"
    fly status -a politician-trading-etl 2>/dev/null || echo "  Not deployed or not accessible"
    echo ""
    echo "Server:"
    fly status -a politician-trading-server 2>/dev/null || echo "  Not deployed or not accessible"
    echo ""
    echo "Client:"
    fly status -a govmarket-client 2>/dev/null || echo "  Not deployed or not accessible"
}

logs-etl() {
    echo "📜 Logs for Python ETL service..."
    fly logs -a politician-trading-etl
}

logs-server() {
    echo "📜 Logs for Elixir server..."
    fly logs -a politician-trading-server
}

logs-client() {
    echo "📜 Logs for React client..."
    fly logs -a govmarket-client
}

# =============================================================================
# SSH Functions
# =============================================================================

ssh-etl() {
    echo "🔐 SSH into Python ETL service..."
    fly ssh console -a politician-trading-etl
}

ssh-server() {
    echo "🔐 SSH into Elixir server..."
    fly ssh console -a politician-trading-server
}

ssh-client() {
    echo "🔐 SSH into React client..."
    fly ssh console -a govmarket-client
}

# =============================================================================
# Scale Functions
# =============================================================================

scale() {
    local app="${1:-}"
    local count="${2:-1}"

    if [ -z "$app" ]; then
        echo "Usage: mcli run services scale <etl|server|client> [count]"
        exit 1
    fi

    case "$app" in
        etl)    fly scale count "$count" -a politician-trading-etl ;;
        server) fly scale count "$count" -a politician-trading-server ;;
        client) fly scale count "$count" -a govmarket-client ;;
        *)      echo "Unknown app: $app. Use: etl, server, or client" && exit 1 ;;
    esac
}

# =============================================================================
# Help
# =============================================================================

help() {
    echo "Fly.io Services Management"
    echo ""
    echo "Deploy:"
    echo "  deploy-all     Deploy all services"
    echo "  deploy-etl     Deploy Python ETL service"
    echo "  deploy-server  Deploy Elixir server"
    echo "  deploy-client  Deploy React client"
    echo ""
    echo "Monitor:"
    echo "  status         Show status of all services"
    echo "  logs-etl       Stream ETL logs"
    echo "  logs-server    Stream server logs"
    echo "  logs-client    Stream client logs"
    echo ""
    echo "Access:"
    echo "  ssh-etl        SSH into ETL container"
    echo "  ssh-server     SSH into server container"
    echo "  ssh-client     SSH into client container"
    echo ""
    echo "Scale:"
    echo "  scale <app> [count]  Scale app (etl|server|client)"
}

# =============================================================================
# Function Dispatcher (do not modify below this line)
# =============================================================================

_list_functions() {
    echo "Available functions for 'services':"
    # Works in both bash and zsh - matches alphanumeric, underscore, and hyphen
    typeset -f | grep '^[a-z][a-z0-9_-]* ()' | sed 's/ ().*//' | sort | while read -r fn; do
        echo "  $fn"
    done
}

_main() {
    local cmd="${1:-}"

    if [ -z "$cmd" ]; then
        echo "Usage: mcli run services <function> [args...]"
        echo ""
        _list_functions
        exit 0
    fi

    if declare -f "$cmd" > /dev/null 2>&1; then
        shift
        "$cmd" "$@"
    else
        echo "Error: Unknown function '$cmd'"
        echo ""
        _list_functions
        exit 1
    fi
}

_main "$@"
