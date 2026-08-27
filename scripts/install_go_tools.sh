#!/bin/bash
export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin

go install github.com/projectdiscovery/katana/cmd/katana@latest 2>&1
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest 2>&1
go install github.com/projectdiscovery/uncover/cmd/uncover@latest 2>&1
go install github.com/lc/gau/v2/cmd/gau@latest 2>&1
go install github.com/tomnomnom/waybackurls@latest 2>&1
go install github.com/tomnomnom/httprobe@latest 2>&1
go install github.com/tomnomnom/unfurl@latest 2>&1
go install github.com/tomnomnom/assetfinder@latest 2>&1
go install github.com/jaeles-project/gospider@latest 2>&1
go install github.com/hakluke/hakrawler@latest 2>&1
go install github.com/hahwul/dalfox/v2@latest 2>&1
go install github.com/haccer/subjack@latest 2>&1
go install github.com/PentestPad/subzy@latest 2>&1
echo GO_TOOLS_DONE
