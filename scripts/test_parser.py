from app.parsers import ParserRegistry

pr = ParserRegistry()

sample = """Nmap scan report for 192.168.1.1
Host is up (0.0015s latency).
22/tcp   open  ssh     OpenSSH 8.9p1
80/tcp   open  http    Apache httpd 2.4.52
443/tcp  open  https   nginx 1.18.0
3306/tcp closed mysql

Nmap done: 1 IP address (1 host up)"""

result = pr.parse_output(sample, "nmap")
print(f"Hosts: {len(result['hosts'])}")
h = result["hosts"][0]
print(f"IP: {h['ip']}, Ports: {len(h['ports'])}")
for p in h["ports"]:
    print(f"  {p['port']}/{p['protocol']} {p['state']} {p['service']} {p.get('version', '')}")
