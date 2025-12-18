# Capitol Trades Makefile

.PHONY: dev build preview install clean

# Install dependencies
install:
	npm install

# Start development server
dev:
	npm run dev

# Build for production
build:
	npm run build

# Preview production build locally
preview:
	npm run build && npm run preview

# Clean build artifacts
clean:
	rm -rf dist node_modules/.vite

# Start Python sync UI (requires Python environment)
python-sync:
	cd python && streamlit run streamlit_sync_page.py

# Install Python dependencies
python-install:
	cd python && pip install -r requirements.txt
