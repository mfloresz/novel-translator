package store

import (
	"fmt"
	"strings"

	"github.com/pocketbase/pocketbase/core"
)

type AuthResult struct {
	Token string `json:"token"`
	User  User   `json:"user"`
}

func (s *Store) CreateUser(email, password, name string) (*AuthResult, error) {
	users, err := s.App.FindCollectionByNameOrId(UsersCollection)
	if err != nil {
		return nil, err
	}
	record := core.NewRecord(users)
	record.SetEmail(strings.TrimSpace(email))
	record.SetPassword(password)
	record.SetVerified(true)
	record.Set("name", strings.TrimSpace(name))
	record.Set("theme", "system")
	record.Set("active_provider", DefaultAISettings.Provider)
	if err := s.App.Save(record); err != nil {
		return nil, err
	}
	token, err := record.NewAuthToken()
	if err != nil {
		return nil, err
	}
	return &AuthResult{Token: token, User: userFromRecord(record)}, nil
}

func (s *Store) AuthenticateUser(email, password string) (*AuthResult, error) {
	record, err := s.App.FindAuthRecordByEmail(UsersCollection, strings.TrimSpace(email))
	if err != nil || record == nil || !record.ValidatePassword(password) {
		return nil, fmt.Errorf("invalid credentials")
	}
	token, err := record.NewAuthToken()
	if err != nil {
		return nil, err
	}
	return &AuthResult{Token: token, User: userFromRecord(record)}, nil
}

func (s *Store) RefreshAuth(token string) (*AuthResult, error) {
	record, err := s.App.FindAuthRecordByToken(token, core.TokenTypeAuth)
	if err != nil {
		return nil, err
	}
	newToken, err := record.NewAuthToken()
	if err != nil {
		return nil, err
	}
	return &AuthResult{Token: newToken, User: userFromRecord(record)}, nil
}

func (s *Store) FindAuthRecord(token string) (*core.Record, error) {
	return s.App.FindAuthRecordByToken(token, core.TokenTypeAuth)
}
