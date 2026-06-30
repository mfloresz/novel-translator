package noveldownloader

import (
	"net/url"
	"strings"
)

type FenrirRealmParser struct{}

func NewFenrirRealmParser() *FenrirRealmParser {
	return &FenrirRealmParser{}
}

func (p *FenrirRealmParser) Name() string {
	return "fenrirealm"
}

func (p *FenrirRealmParser) CanHandle(urlStr string) bool {
	u, err := url.Parse(urlStr)
	if err != nil {
		return false
	}
	host := strings.ToLower(u.Host)
	host = strings.TrimPrefix(host, "www.")
	return host == "fenrirealm.com"
}
