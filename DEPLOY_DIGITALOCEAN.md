# DigitalOcean Deploy

Bu proje için en pratik kurulum:

- Uygulamayı Docker ile çalıştır
- SQLite verisini host üzerindeki `data/` klasöründe tut
- Domain'i mevcut reverse proxy'ne bağla

## 1. Sunucuda gerekli araçlar

Ubuntu için:

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

## 2. Kodu sunucuya al

```bash
git clone <GITHUB_REPO_URL> leadbot
cd leadbot
cp .env.example .env
```

`.env` içinde en az şunları değiştir:

```env
LEADBOT_USERNAME=senin-kullanici-adin
LEADBOT_PASSWORD=guclu-bir-sifre
LEADBOT_SESSION_SECRET=uzun-rastgele-bir-gizli-anahtar
```

## 3. Container'ı ayağa kaldır

```bash
docker compose up -d --build
```

Kontrol:

```bash
docker compose ps
docker compose logs -f leadbot
```

Uygulama host üzerinde şu adreste dinler:

- `http://127.0.0.1:8000`

## 4. Domain bağlama

DNS tarafında bir `A` kaydı oluştur:

- `lead.senin-domainin.com -> droplet-ip`

## 5. Reverse proxy

Bu repoda örnek bir Caddy konfigi var: `Caddyfile.example`

Eğer sunucuda hali hazırda Nginx veya Caddy kullanıyorsan, mantık şu:

- dış istek `lead.senin-domainin.com`
- iç hedef `127.0.0.1:8000`

Örnek Caddy:

```caddy
lead.senin-domainin.com {
  encode zstd gzip
  reverse_proxy 127.0.0.1:8000
}
```

## 6. Güncelleme

```bash
cd leadbot
git pull
docker compose up -d --build
```

## Notlar

- SQLite verisi `./data/leadbot.db` içinde kalır.
- `docker compose down` veriyi silmez.
- Scraper Playwright/Chromium kullandığı için Docker image ilk build'de biraz uzun sürebilir.
- Eğer 80/443 portları şu an n8n veya başka bir servis tarafından kullanılıyorsa, mevcut reverse proxy yapılandırmana sadece yeni bir host kuralı eklemen gerekir. LeadBot container'ı zaten sadece `127.0.0.1:8000` üstünde açılıyor.
