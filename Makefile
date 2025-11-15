.PHONY: test benchmark help clean

# Default target
help:
	@echo "🌍 GeospatialHosting Benchmarking Environment"
	@echo "================================================"
	@echo "Available targets:"
	@echo "  test       - Run the test suite using Python unittest"
	@echo "  benchmark  - Run GeoServer benchmarks"
	@echo "  clean      - Clean up temporary files and results"
	@echo "  help       - Show this help message"

# Run tests using Python unittest discovery
test:
	@echo "🧪 Running GeoServer Benchmarker Test Suite"
	@echo "============================================"
	@python -m unittest discover -s gsh_benchmarker/tests -p "test_*.py" -v

# Run benchmarks
benchmark:
	@echo "📊 Running GeoServer Benchmarks"
	@echo "================================"
	@if [ ! -d "gsh_benchmarker" ]; then \
		echo "❌ gsh_benchmarker module not found in current directory"; \
		exit 1; \
	fi
	@python -m gsh_benchmarker.geoserver.gsh_benchmarker $(ARGS)

# Clean up results and temporary files
clean:
	@echo "🧹 Cleaning up temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.pyo" -delete 2>/dev/null || true
	@find . -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed"