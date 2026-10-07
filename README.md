# Clinic AI Assistant — Telegram Bot

Bot for Clínica del Oriente HR (256 employees).  
Replaces the web dashboard: the bot IS the platform.

## Stack
- **Bot**: python-telegram-bot 21.x
- **LLM local**: llama.cpp (llama-server) — LFM2.5-8B-A1B / LFM2.5-2.6B / Qwen2.5-7B
- **LLM cloud fallback**: DeepSeek V4-Flash → OpenAI GPT-5-Nano
- **DB**: SQLite (PostgreSQL-ready)
- **PDF**: WeasyPrint + Jinja2 + QR
- **Contenedores**: Docker Compose (llama-server + bot)
- **Acceso remoto**: Tailscale + SSH

## Skills (build order)
| # | Skill | What it does |
|---|-------|--------------|
| 1 | **certificados** | Generates PDF (work/times/salary) with verification QR |
| 2 | **vacaciones** | Request → approval buttons in leaders' group |
| 3 | **consulta** | Balance, schedule, profile, team (leader), monthly certificates (HR) |

## Security (6 layers)
1. **Whitelist** — in-person registration with employee ID
2. **PIN** — bcrypt, 3 attempts, cooldown + HR alert
3. **Sensitivity** — basic certs: PIN; salary: PIN + extra confirmation
4. **QR/hash** — anti-forgery in PDF
5. **Audit log** — full traceability
6. **Revocation** — instant offboarding (theft/loss)

## Prerequisites (Windows 11)

1. **WSL2** with Ubuntu 22.04+:
   ```powershell
   wsl --install -d Ubuntu-22.04
   ```
2. **NVIDIA driver on Windows** (≥ 512.x). Do NOT install drivers inside WSL — the Windows driver exposes the GPU to WSL2 automatically. Check: `nvidia-smi` in PowerShell.
3. **Docker Desktop** (≥ 4.29) with the **WSL2 backend** enabled:
   - Settings → General → "Use the WSL 2 based engine" ✅
   - Settings → Resources → WSL Integration → enable your Ubuntu distro ✅
4. Verify GPU inside WSL2:
   ```bash
   nvidia-smi
   docker run --rm --gpus all ghcr.io/ggml-org/llama.cpp:server-cuda13 --help
   ```
   Requires an NVIDIA GPU; for CPU-only machines change the image in `docker-compose.yml`.

> **Paths:** run everything inside the WSL2 Linux filesystem (`~/clinica-oriente-bot`). Do NOT put the repo on `C:\` or `/mnt/c` — bind-mount performance is poor there.

## Quick deploy

```bash
# 0. Inside WSL2 (Ubuntu)
cd ~
# 1. Clone and configure
git clone <repo>
cd clinica-oriente-bot
cp .env.example .env
# Edit .env with real tokens

# 2. Download GGUF models into models/
# LFM2.5-8B-A1B, LFM2.5-2.6B, Qwen2.5-7B-Instruct

# 3. Point the server at the active model (no symlink needed)
# docker-compose.yml uses: LLAMA_ARG_MODEL=/models/active/model.gguf
# -> place the chosen file at models/active/model.gguf (copy on Linux, or copy in Explorer)
mkdir -p models/active
cp models/lfm2.5-8b-a1b-q4_k_m.gguf models/active/model.gguf

# 4. Start
docker compose up -d

# 5. Verify
docker compose ps                 # all services healthy
curl -s http://localhost:8080/health
docker compose logs -f bot
```

## Project structure
```
clinica-oriente-bot/
├── docker-compose.yml
├── config.yaml
├── .env
├── models/
│   └── active/model.gguf   (copy of the chosen model)
├── bot/
│   ├── Dockerfile
│   ├── main.py
│   ├── config.py
│   ├── transport/telegram.py
│   ├── skills/
│   │   ├── certificados.py
│   │   ├── vacaciones.py
│   │   └── consulta.py
│   ├── engine/
│   │   ├── labor_law.py
│   │   └── router.py
│   ├── db/
│   │   ├── models.py
│   │   └── __init__.py
│   └── utils/
└── data/ (SQLite + certificados + logs)
```

## Offline installation (recommended for the clinic)

Do not depend on internet at install time. Prepare a release bundle on an SSD:

```bash
# On your dev machine / before visiting the clinic:
docker build -t clinica-bot:latest ./bot
docker save ghcr.io/ggml-org/llama.cpp:server-cuda13 -o images/llama-server.tar
docker save clinica-bot:latest -o images/clinica-bot.tar
# + full repo zip, models/*.gguf, INSTALACION_CLINICA.pdf
```

On the clinic PC (inside WSL2):

```bash
docker load -i images/llama-server.tar
docker load -i images/clinica-bot.tar
cd ~/clinica-oriente-bot && cp .env.example .env
docker compose up -d
```

## Remote access (after clinic install)

```powershell
# On the clinic Windows PC:
# 1. Install Tailscale for Windows (system tray app, sign in)
# 2. Optional: enable OpenSSH Server (Settings > Optional Features)
```

```bash
# From your laptop (after signing into the same Tailscale account):
ssh clinic-windows        # opens PowerShell on the clinic PC
wsl                       # enter Ubuntu
cd ~/clinica-oriente-bot
docker compose logs -f bot
docker compose ps
```

- Tailscale provides the encrypted tunnel; no router configuration needed.
- If OpenSSH Server is blocked by the clinic firewall, restrict the SSH rule to the Tailscale interface.

## Model benchmark (Phase 0)
```bash
# 20 test prompts covering the 3 skills
# Gate: ≥90% intent accuracy + <10s response
```

## Costs
- Local: **$0/mo** (80% of requests)
- DeepSeek V4-Flash: **~$0.90/mo** (fallback)
- Estimated total: **<$2/mo** for 256 employees

> Note: `config.yaml → pdf.qr_base_url` (`https://oriente.local/verify`) is a placeholder. For real QR verification use a URL reachable from outside (e.g. a Tailscale/DDNS-hosted verifier).

## License
Private — Clínica del Oriente