package noveldownloader

import (
	"net/url"
	"strings"
)

type NovelbinParser struct{}

func NewNovelbinParser() *NovelbinParser {
	return &NovelbinParser{}
}

func (p *NovelbinParser) Name() string {
	return "novelbin"
}

func (p *NovelbinParser) CanHandle(urlStr string) bool {
	u, err := url.Parse(urlStr)
	if err != nil {
		return false
	}
	host := strings.ToLower(u.Host)
	host = strings.TrimPrefix(host, "www.")
	return host == "novelbin.com"
}
