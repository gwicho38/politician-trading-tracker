#!/usr/bin/env python3
# @description: Generate comprehensive repository context for LLM consumption
# @version: 1.0.0
# @group: workflows

"""
Repository Context Generator for mcli.

Generates a comprehensive plain text blob containing repository analysis and file contents,
optimized for LLM ingestion. Includes language detection, architecture analysis, schema
extraction, and dependency mapping.

Usage:
    mcli run context generate                           # Full repo context
    mcli run context generate --query "database"        # Filter by keyword
    mcli run context generate --output mycontext.txt    # Custom output file
    mcli run context generate --file-patterns ".py,.ts" # Specific file types
"""

import os
import re
import subprocess
import json
import click
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
from collections import defaultdict
from datetime import datetime

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


# Configuration
DEFAULT_MAX_FILE_SIZE = 1048576  # 1MB
DEFAULT_EXCLUDE_PATTERNS = [
    '.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env',
    '.env', '.DS_Store', '*.pyc', '*.pyo', '*.so', '*.dylib', '*.dll',
    '*.exe', '*.bin', '*.obj', '*.o', '*.a', '*.lib', '*.class',
    '*.jar', '*.war', '*.ear', '*.zip', '*.tar', '*.gz', '*.rar',
    '*.7z', '*.bz2', '*.xz', '*.iso', '*.dmg', '*.pkg', '*.deb',
    '*.rpm', '*.msi', '*.app', '*.whl', '*.egg', '*.egg-info',
    'dist', 'build', 'target', '.next', '.nuxt', '.output',
    'coverage', '.coverage', 'htmlcov', '.pytest_cache', '.mypy_cache',
    '.tox', '.nox', '.hypothesis', '*.log', '*.lock', 'package-lock.json',
    'yarn.lock', 'pnpm-lock.yaml', 'Cargo.lock', 'poetry.lock',
    '*.min.js', '*.min.css', '*.map', '*.chunk.js', '*.chunk.css',
    '*.ico', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg', '*.webp',
    '*.mp3', '*.mp4', '*.wav', '*.avi', '*.mov', '*.webm',
    '*.ttf', '*.otf', '*.woff', '*.woff2', '*.eot',
    '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx', '*.ppt', '*.pptx',
    '*.sqlite', '*.db', '*.sqlite3', '*.mdb',
    '.idea', '.vscode', '*.iml', '.project', '.classpath', '.settings',
    'Thumbs.db', 'desktop.ini', '*.swp', '*.swo', '*~',
]

# Language detection by file extension
LANGUAGE_MAP = {
    '.py': 'Python',
    '.pyx': 'Cython',
    '.pyi': 'Python (Type Stubs)',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript (React)',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript (React)',
    '.mjs': 'JavaScript (ES Module)',
    '.cjs': 'JavaScript (CommonJS)',
    '.vue': 'Vue.js',
    '.svelte': 'Svelte',
    '.rs': 'Rust',
    '.go': 'Go',
    '.java': 'Java',
    '.kt': 'Kotlin',
    '.kts': 'Kotlin Script',
    '.scala': 'Scala',
    '.rb': 'Ruby',
    '.php': 'PHP',
    '.cs': 'C#',
    '.fs': 'F#',
    '.vb': 'Visual Basic',
    '.c': 'C',
    '.h': 'C/C++ Header',
    '.cpp': 'C++',
    '.cc': 'C++',
    '.cxx': 'C++',
    '.hpp': 'C++ Header',
    '.m': 'Objective-C',
    '.mm': 'Objective-C++',
    '.swift': 'Swift',
    '.dart': 'Dart',
    '.ex': 'Elixir',
    '.exs': 'Elixir Script',
    '.erl': 'Erlang',
    '.hrl': 'Erlang Header',
    '.hs': 'Haskell',
    '.lhs': 'Literate Haskell',
    '.ml': 'OCaml',
    '.mli': 'OCaml Interface',
    '.clj': 'Clojure',
    '.cljs': 'ClojureScript',
    '.cljc': 'Clojure (Common)',
    '.lua': 'Lua',
    '.pl': 'Perl',
    '.pm': 'Perl Module',
    '.r': 'R',
    '.R': 'R',
    '.jl': 'Julia',
    '.nim': 'Nim',
    '.zig': 'Zig',
    '.v': 'V / Verilog',
    '.sql': 'SQL',
    '.sh': 'Shell (Bash)',
    '.bash': 'Bash',
    '.zsh': 'Zsh',
    '.fish': 'Fish',
    '.ps1': 'PowerShell',
    '.bat': 'Batch',
    '.cmd': 'Windows Command',
    '.html': 'HTML',
    '.htm': 'HTML',
    '.xhtml': 'XHTML',
    '.css': 'CSS',
    '.scss': 'SCSS',
    '.sass': 'Sass',
    '.less': 'Less',
    '.styl': 'Stylus',
    '.xml': 'XML',
    '.xsl': 'XSLT',
    '.xsd': 'XML Schema',
    '.json': 'JSON',
    '.yaml': 'YAML',
    '.yml': 'YAML',
    '.toml': 'TOML',
    '.ini': 'INI',
    '.cfg': 'Config',
    '.conf': 'Config',
    '.md': 'Markdown',
    '.mdx': 'MDX',
    '.rst': 'reStructuredText',
    '.tex': 'LaTeX',
    '.txt': 'Plain Text',
    '.csv': 'CSV',
    '.tsv': 'TSV',
    '.graphql': 'GraphQL',
    '.gql': 'GraphQL',
    '.proto': 'Protocol Buffers',
    '.thrift': 'Thrift',
    '.avsc': 'Avro Schema',
    '.tf': 'Terraform',
    '.tfvars': 'Terraform Variables',
    '.hcl': 'HCL',
    '.dockerfile': 'Dockerfile',
    '.containerfile': 'Containerfile',
    '.gradle': 'Gradle',
    '.groovy': 'Groovy',
    '.cmake': 'CMake',
    '.make': 'Makefile',
    '.mk': 'Makefile',
    '.prisma': 'Prisma',
    '.sol': 'Solidity',
    '.move': 'Move',
    '.cairo': 'Cairo',
}

