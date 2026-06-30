BIN := translator-server

.PHONY: frontend build android compress dev run clean

frontend:
	cd frontend && npm install && npm run build

build: frontend
	CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o bin/$(BIN) ./cmd/server

## android: Compila binario para Android ARM64 (Termux)
android: frontend
	CGO_ENABLED=0 GOOS=android GOARCH=arm64 go build -trimpath -ldflags="-s -w" -o bin/$(BIN)-android-arm64 ./cmd/server

## compress: Comprime el binario con UPX (máxima compresión)
compress:
	@echo "Comprimiendo binario con UPX..."
	@if command -v upx >/dev/null 2>&1; then \
		upx --best --lzma bin/$(BIN); \
		echo "Compresión completada"; \
		ls -lh bin/$(BIN); \
	else \
		echo "Error: UPX no está instalado. Instálalo con: apt install upx-ucl o brew install upx"; \
		exit 1; \
	fi

dev:
	@echo "Run in two terminals:"
	@echo "  1) cd frontend && npm run dev"
	@echo "  2) go run ./cmd/server --addr :8080"

run:
	./bin/$(BIN)

clean:
	rm -f bin/$(BIN)
