package noveldownloader

import (
	"net/url"
	"strings"
)

type NovelfireParser struct{}

func NewNovelfireParser() *NovelfireParser {
	return &NovelfireParser{}
}

func (p *NovelfireParser) Name() string {
	return "novelfire"
}

func (p *NovelfireParser) CanHandle(urlStr string) bool {
	u, err := url.Parse(urlStr)
	if err != nil {
		return false
	}
	host := strings.ToLower(u.Host)
	host = strings.TrimPrefix(host, "www.")
	return host == "novelfire.net"
}
