#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq

apt-get install -y -qq \
  sslscan \
  dnsrecon \
  fierce \
  nbtscan \
  smbclient \
  onesixtyone \
  hping3 \
  arp-scan \
  wfuzz \
  whatweb \
  wafw00f \
  wapiti \
  dirsearch \
  snmp \
  arjun \
  eyewitness \
  joomscan \
  smbmap \
  ldap-utils \
  golang-go \
  python3-pip \
  massdns \
  wpscan \
  theharvester

pip3 install --break-system-packages --quiet \
  sslyze \
  commix \
  paramspider \
  droopescan \
  trufflehog \
  censys \
  shodan

export GOPATH=/root/go
export PATH=$PATH:/usr/local/go/bin:/root/go/bin

go install github.com/projectdiscovery/katana/cmd/katana@latest
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install github.com/projectdiscovery/uncover/cmd/uncover@latest
go install github.com/lc/gau/v2/cmd/gau@latest
go install github.com/tomnomnom/waybackurls@latest
go install github.com/tomnomnom/httprobe@latest
go install github.com/tomnomnom/unfurl@latest
go install github.com/tomnomnom/assetfinder@latest
go install github.com/jaeles-project/gospider@latest
go install github.com/hakluke/hakrawler@latest
go install github.com/hahwul/dalfox/v2@latest
go install github.com/haccer/subjack@latest
go install github.com/PentestPad/subzy@latest

for bin in /root/go/bin/*; do
  if [ -f "$bin" ]; then
    ln -sf "$bin" /usr/local/bin/
  fi
done

echo "ALL_TOOLS_INSTALLATION_COMPLETE"
