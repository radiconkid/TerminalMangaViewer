.PHONY: help run install lint format clean typecheck

# Show help
help:
	@echo "TerMa - Terminal Manga Viewer"
	@echo ""
	@echo "Usage:"
	@echo "  make run ARGS=\"<path>\"    Run the viewer"
	@echo "  make install              Install dependencies and package"
	@echo "  make lint                 Lint with ruff"
	@echo "  make format               Format with ruff"
	@echo "  make typecheck            Type check with mypy"
	@echo "  make clean                Clean cache files"
	@echo ""
	@echo "Examples:"
	@echo "  make run                  View current directory"
	@echo "  make run ARGS=\"~/manga\"   View specific directory"
	@echo "  make run ARGS=\"archive.cbz\"  View archive file"

# Run the viewer directly (no install needed)
run:
	python3 terma.py $(ARGS)

# Install uv if missing, create venv, install package, and check system dependencies
install:
	command -v uv >/dev/null 2>&1 || { \
		echo "Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}
	uv venv --seed 2>/dev/null || uv venv && uv pip install -e . && { \
		command -v chafa >/dev/null 2>&1 && \
		echo "✓ chafa found"; \
	} || { \
		echo ""; \
		echo "⚠️  chafa is not installed."; \
		echo "   chafa is required for image rendering in most terminals."; \
		echo "   Install it with your package manager:"; \
		echo "     pacman -S chafa        (Arch Linux)"; \
		echo "     apt install chafa      (Debian/Ubuntu)"; \
		echo "     brew install chafa     (macOS)"; \
		echo "     dnf install chafa      (Fedora)"; \
		echo ""; \
	}

# Lint with ruff
lint:
	ruff check terma.py

# Format with ruff
format:
	ruff format terma.py

# Clean cache files
clean:
	rm -rf __pycache__ .pytest_cache dist *.egg-info

# Check types with mypy
typecheck:
	mypy terma.py

