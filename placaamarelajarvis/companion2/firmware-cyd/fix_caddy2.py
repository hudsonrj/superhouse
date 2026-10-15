from pathlib import Path

p = Path("/etc/caddy/Caddyfile")
t = p.read_text()
start = t.find("control.ch8ai.com.br {")
if start < 0:
    raise SystemExit("no block")
# find matching closing brace of this site
i = start + len("control.ch8ai.com.br {")
depth = 1
while i < len(t) and depth:
    if t[i] == "{":
        depth += 1
    elif t[i] == "}":
        depth -= 1
    i += 1
end = i
block = t[start:end]
print("OLD BLOCK:\n", block)
new = """control.ch8ai.com.br {
	handle /cyd* {
		reverse_proxy 127.0.0.1:8790
	}
	handle {
		encode zstd gzip
		header {
			Strict-Transport-Security "max-age=31536000; includeSubDomains"
			X-Content-Type-Options "nosniff"
			X-Frame-Options "DENY"
			Referrer-Policy "strict-origin-when-cross-origin"
			-Server
		}
		root * /var/www/control-kiosk
		try_files {path} /index.html
		file_server
		@assets path /assets/*
		header @assets Cache-Control "public, max-age=31536000, immutable"
		header /index.html Cache-Control "no-cache"
	}
}
"""
t2 = t[:start] + new + t[end:]
p.write_text(t2)
print("rewritten")
