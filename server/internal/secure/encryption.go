package secure

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const cipherVersion = "v1"

type Encryptor struct {
	key []byte
}

func NewEncryptorFromConfig(envValue, keyPath string) (*Encryptor, error) {
	key, err := resolveKey(envValue, keyPath)
	if err != nil {
		return nil, err
	}
	return &Encryptor{key: key}, nil
}

func (e *Encryptor) Encrypt(plain string) (string, error) {
	if strings.TrimSpace(plain) == "" {
		return "", nil
	}
	block, err := aes.NewCipher(e.key)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return "", err
	}
	ciphertext := gcm.Seal(nil, nonce, []byte(plain), nil)
	payload := append(nonce, ciphertext...)
	return cipherVersion + ":" + base64.StdEncoding.EncodeToString(payload), nil
}

func (e *Encryptor) Decrypt(encoded string) (string, error) {
	if strings.TrimSpace(encoded) == "" {
		return "", nil
	}
	parts := strings.SplitN(encoded, ":", 2)
	if len(parts) != 2 || parts[0] != cipherVersion {
		return "", fmt.Errorf("unsupported cipher version")
	}
	payload, err := base64.StdEncoding.DecodeString(parts[1])
	if err != nil {
		return "", err
	}
	block, err := aes.NewCipher(e.key)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	nonceSize := gcm.NonceSize()
	if len(payload) < nonceSize {
		return "", fmt.Errorf("invalid encrypted payload")
	}
	nonce := payload[:nonceSize]
	ciphertext := payload[nonceSize:]
	plain, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", err
	}
	return string(plain), nil
}

func resolveKey(envValue, keyPath string) ([]byte, error) {
	if envValue != "" {
		key, err := decodeKey(envValue)
		if err != nil {
			return nil, fmt.Errorf("decode APP_ENCRYPTION_KEY: %w", err)
		}
		if len(key) != 32 {
			return nil, fmt.Errorf("APP_ENCRYPTION_KEY must resolve to 32 bytes")
		}
		return key, nil
	}
	if err := os.MkdirAll(filepath.Dir(keyPath), 0o755); err != nil {
		return nil, fmt.Errorf("create key dir: %w", err)
	}
	if content, err := os.ReadFile(keyPath); err == nil {
		key, err := decodeKey(strings.TrimSpace(string(content)))
		if err != nil {
			return nil, fmt.Errorf("decode local app key: %w", err)
		}
		if len(key) != 32 {
			return nil, fmt.Errorf("local app key must resolve to 32 bytes")
		}
		return key, nil
	}
	key := make([]byte, 32)
	if _, err := rand.Read(key); err != nil {
		return nil, fmt.Errorf("generate app key: %w", err)
	}
	encoded := base64.StdEncoding.EncodeToString(key)
	if err := os.WriteFile(keyPath, []byte(encoded), 0o600); err != nil {
		return nil, fmt.Errorf("write app key: %w", err)
	}
	return key, nil
}

func decodeKey(value string) ([]byte, error) {
	if value == "" {
		return nil, fmt.Errorf("empty key")
	}
	if raw, err := base64.StdEncoding.DecodeString(value); err == nil {
		return raw, nil
	}
	if raw, err := hex.DecodeString(value); err == nil {
		return raw, nil
	}
	return nil, fmt.Errorf("expected base64 or hex encoded key")
}
