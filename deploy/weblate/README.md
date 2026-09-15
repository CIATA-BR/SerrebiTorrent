# Weblate at torrent.ciata.org.br

This directory documents the initial CIATA-hosted translation service for SerrebiTorrent.

## Architecture

- Public URL: `https://torrent.ciata.org.br/`
- Apache terminates HTTPS and reverse-proxies to `127.0.0.1:8088`.
- Weblate runs with the official Docker deployment and is not exposed directly on the public network.
- SerrebiTorrent defaults the in-app **Open online translation** action to this host.
- `SERREBITORRENT_TRANSLATION_URL` can override the public URL without changing application code.
- The built-in URL is only a default; downstream deployments can redirect contributors without rebuilding the application.

## 1. DNS

Create an `A` record for `torrent.ciata.org.br` pointing to the CIATA server public IPv4 address. Add an `AAAA` record only if IPv6 is intentionally exposed and filtered correctly.

## 2. Install Docker support

Install Docker Engine and the Docker Compose plugin using the distribution-supported or official Docker packages. Do not expose Docker's daemon socket publicly.

## 3. Obtain the official Weblate Docker deployment

On the server, use a dedicated directory such as `/opt/weblate`:

```bash
sudo mkdir -p /opt/weblate
sudo chown "$USER":"$USER" /opt/weblate
cd /opt/weblate
git clone https://github.com/WeblateOrg/docker-compose.git .
```

Keep the official compose files as the base. Copy this repository's override example to the deployment directory:

```bash
cp /path/to/SerrebiTorrent/deploy/weblate/docker-compose.override.yml.example \
  /opt/weblate/docker-compose.override.yml
```

The override binds Weblate only to `127.0.0.1:8088` and uses the stable `2026` Weblate image family.

## 4. Secrets and administrator account

Do **not** commit passwords or API tokens. For first boot, either let Weblate generate the administrator password and read it from the startup logs, or set `WEBLATE_ADMIN_PASSWORD` only in a local untracked override/environment file and remove it after bootstrap.

The initial administrator e-mail in the example is `contato@ciata.org.br`.

## 5. Start Weblate

```bash
cd /opt/weblate
docker compose pull
docker compose up -d
docker compose ps
```

Check locally before exposing the site:

```bash
curl -I http://127.0.0.1:8088/
```

## 6. Apache and TLS

Enable the required Apache modules:

```bash
sudo a2enmod proxy proxy_http headers rewrite ssl
```

Create the TLS certificate before enabling the final HTTPS vhost, for example with Certbot. Then copy `apache-torrent.ciata.org.br.conf.example` to `/etc/apache2/sites-available/torrent.ciata.org.br.conf`, enable it, test the configuration and reload Apache:

```bash
sudo a2ensite torrent.ciata.org.br.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

The example expects the Let's Encrypt certificate under `/etc/letsencrypt/live/torrent.ciata.org.br/`.

## 7. Create the Weblate project

Recommended initial Weblate structure:

- Project: `SerrebiTorrent`
- Component: `Application`
- Source language: English
- Translation format: GNU gettext PO
- Repository: the SerrebiTorrent Git repository or a translation-specific integration branch
- Source template: `locales/serrebitorrent.pot`
- Translation files: `locales/*.po`

Configure repository synchronization through pull requests rather than granting Weblate direct write access to `main`.

## 8. Generate/update catalogs

From the SerrebiTorrent repository:

```bash
python tools/translation_tool.py template
python tools/translation_tool.py validate locales/<language>.po
python tools/translation_tool.py compile-all-web
```

The desktop runtime consumes reviewed `.po` files directly. The Web UI consumes generated files under `web_static/locales/`.

## 9. Backups

Back up both the Weblate data volume and PostgreSQL regularly. Before Weblate upgrades, create a database backup and keep the existing PostgreSQL major version unless an intentional database migration is planned.

## Security notes

- Keep Weblate bound to loopback; Apache is the only public entry point.
- Keep `WEBLATE_DEBUG` disabled in production.
- Never commit admin passwords, Weblate tokens, GitHub tokens or SMTP credentials.
- Restrict SSH and Docker administration to trusted CIATA administrators.
- Apply operating-system, Docker and Weblate security updates on a controlled cadence.
