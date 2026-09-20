# ByteNut 自动续期脚本

# ⭐ **觉得有用？给个 Star 支持一下！**
> 注册地址：[https://www.bytenut.com/](https://www.bytenut.com/auth/login)

自动检查并续期 ByteNut 免费游戏服务器的 GitHub Actions 脚本。支持多账号、多种代理协议、离线自动开机和 Telegram 通知等功能。

## ✨ 功能特性

- ✅ 多账号支持
- ✅ 自动登录（处理 Cloudflare Turnstile 验证）
- ✅ 智能检测服务器状态（过期自动续期，离线自动开机）
- ✅ 支持多种代理协议（VLESS / VMess / Trojan / Shadowsocks / SOCKS5）
- ✅ Telegram 通知（带截图）
- ✅ 自动处理续期冷却与过期保护
- ✅ 保留最近 2 条运行记录，仓库清爽不膨胀


## 📋 前置要求

### 1. GitHub Secrets 配置

进入仓库 `Settings` → `Secrets and variables` → `Actions`，添加以下 Secrets：

| Secret 名称 | 必填 | 说明 | 示例 |
|------------|------|------|------|
| `BYTENUT` | ✅ | ByteNut 账号信息 | 见下方格式 |
| `TG_BOT_TOKEN` | ❌ | Telegram Bot Token | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TG_CHAT_ID` | ❌ | Telegram Chat ID | `123456789` |
| `PROXY_NODE` | ❌ | 代理节点链接 | `vless://uuid@server:port?type=ws&security=tls&sni=example.com` |

### 2. BYTENUT 格式

每行一个账号，格式：`用户名-----密码`（中间是五个减号）

```
user1-----MyP@ssw0rd
user2-----AnotherP@ss
```

### 3. PROXY_NODE 格式（可选）

支持直连或以下代理协议：

| 协议 | 示例 |
|------|------|
| VLESS | `vless://uuid@host:port?type=ws&security=tls&sni=example.com` |
| VMess | `vmess://eyJhZGQiOiIxLjIuMy40IiwidiI6IjIiLCJwc...` |
| Trojan | `trojan://password@host:port?type=ws&sni=example.com` |
| Shadowsocks | `ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@host:port` |
| SOCKS5 | `socks5://user:pass@host:port` 或 `socks5://host:port` |

> 留空则使用直连。VLESS Reality / gRPC / WebSocket 等高级特性均已支持。

### 4. Telegram 通知配置（可选）

1. 创建 Bot：向 [@BotFather](https://t.me/BotFather) 发送 `/newbot`
2. 获取 Chat ID：向 [@userinfobot](https://t.me/userinfobot) 发送任意消息
3. 将 Bot Token 和 Chat ID 添加到 Secrets

## 🚀 使用方法

### 方法 1：定时自动运行

工作流默认每小时执行一次（UTC 时间），无需任何操作。Fork 并配置好 Secrets 后即开始自动工作。

如果需要修改频率，可编辑 `.github/workflows/bytenut-renewal.yml`：

```yaml
schedule:
  - cron: '0 */1 * * *'  # 每小时执行一次
```

常用 cron 表达式：
- `0 */1 * * *` - 每小时
- `0 */2 * * *` - 每 2 小时
- `0 0,12 * * *` - 每天 0 点和 12 点

### 方法 2：手动触发（GitHub 网页）

1. 进入仓库的 `Actions` 页面
2. 选择 `Bytenut 续期` 工作流
3. 点击 `Run workflow`
4. 点击绿色的 `Run workflow` 按钮

### 方法 3：API 调用

```bash
curl -X POST \
  -H "Authorization: Bearer ghp_XXXXXXXXXXXXXXXXXXXXXXXXX" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/你的用户名/你的仓库名/actions/workflows/bytenut-renewal.yml/dispatches \
  -d '{"ref":"main"}'
```

## 🐛 常见问题

### 1. 登录失败

**原因**：
- 账号密码错误
- Turnstile 验证失败
- 网络问题

**解决**：
- 检查 `BYTENUT` Secret 格式是否正确
- 查看 Actions 日志中的截图（在 Artifacts 中）
- 尝试配置代理（`PROXY_NODE`）

### 2. 续期失败

**原因**：
- 处于续期冷却期
- Turnstile 验证未通过
- 服务器已过期且无法操作

**解决**：
- 脚本会自动在下次运行时重试
- 检查截图确认具体原因
- 手动登录网站查看服务器状态

### 3. Telegram 通知未收到

**原因**：
- Bot Token 或 Chat ID 错误
- Bot 未启动对话

**解决**：
- 在 Telegram 中向 Bot 发送 `/start`
- 验证 Secret 配置是否正确
- 检查 Actions 日志中的错误信息

### 4. 代理连接失败

**原因**：
- `PROXY_NODE` 格式错误
- 代理服务器不可用
- 不支持的协议

**解决**：
- 验证代理链接是否符合规范
- 测试代理服务器连通性
- 留空 `PROXY_NODE` 则使用直连模式

### 5. 截图在哪里查看？

在 Actions 运行完成后，向下滚动找到 `Artifacts` 区域，下载 `screenshots` 压缩包即可查看所有截图。

## 📋 服务器状态与处理逻辑

| 状态 | 条件 | 操作 |
|------|------|------|
| `running` 且可续期 | 无冷却，未过期 | ✅ 续期 |
| `running` 且冷却中 | 冷却期内 | ⏭️ 跳过，等待下次运行 |
| `offline` 且可续期 | 无冷却 | ✅ 续期并开机 |
| `offline` 且冷却中 | 冷却期，未过期 | ✅ 仅开机 |
| `offline` 且已过期 | 已过期且冷却中 | 🚫 跳过，推送提醒 |
| 任意状态已过期 | 可续期 | ✅ 续期 |

## 🔒 安全建议

1. ✅ **使用 GitHub Secrets** 存储敏感信息
2. ✅ **定期更新密码** 并同步到 Secrets
3. ✅ **限制 GitHub Token 权限**（仅 `repo` 和 `workflow`）
4. ✅ **开启仓库私有** 防止信息泄露（可选）
5. ✅ **定期检查 Actions 运行日志**

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**⚠️ 免责声明**：本脚本仅供学习交流使用，使用者需遵守 ByteNut 的服务条款。因使用本脚本造成的任何问题，作者不承担任何责任。