# Framework detection patterns
FRAMEWORK_INDICATORS = {
    'package.json': {
        'React': ['react', 'react-dom'],
        'Next.js': ['next'],
        'Vue.js': ['vue'],
        'Nuxt.js': ['nuxt'],
        'Angular': ['@angular/core'],
        'Svelte': ['svelte'],
        'SvelteKit': ['@sveltejs/kit'],
        'Express.js': ['express'],
        'Fastify': ['fastify'],
        'NestJS': ['@nestjs/core'],
        'Electron': ['electron'],
        'React Native': ['react-native'],
        'Remix': ['@remix-run/react'],
        'Astro': ['astro'],
        'Vite': ['vite'],
        'Webpack': ['webpack'],
        'Tailwind CSS': ['tailwindcss'],
        'Material UI': ['@mui/material'],
        'Chakra UI': ['@chakra-ui/react'],
        'Prisma': ['prisma', '@prisma/client'],
        'Drizzle': ['drizzle-orm'],
        'tRPC': ['@trpc/server', '@trpc/client'],
        'Supabase': ['@supabase/supabase-js'],
        'Firebase': ['firebase'],
    },
    'requirements.txt': {
        'Django': ['django'],
        'Flask': ['flask'],
        'FastAPI': ['fastapi'],
        'Starlette': ['starlette'],
        'SQLAlchemy': ['sqlalchemy'],
        'Pydantic': ['pydantic'],
        'Celery': ['celery'],
        'Pandas': ['pandas'],
        'NumPy': ['numpy'],
        'Scikit-learn': ['scikit-learn', 'sklearn'],
        'TensorFlow': ['tensorflow'],
        'PyTorch': ['torch'],
        'Transformers': ['transformers'],
        'LangChain': ['langchain'],
        'OpenAI': ['openai'],
        'Anthropic': ['anthropic'],
        'Supabase': ['supabase'],
        'Pytest': ['pytest'],
        'Black': ['black'],
        'Ruff': ['ruff'],
    },
    'pyproject.toml': {
        'Poetry': ['tool.poetry'],
        'PDM': ['tool.pdm'],
        'Hatch': ['tool.hatch'],
        'Flit': ['tool.flit'],
    },
    'Cargo.toml': {
        'Actix Web': ['actix-web'],
        'Axum': ['axum'],
        'Rocket': ['rocket'],
        'Tokio': ['tokio'],
        'Serde': ['serde'],
        'Diesel': ['diesel'],
        'SQLx': ['sqlx'],
    },
    'go.mod': {
        'Gin': ['github.com/gin-gonic/gin'],
        'Echo': ['github.com/labstack/echo'],
        'Fiber': ['github.com/gofiber/fiber'],
        'Chi': ['github.com/go-chi/chi'],
        'GORM': ['gorm.io/gorm'],
    },
    'mix.exs': {
        'Phoenix': ['phoenix'],
        'Ecto': ['ecto'],
        'Absinthe': ['absinthe'],
        'LiveView': ['phoenix_live_view'],
    },
    'Gemfile': {
        'Rails': ['rails'],
        'Sinatra': ['sinatra'],
        'Hanami': ['hanami'],
        'RSpec': ['rspec'],
    },
}

# Architecture pattern indicators
ARCHITECTURE_PATTERNS = {
    'MVC': ['controllers', 'models', 'views', 'app/controllers', 'app/models', 'app/views'],
    'MVVM': ['viewmodels', 'view-models'],
    'Clean Architecture': ['domain', 'infrastructure', 'application', 'presentation', 'use_cases', 'usecases'],
    'Hexagonal': ['ports', 'adapters', 'core'],
    'Microservices': ['services', 'api-gateway', 'service-mesh'],
    'Monorepo': ['packages', 'apps', 'libs', 'workspaces'],
    'Feature-based': ['features', 'modules'],
    'Component-based': ['components', 'ui', 'shared'],
    'API-first': ['api', 'routes', 'endpoints', 'handlers'],
    'Event-driven': ['events', 'handlers', 'listeners', 'subscribers'],
    'CQRS': ['commands', 'queries', 'read-models', 'write-models'],
    'Repository Pattern': ['repositories', 'repos'],
    'Service Layer': ['services', 'service'],
    'Data Access Layer': ['dal', 'data-access', 'persistence'],
}

