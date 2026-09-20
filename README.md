# ByteNut Auto-Renewal Script

# ⭐ **Found it useful? Give it a Star!**
> Registration link: [https://www.bytenut.com/](https://www.bytenut.com/auth/login)

A GitHub Actions script that automatically checks and renews ByteNut free game servers. Supports multiple accounts, multiple proxy protocols, automatic power-on when offline, and Telegram notifications.

## ✨ Features

- ✅ Multi-account support
- ✅ Automatic login (handles Cloudflare Turnstile verification)
- ✅ Smart server status checks (auto-renew on expiration, auto-power-on when offline)
- ✅ Supports multiple proxy protocols (VLESS / VMess / Trojan / Shadowsocks / SOCKS5)
- ✅ Telegram notifications (with screenshots)
- ✅ Automatic handling of renewal cooldown and expiration protection
- ✅ Keeps the latest 2 run records to avoid repository bloat

## 📋 Prerequisites

### 1. GitHub Secrets Configuration

Go to your repository `Settings` → `Secrets and variables` → `Actions`, and add the following Secrets:

| Secret Name | Required | Description | Example |
|------------|----------|-------------|---------|
| `BYTENUT` | ✅ | ByteNut account information | See format below |
| `TG_BOT_TOKEN` | ❌ | Telegram Bot Token | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TG_CHAT_ID` | ❌ | Telegram Chat ID | `123456789` |
| `PROXY_NODE` | ❌ | Proxy node URL | `vless://uuid@server:port?type=ws&security=tls&sni=example.com` |

### 2. BYTENUT Format

One account per line, in the format: `username-----password` (five dashes in the middle)

```text
user1-----MyP@ssw0rd
user2-----AnotherP@ss
```

### 3. PROXY_NODE Format (Optional)

Supports direct connection or the following proxy protocols:

| Protocol | Example |
|----------|---------|
| VLESS | `vless://uuid@host:port?type=ws&security=tls&sni=example.com` |
| VMess | `vmess://eyJhZGQiOiIxLjIuMy40IiwidiI6IjIiLCJwc...` |
| Trojan | `trojan://password@host:port?type=ws&sni=example.com` |
| Shadowsocks | `ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@host:port` |
| SOCKS5 | `socks5://user:pass@host:port` or `socks5://host:port` |

> Leave it empty to use direct connection. Advanced features such as VLESS Reality / gRPC / WebSocket are supported.

### 4. Telegram Notification Setup (Optional)

1. Create a bot: send `/newbot` to [@BotFather](https://t.me/BotFather)
2. Get your Chat ID: send any message to [@userinfobot](https://t.me/userinfobot)
3. Add the Bot Token and Chat ID to Secrets

## 🚀 How to Use

### Method 1: Scheduled Automatic Run

The workflow runs automatically once per hour (UTC) by default. No manual action is required after forking and configuring the Secrets.

If you want to change the frequency, edit `.github/workflows/bytenut-renewal.yml`:

```yaml
schedule:
  - cron: '0 */1 * * *'  # Run once every hour
```

Common cron expressions:
- `0 */1 * * *` - Every hour
- `0 */2 * * *` - Every 2 hours
- `0 0,12 * * *` - Every day at 00:00 and 12:00

### Method 2: Manual Trigger (GitHub Web UI)

1. Go to the repository `Actions` page
2. Select the `Bytenut Renewal` workflow
3. Click `Run workflow`
4. Click the green `Run workflow` button

### Method 3: API Call

```bash
curl -X POST \
  -H "Authorization: Bearer ghp_XXXXXXXXXXXXXXXXXXXXXXXXX" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/your-username/your-repo-name/actions/workflows/bytenut-renewal.yml/dispatches \
  -d '{"ref":"main"}'
```

## 🐛 Common Issues

### 1. Login Failed

**Possible reasons**:
- Incorrect username/password
- Turnstile verification failed
- Network issue

**Solutions**:
- Check whether the `BYTENUT` Secret format is correct
- Review screenshots from the Actions log (available in Artifacts)
- Try configuring a proxy (`PROXY_NODE`)

### 2. Renewal Failed

**Possible reasons**:
- The server is in the renewal cooldown period
- Turnstile verification did not pass
- The server is expired and cannot be processed

**Solutions**:
- The script will retry automatically on the next run
- Check the screenshots to confirm the exact reason
- Log in to the website manually to verify server status

### 3. Telegram Notifications Not Received

**Possible reasons**:
- Bot Token or Chat ID is incorrect
- The bot has not been started in chat

**Solutions**:
- Send `/start` to the bot in Telegram
- Verify the Secret configuration
- Check the Actions log for error messages

### 4. Proxy Connection Failed

**Possible reasons**:
- `PROXY_NODE` format is incorrect
- Proxy server is unavailable
- Unsupported protocol

**Solutions**:
- Verify that the proxy URL matches the required format
- Test the connectivity of the proxy server
- Leave `PROXY_NODE` empty to use direct mode

### 5. Where to View Screenshots?

After the workflow run completes, scroll down to the `Artifacts` section and download the `screenshots` archive to view all captured screenshots.

## 📋 Server Status and Processing Logic

| Status | Condition | Action |
|--------|-----------|--------|
| `running` and renewable | No cooldown, not expired | ✅ Renew |
| `running` and in cooldown | Cooling down | ⏭️ Skip and wait for next run |
| `offline` and renewable | No cooldown | ✅ Renew and power on |
| `offline` and in cooldown | Cooling down, not expired | ✅ Power on only |
| `offline` and expired | Expired and cooling down | 🚫 Skip and send alert |
| Any state is expired | Renewable | ✅ Renew |

## 🔒 Security Recommendations

1. ✅ Use GitHub Secrets to store sensitive information
2. ✅ Regularly update passwords and sync them to Secrets
3. ✅ Restrict GitHub Token permissions (only `repo` and `workflow`)
4. ✅ Enable private repository mode to prevent information leakage (optional)
5. ✅ Review Actions logs regularly

## 📄 License

MIT License

## 🤝 Contributing

Issues and Pull Requests are welcome!

---

**⚠️ Disclaimer**: This script is intended for educational and learning purposes only. Users must comply with ByteNut's terms of service. The author assumes no responsibility for any problems caused by using this script.
