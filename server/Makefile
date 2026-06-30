BIN    := translator-server
VERSION ?= dev
LDFLAGS := -s -w -X main.Version=$(VERSION)

.PHONY: frontend build android android-armv7 linux-arm64 linux-armv7 compress dev run clean

frontend:
	cd frontend && npm install && npm run build

build: frontend
	CGO_ENABLED=0 go build -trimpath -ldflags="$(LDFLAGS)" -o bin/$(BIN)-linux-amd64-$(VERSION) ./cmd/server

linux-arm64: frontend
	CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -trimpath -ldflags="$(LDFLAGS)" -o bin/$(BIN)-linux-arm64-$(VERSION) ./cmd/server

linux-armv7: frontend
	CGO_ENABLED=0 GOOS=linux GOARCH=arm GOARM=7 go build -trimpath -ldflags="$(LDFLAGS)" -o bin/$(BIN)-linux-armv7-$(VERSION) ./cmd/server

android: frontend
	CGO_ENABLED=0 GOOS=android GOARCH=arm64 go build -trimpath -ldflags="$(LDFLAGS)" -o bin/$(BIN)-android-arm64-$(VERSION) ./cmd/server

android-armv7: frontend
	CGO_ENABLED=0 GOOS=android GOARCH=arm GOARM=7 go build -trimpath -ldflags="$(LDFLAGS)" -o bin/$(BIN)-android-armv7-$(VERSION) ./cmd/server

## all: Compila para todas las plataformas
all: build linux-arm64 linux-armv7 android android-armv7

## compress: Comprime el binario con UPX (máxima compresión)
compress:
	@echo "Comprimiendo binario con UPX..."
	@if command -v upx >/dev/null 2>&1; then \
		upx --best --lzma bin/$(BIN)-*; \
		echo "Compresión completada"; \
		ls -lh bin/; \
	else \
		echo "Error: UPX no está instalado. Instálalo con: apt install upx-ucl o brew install upx"; \
		exit 1; \
	fi

dev:
	@echo "Run in two terminals:"
	@echo "  1) cd frontend && npm run dev"
	@echo "  2) go run ./cmd/server --addr :8080"

run:
	./bin/$(BIN)-linux-amd64-$(VERSION)

clean:
	rm -f bin/$(BIN)-*