# Secrets patterns to redact
SECRETS_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', r'\1=***REDACTED***'),
    (r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', r'\1=***REDACTED***'),
    (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\']{8,})["\']?', r'\1=***REDACTED***'),
    (r'(?i)(token)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', r'\1=***REDACTED***'),
    (r'(?i)(auth[_-]?token|authtoken)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', r'\1=***REDACTED***'),
    (r'(?i)(bearer)\s+([a-zA-Z0-9_\-\.]{20,})', r'\1 ***REDACTED***'),
    (r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[=:]\s*["\']?([A-Z0-9]{16,})["\']?', r'\1=***REDACTED***'),
    (r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[=:]\s*["\']?([a-zA-Z0-9/+=]{30,})["\']?', r'\1=***REDACTED***'),
    (r'(?i)(private[_-]?key)\s*[=:]\s*["\']?([^\s"\']{20,})["\']?', r'\1=***REDACTED***'),
    (r'(sk-[a-zA-Z0-9]{20,})', '***REDACTED_OPENAI_KEY***'),
    (r'(sk-ant-[a-zA-Z0-9\-]{20,})', '***REDACTED_ANTHROPIC_KEY***'),
    (r'(ghp_[a-zA-Z0-9]{20,})', '***REDACTED_GITHUB_TOKEN***'),
    (r'(gho_[a-zA-Z0-9]{20,})', '***REDACTED_GITHUB_TOKEN***'),
    (r'(postgres(?:ql)?://[^:]+:)([^@]+)(@)', r'\1***REDACTED***\3'),
    (r'(mysql://[^:]+:)([^@]+)(@)', r'\1***REDACTED***\3'),
    (r'(mongodb(?:\+srv)?://[^:]+:)([^@]+)(@)', r'\1***REDACTED***\3'),
    (r'(redis://[^:]+:)([^@]+)(@)', r'\1***REDACTED***\3'),
]


def get_repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).parent.parent.parent


def echo(message: str, style: str = None):
    """Print message with optional styling."""
    if HAS_RICH and console and style:
        console.print(message, style=style)
    else:
        click.echo(message)


def redact_secrets(content: str) -> str:
    """Redact sensitive information from content."""
    for pattern, replacement in SECRETS_PATTERNS:
        content = re.sub(pattern, replacement, content)
    return content


def is_binary_file(file_path: Path) -> bool:
    """Check if a file is binary by reading initial bytes."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
            if b'\x00' in chunk:
                return True
            # Check for high ratio of non-text characters
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
            non_text = sum(1 for byte in chunk if byte not in text_chars)
            if len(chunk) > 0 and non_text / len(chunk) > 0.30:
                return True
    except Exception:
        return True
    return False


def should_exclude(path: Path, exclude_patterns: List[str], repo_root: Path) -> bool:
    """Check if a path should be excluded based on patterns."""
    rel_path = str(path.relative_to(repo_root))
    path_parts = path.parts

    for pattern in exclude_patterns:
        pattern = pattern.strip()
        if not pattern:
            continue

        # Direct name match
        if pattern in path_parts:
            return True

        # Glob pattern match
        if '*' in pattern:
            import fnmatch
            if fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return True

        # Path contains pattern
        if pattern in rel_path:
            return True

    return False


def matches_file_patterns(path: Path, file_patterns: List[str]) -> bool:
    """Check if a file matches the specified patterns."""
    if not file_patterns:
        return True

    for pattern in file_patterns:
        pattern = pattern.strip()
        if not pattern:
            continue

        # Extension match (e.g., ".py" or "py")
        if pattern.startswith('.'):
            if path.suffix.lower() == pattern.lower():
                return True
        elif not pattern.startswith('*'):
            if path.suffix.lower() == f'.{pattern.lower()}':
                return True

        # Glob pattern match
        if '*' in pattern:
            import fnmatch
            if fnmatch.fnmatch(path.name, pattern):
                return True

    return False


def get_git_info(repo_path: Path) -> Dict[str, Any]:
    """Get Git repository information."""
    info = {
        'is_git_repo': False,
        'branch': None,
        'remote_url': None,
        'last_commit': None,
        'total_commits': None,
        'contributors': [],
    }

    git_dir = repo_path / '.git'
    if not git_dir.exists():
        return info

    info['is_git_repo'] = True

    try:
        # Current branch
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            info['branch'] = result.stdout.strip()

        # Remote URL
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            info['remote_url'] = result.stdout.strip()

        # Last commit
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%H|%s|%an|%ai'],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|', 3)
            if len(parts) >= 4:
                info['last_commit'] = {
                    'hash': parts[0][:8],
                    'message': parts[1][:100],
                    'author': parts[2],
                    'date': parts[3],
                }

        # Total commits
        result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            info['total_commits'] = int(result.stdout.strip())

        # Top contributors
        result = subprocess.run(
            ['git', 'shortlog', '-sn', '--no-merges', 'HEAD'],
            cwd=repo_path, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n')[:5]:
                if line.strip():
                    parts = line.strip().split('\t', 1)
                    if len(parts) == 2:
                        info['contributors'].append({
                            'commits': int(parts[0].strip()),
                            'name': parts[1].strip()
                        })
    except Exception:
        pass

    return info


def detect_languages(repo_path: Path, files: List[Path]) -> Dict[str, int]:
    """Detect programming languages used in the repository."""
    language_counts = defaultdict(int)

    for file_path in files:
        ext = file_path.suffix.lower()
        if ext in LANGUAGE_MAP:
            language_counts[LANGUAGE_MAP[ext]] += 1

        # Special case for Dockerfile
        if file_path.name.lower() in ('dockerfile', 'containerfile'):
            language_counts['Dockerfile'] += 1
        elif file_path.name.lower() == 'makefile':
            language_counts['Makefile'] += 1

    # Sort by count
    return dict(sorted(language_counts.items(), key=lambda x: -x[1]))


def detect_frameworks(repo_path: Path) -> Dict[str, List[str]]:
    """Detect frameworks and libraries used in the repository.

    Scans both root directory and immediate subdirectories for monorepo support.
    """
    frameworks = defaultdict(set)  # Use set to avoid duplicates

    # Directories to search (root + immediate subdirs for monorepos)
    search_dirs = [repo_path]
    for item in repo_path.iterdir():
        if item.is_dir() and not item.name.startswith('.') and item.name not in ['node_modules', '__pycache__', 'dist', 'build']:
            search_dirs.append(item)

    for search_dir in search_dirs:
        dir_label = '' if search_dir == repo_path else f' ({search_dir.name})'

        for config_file, framework_map in FRAMEWORK_INDICATORS.items():
            config_path = search_dir / config_file
            if not config_path.exists():
                continue

            try:
                content = config_path.read_text(encoding='utf-8', errors='ignore')

                if config_file == 'package.json':
                    try:
                        data = json.loads(content)
                        all_deps = {}
                        for dep_key in ['dependencies', 'devDependencies', 'peerDependencies']:
                            if dep_key in data:
                                all_deps.update(data[dep_key])

                        for framework, indicators in framework_map.items():
                            for indicator in indicators:
                                if indicator in all_deps:
                                    frameworks['JavaScript/TypeScript'].add(framework)
                                    break
                    except json.JSONDecodeError:
                        pass

                elif config_file in ('requirements.txt', 'Gemfile', 'go.mod', 'Cargo.toml'):
                    content_lower = content.lower()
                    category = {
                        'requirements.txt': 'Python',
                        'Gemfile': 'Ruby',
                        'go.mod': 'Go',
                        'Cargo.toml': 'Rust',
                    }[config_file]

                    for framework, indicators in framework_map.items():
                        for indicator in indicators:
                            if indicator.lower() in content_lower:
                                frameworks[category].add(framework)
                                break

                elif config_file == 'pyproject.toml':
                    for framework, indicators in framework_map.items():
                        for indicator in indicators:
                            if indicator in content:
                                frameworks['Python (Build)'].add(framework)
                                break

                elif config_file == 'mix.exs':
                    for framework, indicators in framework_map.items():
                        for indicator in indicators:
                            if f':{indicator}' in content or f'"{indicator}"' in content:
                                frameworks['Elixir'].add(framework)
                                break
            except Exception:
                continue

    # Convert sets to sorted lists
    return {k: sorted(list(v)) for k, v in frameworks.items()}


def detect_architecture(repo_path: Path) -> List[str]:
    """Detect architectural patterns based on directory structure."""
    detected = []

    # Get all directories
    dirs = set()
    for item in repo_path.rglob('*'):
        if item.is_dir() and '.git' not in str(item):
            rel_path = str(item.relative_to(repo_path)).lower()
            dirs.add(rel_path)
            dirs.add(item.name.lower())

    for pattern, indicators in ARCHITECTURE_PATTERNS.items():
        for indicator in indicators:
            if indicator.lower() in dirs:
                detected.append(pattern)
                break

    return list(set(detected))


def extract_database_info(repo_path: Path, files: List[Path]) -> Dict[str, Any]:
    """Extract database-related information."""
    db_info = {
        'types': set(),
        'schemas': [],
        'orm_models': [],
        'migrations': [],
    }

    # Check for database types in config files
    db_indicators = {
        'PostgreSQL': ['postgres', 'postgresql', 'pg_', 'psycopg'],
        'MySQL': ['mysql', 'mariadb'],
        'SQLite': ['sqlite'],
        'MongoDB': ['mongodb', 'mongoose', 'mongo'],
        'Redis': ['redis', 'ioredis'],
        'Supabase': ['supabase'],
        'Firebase': ['firebase', 'firestore'],
        'DynamoDB': ['dynamodb', 'aws-sdk'],
        'Elasticsearch': ['elasticsearch', 'elastic'],
        'Cassandra': ['cassandra'],
    }

    for file_path in files:
        try:
            if file_path.suffix in ['.sql']:
                db_info['types'].add('SQL Database')
                rel_path = str(file_path.relative_to(repo_path))

                # Check if it's a migration
                if 'migration' in rel_path.lower():
                    db_info['migrations'].append(rel_path)
                else:
                    db_info['schemas'].append(rel_path)

            # Check for ORM models
            if file_path.suffix in ['.py', '.ts', '.js', '.rb']:
                content = file_path.read_text(encoding='utf-8', errors='ignore')[:5000]
                content_lower = content.lower()

                # Detect database types
                for db_type, indicators in db_indicators.items():
                    for indicator in indicators:
                        if indicator in content_lower:
                            db_info['types'].add(db_type)
                            break

                # Detect ORM models
                orm_patterns = [
                    (r'class\s+\w+.*\(.*Model\)', 'ORM Model'),
                    (r'class\s+\w+.*\(.*Base\)', 'SQLAlchemy Model'),
                    (r'@Entity', 'TypeORM Entity'),
                    (r'model\s+\w+\s*\{', 'Prisma Model'),
                    (r'schema\s*=.*Schema\(', 'Mongoose Schema'),
                ]

                for pattern, model_type in orm_patterns:
                    if re.search(pattern, content):
                        rel_path = str(file_path.relative_to(repo_path))
                        if rel_path not in [m['path'] for m in db_info['orm_models']]:
                            db_info['orm_models'].append({
                                'path': rel_path,
                                'type': model_type
                            })
                        break

            # Check Prisma schema
            if file_path.name == 'schema.prisma':
                db_info['types'].add('Prisma')
                db_info['schemas'].append(str(file_path.relative_to(repo_path)))

        except Exception:
            continue

    db_info['types'] = list(db_info['types'])
    return db_info


def extract_dependencies(repo_path: Path) -> Dict[str, Any]:
    """Extract dependency information from various package managers."""
    deps = {}

    # package.json (Node.js)
    pkg_json = repo_path / 'package.json'
    if pkg_json.exists():
        try:
            content = json.loads(pkg_json.read_text())
            deps['npm'] = {
                'dependencies': list(content.get('dependencies', {}).keys()),
                'devDependencies': list(content.get('devDependencies', {}).keys()),
            }
        except Exception:
            pass

    # requirements.txt (Python)
    req_txt = repo_path / 'requirements.txt'
    if req_txt.exists():
        try:
            content = req_txt.read_text()
            packages = []
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    pkg = re.split(r'[<>=!~\[]', line)[0].strip()
                    if pkg:
                        packages.append(pkg)
            deps['pip'] = packages
        except Exception:
            pass

    # pyproject.toml (Python)
    pyproject = repo_path / 'pyproject.toml'
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            # Simple extraction for dependencies
            if 'dependencies' in content:
                deps['pyproject'] = 'See pyproject.toml for details'
        except Exception:
            pass

    # Cargo.toml (Rust)
    cargo = repo_path / 'Cargo.toml'
    if cargo.exists():
        try:
            content = cargo.read_text()
            in_deps = False
            packages = []
            for line in content.split('\n'):
                if '[dependencies]' in line or '[dev-dependencies]' in line:
                    in_deps = True
                    continue
                if line.startswith('[') and in_deps:
                    in_deps = False
                if in_deps and '=' in line:
                    pkg = line.split('=')[0].strip()
                    if pkg and not pkg.startswith('#'):
                        packages.append(pkg)
            if packages:
                deps['cargo'] = packages
        except Exception:
            pass

    # go.mod (Go)
    go_mod = repo_path / 'go.mod'
    if go_mod.exists():
        try:
            content = go_mod.read_text()
            packages = []
            for line in content.split('\n'):
                if line.strip().startswith('require'):
                    continue
                if '/' in line and not line.strip().startswith('//'):
                    parts = line.strip().split()
                    if parts:
                        packages.append(parts[0])
            if packages:
                deps['go'] = packages[:20]  # Limit to first 20
        except Exception:
            pass

    # mix.exs (Elixir)
    mix_exs = repo_path / 'mix.exs'
    if mix_exs.exists():
        try:
            content = mix_exs.read_text()
            packages = re.findall(r'\{:(\w+),', content)
            if packages:
                deps['mix'] = list(set(packages))
        except Exception:
            pass

    return deps


def extract_api_routes(repo_path: Path, files: List[Path]) -> Dict[str, List[Dict[str, str]]]:
    """Extract API routes and endpoints from the codebase."""
    routes = defaultdict(list)

    # Patterns for different frameworks
    route_patterns = [
        # FastAPI / Flask / Starlette
        (r'@(app|router|api)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', 'Python'),
        # Express.js / Fastify
        (r'(app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', 'JavaScript'),
        # Phoenix / Elixir
        (r'(get|post|put|delete|patch)\s+["\']([^"\']+)["\']', 'Elixir'),
        # Next.js API routes (from file paths)
        (r'pages/api/|app/api/', 'Next.js'),
    ]

    for file_path in files:
        if file_path.suffix not in ['.py', '.js', '.ts', '.ex', '.exs', '.jsx', '.tsx']:
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = str(file_path.relative_to(repo_path))

            # Check for Next.js API routes
            if 'pages/api/' in rel_path or 'app/api/' in rel_path:
                route_path = rel_path.replace('pages/api/', '/api/').replace('app/api/', '/api/')
                route_path = re.sub(r'\.(js|ts|jsx|tsx)$', '', route_path)
                route_path = re.sub(r'/route$', '', route_path)
                route_path = re.sub(r'/index$', '', route_path)
                route_path = re.sub(r'\[([^\]]+)\]', r':\1', route_path)  # [id] -> :id
                routes['Next.js API'].append({
                    'method': 'HANDLER',
                    'path': route_path,
                    'file': rel_path
                })
                continue

            # Python routes
            if file_path.suffix == '.py':
                for match in re.finditer(r'@(app|router|api|bp)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', content):
                    routes['Python API'].append({
                        'method': match.group(2).upper(),
                        'path': match.group(3),
                        'file': rel_path
                    })

            # JavaScript/TypeScript routes
            elif file_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
                for match in re.finditer(r'\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', content):
                    routes['JavaScript API'].append({
                        'method': match.group(1).upper(),
                        'path': match.group(2),
                        'file': rel_path
                    })

            # Elixir/Phoenix routes
            elif file_path.suffix in ['.ex', '.exs']:
                if 'router' in rel_path.lower() or '_web' in rel_path.lower():
                    for match in re.finditer(r'(get|post|put|delete|patch)\s+["\']([^"\']+)["\']', content):
                        routes['Phoenix API'].append({
                            'method': match.group(1).upper(),
                            'path': match.group(2),
                            'file': rel_path
                        })

        except Exception:
            continue

    return dict(routes)


def extract_entry_points(repo_path: Path) -> Dict[str, List[str]]:
    """Identify main entry points and configuration files."""
    entry_points = {
        'main_files': [],
        'config_files': [],
        'build_files': [],
        'ci_cd': [],
        'docker': [],
    }

    # Main entry point patterns
    main_patterns = [
        'main.py', 'app.py', 'server.py', 'index.py', '__main__.py',
        'main.ts', 'main.js', 'index.ts', 'index.js', 'server.ts', 'server.js',
        'main.go', 'main.rs', 'main.ex', 'application.ex',
        'App.tsx', 'App.jsx', 'App.vue', 'App.svelte',
    ]

    # Config patterns
    config_patterns = [
        'package.json', 'tsconfig.json', 'jsconfig.json',
        'requirements.txt', 'pyproject.toml', 'setup.py', 'setup.cfg',
        'Cargo.toml', 'go.mod', 'mix.exs', 'Gemfile',
        '.env.example', '.env.sample', 'config.yaml', 'config.yml', 'config.json',
        'tailwind.config.js', 'tailwind.config.ts', 'postcss.config.js',
        'vite.config.ts', 'vite.config.js', 'next.config.js', 'next.config.mjs',
        'webpack.config.js', 'rollup.config.js', 'esbuild.config.js',
        '.eslintrc', '.eslintrc.js', '.eslintrc.json', '.prettierrc',
        'jest.config.js', 'vitest.config.ts', 'pytest.ini', 'conftest.py',
    ]

    # Build patterns
    build_patterns = [
        'Makefile', 'Justfile', 'Taskfile.yml',
        'build.sh', 'build.py', 'build.gradle', 'pom.xml',
        'CMakeLists.txt', 'meson.build',
    ]

    # CI/CD patterns
    ci_patterns = [
        '.github/workflows', '.gitlab-ci.yml', '.travis.yml',
        'Jenkinsfile', '.circleci', 'azure-pipelines.yml',
        'bitbucket-pipelines.yml', '.drone.yml',
    ]

    # Docker patterns
    docker_patterns = [
        'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
        'compose.yml', 'compose.yaml', '.dockerignore',
    ]

    for item in repo_path.rglob('*'):
        if not item.is_file():
            continue

        rel_path = str(item.relative_to(repo_path))

        # Skip excluded directories
        if any(excl in rel_path for excl in ['node_modules', '__pycache__', '.git', 'dist', 'build', '.venv', 'venv', 'env/', '.env']):
            continue

        name = item.name

        if name in main_patterns:
            entry_points['main_files'].append(rel_path)
        if name in config_patterns:
            entry_points['config_files'].append(rel_path)
        if name in build_patterns:
            entry_points['build_files'].append(rel_path)
        if name in docker_patterns or 'dockerfile' in name.lower():
            entry_points['docker'].append(rel_path)

        # CI/CD directory check
        for ci in ci_patterns:
            if ci in rel_path:
                if rel_path not in entry_points['ci_cd']:
                    entry_points['ci_cd'].append(rel_path)
                break

    # Sort and limit
    for key in entry_points:
        entry_points[key] = sorted(set(entry_points[key]))[:20]

    return entry_points


def extract_project_info(repo_path: Path) -> Dict[str, Any]:
    """Extract project name, description, and other metadata."""
    info = {
        'name': repo_path.name,
        'description': None,
        'version': None,
        'license': None,
        'readme_summary': None,
    }

    # Try package.json
    pkg_json = repo_path / 'package.json'
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            info['name'] = data.get('name', info['name'])
            info['description'] = data.get('description')
            info['version'] = data.get('version')
            info['license'] = data.get('license')
        except Exception:
            pass

    # Try pyproject.toml
    pyproject = repo_path / 'pyproject.toml'
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if name_match:
                info['name'] = name_match.group(1)
            desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
            if desc_match:
                info['description'] = desc_match.group(1)
            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if version_match:
                info['version'] = version_match.group(1)
        except Exception:
            pass

    # Try mix.exs for Elixir
    mix_exs = repo_path / 'mix.exs'
    if mix_exs.exists():
        try:
            content = mix_exs.read_text()
            app_match = re.search(r'app:\s*:(\w+)', content)
            if app_match:
                info['name'] = app_match.group(1)
            version_match = re.search(r'version:\s*["\']([^"\']+)["\']', content)
            if version_match:
                info['version'] = version_match.group(1)
        except Exception:
            pass

    # Try README for description
    for readme_name in ['README.md', 'README.rst', 'README.txt', 'README']:
        readme_path = repo_path / readme_name
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding='utf-8', errors='ignore')
                # Get first meaningful paragraph (skip badges, titles)
                lines = content.split('\n')
                summary_lines = []
                in_content = False

                for line in lines[:50]:
                    line = line.strip()
                    # Skip badges, images, and headers
                    if line.startswith('![') or line.startswith('[![') or line.startswith('#'):
                        continue
                    if line.startswith('---') or line.startswith('==='):
                        continue
                    if not line:
                        if summary_lines:
                            break
                        continue
                    if len(line) > 20:  # Meaningful content
                        summary_lines.append(line)
                        if len(summary_lines) >= 3:
                            break

                if summary_lines:
                    info['readme_summary'] = ' '.join(summary_lines)[:500]
                break
            except Exception:
                pass

    return info


def extract_test_info(repo_path: Path, files: List[Path]) -> Dict[str, Any]:
    """Extract information about tests in the codebase."""
    test_info = {
        'test_files': [],
        'test_directories': set(),
        'test_frameworks': set(),
        'total_test_files': 0,
    }

    test_patterns = ['test_', '_test.', '.test.', '.spec.', '_spec.']
    test_dirs = ['tests', 'test', '__tests__', 'spec', 'specs']

    for file_path in files:
        rel_path = str(file_path.relative_to(repo_path))
        name = file_path.name.lower()

        # Check if it's a test file
        is_test = any(p in name for p in test_patterns)
        in_test_dir = any(f'/{d}/' in f'/{rel_path}' or rel_path.startswith(f'{d}/') for d in test_dirs)

        if is_test or in_test_dir:
            test_info['test_files'].append(rel_path)

            # Track test directories
            for d in test_dirs:
                if f'/{d}/' in f'/{rel_path}' or rel_path.startswith(f'{d}/'):
                    test_info['test_directories'].add(d)

            # Detect test framework
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')[:2000]
                if 'pytest' in content or 'import pytest' in content:
                    test_info['test_frameworks'].add('pytest')
                if 'unittest' in content:
                    test_info['test_frameworks'].add('unittest')
                if 'jest' in content or "from 'jest'" in content:
                    test_info['test_frameworks'].add('Jest')
                if 'vitest' in content:
                    test_info['test_frameworks'].add('Vitest')
                if 'mocha' in content or 'describe(' in content:
                    test_info['test_frameworks'].add('Mocha')
                if 'ExUnit' in content:
                    test_info['test_frameworks'].add('ExUnit')
                if '@Test' in content or 'JUnit' in content:
                    test_info['test_frameworks'].add('JUnit')
            except Exception:
                pass

    test_info['total_test_files'] = len(test_info['test_files'])
    test_info['test_files'] = test_info['test_files'][:20]  # Limit for display
    test_info['test_directories'] = list(test_info['test_directories'])
    test_info['test_frameworks'] = list(test_info['test_frameworks'])

    return test_info


def get_directory_tree(repo_path: Path, max_depth: int = 4, exclude_patterns: List[str] = None) -> str:
    """Generate a directory tree representation."""
    exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS

    def should_skip(path: Path) -> bool:
        name = path.name
        if name.startswith('.') and name != '.':
            return True
        for pattern in exclude_patterns:
            if pattern in str(path) or pattern == name:
                return True
        return False

    def build_tree(dir_path: Path, prefix: str = '', depth: int = 0) -> List[str]:
        if depth > max_depth:
            return ['    ' * depth + '...']

        lines = []
        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            items = [i for i in items if not should_skip(i)]

            for i, item in enumerate(items[:50]):  # Limit items per directory
                is_last = i == len(items) - 1 or i == 49
                connector = '└── ' if is_last else '├── '

                if item.is_dir():
                    lines.append(f'{prefix}{connector}{item.name}/')
                    extension = '    ' if is_last else '│   '
                    lines.extend(build_tree(item, prefix + extension, depth + 1))
                else:
                    lines.append(f'{prefix}{connector}{item.name}')

            if len(items) > 50:
                lines.append(f'{prefix}    ... and {len(items) - 50} more items')
        except PermissionError:
            lines.append(f'{prefix}[Permission denied]')

        return lines

    tree_lines = [f'{repo_path.name}/']
    tree_lines.extend(build_tree(repo_path))
    return '\n'.join(tree_lines)


def get_env_example(repo_path: Path) -> Optional[str]:
    """Get environment variable examples (redacted)."""
    env_files = ['.env.example', '.env.sample', '.env.template', 'env.example']

    for env_file in env_files:
        env_path = repo_path / env_file
        if env_path.exists():
            try:
                content = env_path.read_text(encoding='utf-8', errors='ignore')
                return redact_secrets(content)
            except Exception:
                pass

    return None


def collect_files(repo_path: Path, file_patterns: List[str], exclude_patterns: List[str]) -> List[Path]:
    """Collect all relevant files from the repository."""
    files = []

    for file_path in repo_path.rglob('*'):
        if not file_path.is_file():
            continue

        if should_exclude(file_path, exclude_patterns, repo_path):
            continue

        if not matches_file_patterns(file_path, file_patterns):
            continue

        if is_binary_file(file_path):
            continue

        files.append(file_path)

    return sorted(files, key=lambda x: str(x.relative_to(repo_path)))


def filter_by_query(files: List[Path], query: str, repo_path: Path) -> List[Tuple[Path, List[str]]]:
    """Filter files by query and return matching files with relevant lines."""
    if not query:
        return [(f, []) for f in files]

    query_lower = query.lower()
    query_pattern = re.compile(re.escape(query), re.IGNORECASE)
    results = []

    for file_path in files:
        try:
            # Check filename first
            if query_lower in str(file_path.relative_to(repo_path)).lower():
                results.append((file_path, []))
                continue

            # Check content
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if query_pattern.search(content):
                # Extract matching lines
                matching_lines = []
                for i, line in enumerate(content.split('\n'), 1):
                    if query_pattern.search(line):
                        matching_lines.append(f'L{i}: {line.strip()[:200]}')
                        if len(matching_lines) >= 10:
                            break
                results.append((file_path, matching_lines))
        except Exception:
            continue

    return results


def generate_context_blob(
    repo_path: Path,
    branch: Optional[str] = None,
    file_patterns: List[str] = None,
    exclude_patterns: List[str] = None,
    query: Optional[str] = None,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    include_file_contents: bool = True,
) -> str:
    """Generate the comprehensive context blob."""

    exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS
    file_patterns = file_patterns or []

    sections = []

    # Header
    sections.append('=' * 80)
    sections.append('REPOSITORY CONTEXT ANALYSIS')
    sections.append(f'Generated: {datetime.now().isoformat()}')
    sections.append(f'Repository: {repo_path.name}')
    if query:
        sections.append(f'Query Filter: {query}')
    sections.append('=' * 80)
    sections.append('')

    # Project Information
    project_info = extract_project_info(repo_path)
    sections.append('### PROJECT OVERVIEW')
    sections.append(f'  Name: {project_info["name"]}')
    if project_info['description']:
        sections.append(f'  Description: {project_info["description"]}')
    if project_info['version']:
        sections.append(f'  Version: {project_info["version"]}')
    if project_info['license']:
        sections.append(f'  License: {project_info["license"]}')
    if project_info['readme_summary']:
        sections.append(f'  Summary: {project_info["readme_summary"]}')
    sections.append('')

    # Git Information
    git_info = get_git_info(repo_path)
    if git_info['is_git_repo']:
        sections.append('### GIT INFORMATION')
        sections.append(f'Branch: {git_info["branch"]}')
        if git_info['remote_url']:
            sections.append(f'Remote: {git_info["remote_url"]}')
        if git_info['total_commits']:
            sections.append(f'Total Commits: {git_info["total_commits"]}')
        if git_info['last_commit']:
            lc = git_info['last_commit']
            sections.append(f'Last Commit: {lc["hash"]} - {lc["message"]}')
            sections.append(f'  Author: {lc["author"]} ({lc["date"]})')
        if git_info['contributors']:
            sections.append('Top Contributors:')
            for c in git_info['contributors']:
                sections.append(f'  - {c["name"]}: {c["commits"]} commits')
        sections.append('')

    # Collect files
    files = collect_files(repo_path, file_patterns, exclude_patterns)
    sections.append(f'### FILE STATISTICS')
    sections.append(f'  Total text files analyzed: {len(files)}')
    sections.append('')

    # Language Detection
    sections.append('### LANGUAGES AND TECH STACK')
    languages = detect_languages(repo_path, files)
    if languages:
        total_files = sum(languages.values())
        for lang, count in list(languages.items())[:15]:
            pct = (count / total_files) * 100
            sections.append(f'  {lang}: {count} files ({pct:.1f}%)')
    else:
        sections.append('  No programming languages detected')
    sections.append('')

    # Framework Detection
    sections.append('### FRAMEWORKS AND LIBRARIES')
    frameworks = detect_frameworks(repo_path)
    if frameworks:
        for category, fw_list in frameworks.items():
            sections.append(f'  {category}: {", ".join(fw_list)}')
    else:
        sections.append('  No frameworks detected')
    sections.append('')

    # Architecture Detection
    sections.append('### ARCHITECTURE PATTERNS')
    arch_patterns = detect_architecture(repo_path)
    if arch_patterns:
        for pattern in arch_patterns:
            sections.append(f'  - {pattern}')
    else:
        sections.append('  No specific architecture patterns detected')
    sections.append('')

    # Database Information
    sections.append('### DATABASE AND STORAGE')
    db_info = extract_database_info(repo_path, files)
    if db_info['types']:
        sections.append(f'  Database Types: {", ".join(db_info["types"])}')
    if db_info['schemas']:
        sections.append(f'  Schema Files: {len(db_info["schemas"])}')
        for schema in db_info['schemas'][:5]:
            sections.append(f'    - {schema}')
    if db_info['orm_models']:
        sections.append(f'  ORM Models: {len(db_info["orm_models"])}')
        for model in db_info['orm_models'][:5]:
            sections.append(f'    - {model["path"]} ({model["type"]})')
    if db_info['migrations']:
        sections.append(f'  Migrations: {len(db_info["migrations"])}')
    if not any([db_info['types'], db_info['schemas'], db_info['orm_models']]):
        sections.append('  No database information detected')
    sections.append('')

    # Dependencies
    sections.append('### DEPENDENCIES')
    deps = extract_dependencies(repo_path)
    if deps:
        for pkg_mgr, packages in deps.items():
            if isinstance(packages, dict):
                for dep_type, pkg_list in packages.items():
                    if pkg_list:
                        sections.append(f'  {pkg_mgr} ({dep_type}): {len(pkg_list)} packages')
                        sections.append(f'    {", ".join(pkg_list[:10])}{"..." if len(pkg_list) > 10 else ""}')
            elif isinstance(packages, list):
                sections.append(f'  {pkg_mgr}: {len(packages)} packages')
                sections.append(f'    {", ".join(packages[:10])}{"..." if len(packages) > 10 else ""}')
            else:
                sections.append(f'  {pkg_mgr}: {packages}')
    else:
        sections.append('  No dependency files found')
    sections.append('')

    # Entry Points and Configuration
    sections.append('### ENTRY POINTS AND CONFIGURATION')
    entry_points = extract_entry_points(repo_path)
    if entry_points['main_files']:
        sections.append('  Main Entry Points:')
        for f in entry_points['main_files'][:10]:
            sections.append(f'    - {f}')
    if entry_points['config_files']:
        sections.append('  Configuration Files:')
        for f in entry_points['config_files'][:10]:
            sections.append(f'    - {f}')
    if entry_points['build_files']:
        sections.append('  Build Files:')
        for f in entry_points['build_files'][:5]:
            sections.append(f'    - {f}')
    if entry_points['docker']:
        sections.append('  Docker/Container Files:')
        for f in entry_points['docker'][:5]:
            sections.append(f'    - {f}')
    if entry_points['ci_cd']:
        sections.append('  CI/CD Configuration:')
        for f in entry_points['ci_cd'][:5]:
            sections.append(f'    - {f}')
    sections.append('')

    # API Routes
    sections.append('### API ROUTES AND ENDPOINTS')
    api_routes = extract_api_routes(repo_path, files)
    if api_routes:
        for category, routes in api_routes.items():
            sections.append(f'  {category}:')
            for route in routes[:15]:
                sections.append(f'    {route["method"]:6} {route["path"]}  ({route["file"]})')
            if len(routes) > 15:
                sections.append(f'    ... and {len(routes) - 15} more routes')
    else:
        sections.append('  No API routes detected')
    sections.append('')

    # Test Information
    sections.append('### TESTING')
    test_info = extract_test_info(repo_path, files)
    sections.append(f'  Total Test Files: {test_info["total_test_files"]}')
    if test_info['test_frameworks']:
        sections.append(f'  Test Frameworks: {", ".join(test_info["test_frameworks"])}')
    if test_info['test_directories']:
        sections.append(f'  Test Directories: {", ".join(test_info["test_directories"])}')
    if test_info['test_files']:
        sections.append('  Sample Test Files:')
        for f in test_info['test_files'][:10]:
            sections.append(f'    - {f}')
    sections.append('')

    # Environment Example
    env_example = get_env_example(repo_path)
    if env_example:
        sections.append('### ENVIRONMENT VARIABLES (from example file)')
        sections.append(env_example[:2000])
        if len(env_example) > 2000:
            sections.append('... (truncated)')
        sections.append('')

    # Directory Structure
    sections.append('### DIRECTORY STRUCTURE')
    tree = get_directory_tree(repo_path, max_depth=3, exclude_patterns=exclude_patterns)
    sections.append(tree)
    sections.append('')

    # File Contents
    if include_file_contents:
        sections.append('=' * 80)
        sections.append('FILE CONTENTS')
        sections.append('=' * 80)
        sections.append('')

        # Filter by query if provided
        if query:
            filtered_files = filter_by_query(files, query, repo_path)
            echo(f'Found {len(filtered_files)} files matching query "{query}"')
        else:
            filtered_files = [(f, []) for f in files]

        for file_path, matching_lines in filtered_files:
            rel_path = file_path.relative_to(repo_path)

            try:
                file_size = file_path.stat().st_size

                sections.append(f'### File: {rel_path}')

                if file_size > max_file_size:
                    sections.append(f'[WARNING: File size ({file_size} bytes) exceeds limit. Showing first {max_file_size} bytes]')
                    content = file_path.read_text(encoding='utf-8', errors='ignore')[:max_file_size]
                    content += '\n... [TRUNCATED]'
                else:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Redact secrets
                content = redact_secrets(content)

                # Show matching lines if query was used
                if matching_lines:
                    sections.append('Matching lines:')
                    for line in matching_lines:
                        sections.append(f'  {line}')
                    sections.append('')

                sections.append('Content:')
                sections.append(content)
                sections.append('')
                sections.append('-' * 40)
                sections.append('')

            except Exception as e:
                sections.append(f'### File: {rel_path}')
                sections.append(f'[ERROR: Could not read file: {e}]')
                sections.append('')

    # Footer
    sections.append('=' * 80)
    sections.append(f'END OF CONTEXT - Total files analyzed: {len(files)}')
    sections.append('=' * 80)

    return '\n'.join(sections)


# Click command group
@click.group(name='context')
def context():
    """Repository context generation commands."""
    pass


@context.command(name='generate')
@click.option('--repo-path', '-r', type=click.Path(exists=True, path_type=Path),
              default=None, help='Path to repository (default: current repo)')
@click.option('--branch', '-b', default=None, help='Branch to analyze (default: current)')
@click.option('--file-patterns', '-f', default='',
              help='Comma-separated file patterns to include (e.g., ".py,.ts,.md")')
@click.option('--exclude-patterns', '-e', default='',
              help='Comma-separated patterns to exclude (e.g., "tests/,.log")')
@click.option('--query', '-q', default=None,
              help='Search query to filter relevant files/content')
@click.option('--output', '-o', 'output_file', type=click.Path(path_type=Path),
              default=None, help='Output file path (default: stdout)')
@click.option('--max-file-size', '-m', type=int, default=DEFAULT_MAX_FILE_SIZE,
              help=f'Max file size in bytes (default: {DEFAULT_MAX_FILE_SIZE})')
@click.option('--no-contents', is_flag=True, default=False,
              help='Skip file contents, only show analysis')
@click.option('--tree-only', is_flag=True, default=False,
              help='Only show directory tree')
def generate(
    repo_path: Optional[Path],
    branch: Optional[str],
    file_patterns: str,
    exclude_patterns: str,
    query: Optional[str],
    output_file: Optional[Path],
    max_file_size: int,
    no_contents: bool,
    tree_only: bool,
):
    """
    Generate comprehensive repository context for LLM consumption.

    Examples:

        mcli run context generate

        mcli run context generate --query "database"

        mcli run context generate -f ".py,.ts" -o context.txt

        mcli run context generate --tree-only
    """
    # Default to current repo
    if repo_path is None:
        repo_path = get_repo_root()

    repo_path = repo_path.resolve()

    if not repo_path.exists():
        click.echo(f'Error: Repository path does not exist: {repo_path}', err=True)
        raise SystemExit(1)

    # Parse patterns
    file_pattern_list = [p.strip() for p in file_patterns.split(',') if p.strip()]
    exclude_pattern_list = DEFAULT_EXCLUDE_PATTERNS.copy()
    if exclude_patterns:
        exclude_pattern_list.extend([p.strip() for p in exclude_patterns.split(',') if p.strip()])

    echo(f'Analyzing repository: {repo_path}', style='bold blue')

    if tree_only:
        tree = get_directory_tree(repo_path, max_depth=4, exclude_patterns=exclude_pattern_list)
        if output_file:
            output_file.write_text(tree)
            echo(f'Directory tree saved to {output_file}', style='green')
        else:
            click.echo(tree)
        return

    # Generate context
    if HAS_RICH:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Generating context...", total=None)
            blob = generate_context_blob(
                repo_path=repo_path,
                branch=branch,
                file_patterns=file_pattern_list,
                exclude_patterns=exclude_pattern_list,
                query=query,
                max_file_size=max_file_size,
                include_file_contents=not no_contents,
            )
    else:
        echo('Generating context...')
        blob = generate_context_blob(
            repo_path=repo_path,
            branch=branch,
            file_patterns=file_pattern_list,
            exclude_patterns=exclude_pattern_list,
            query=query,
            max_file_size=max_file_size,
            include_file_contents=not no_contents,
        )

    # Output
    if output_file:
        output_file.write_text(blob)
        file_size = output_file.stat().st_size
        echo(f'Context saved to {output_file} ({file_size:,} bytes)', style='green')
    else:
        click.echo(blob)


@context.command(name='summary')
@click.option('--repo-path', '-r', type=click.Path(exists=True, path_type=Path),
              default=None, help='Path to repository (default: current repo)')
def summary(repo_path: Optional[Path]):
    """
    Show a quick summary of the repository.

    Example:
        mcli run context summary
    """
    if repo_path is None:
        repo_path = get_repo_root()

    repo_path = repo_path.resolve()

    echo(f'\n📁 Repository: {repo_path.name}', style='bold')
    echo('=' * 50)

    # Git info
    git_info = get_git_info(repo_path)
    if git_info['is_git_repo']:
        echo(f'\n🔀 Branch: {git_info["branch"]}')
        if git_info['total_commits']:
            echo(f'   Commits: {git_info["total_commits"]}')

    # Quick file scan
    files = collect_files(repo_path, [], DEFAULT_EXCLUDE_PATTERNS)
    echo(f'\n📄 Files: {len(files)} text files')

    # Languages
    languages = detect_languages(repo_path, files)
    if languages:
        top_langs = list(languages.items())[:5]
        echo(f'\n💻 Languages: {", ".join(f"{l} ({c})" for l, c in top_langs)}')

    # Frameworks
    frameworks = detect_frameworks(repo_path)
    if frameworks:
        all_fw = []
        for fw_list in frameworks.values():
            all_fw.extend(fw_list)
        echo(f'\n🛠️  Frameworks: {", ".join(all_fw[:10])}')

    # Architecture
    arch = detect_architecture(repo_path)
    if arch:
        echo(f'\n🏗️  Architecture: {", ".join(arch)}')

    # Database
    db_info = extract_database_info(repo_path, files)
    if db_info['types']:
        echo(f'\n🗄️  Databases: {", ".join(db_info["types"])}')

    echo('\n' + '=' * 50)
    echo('Run "mcli run context generate" for full context', style='dim')


# Legacy single command for backwards compatibility
@click.command(name='context_legacy')
@click.argument('name', default='World')
def context_command(name: str):
    """Legacy context command (use 'context generate' instead)."""
    echo(f'Hello, {name}! Use "mcli run context generate" for full functionality.')


if __name__ == '__main__':
    context()
