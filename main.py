import time
import os
import requests
import platform
from datetime import datetime

if "DISPLAY" not in os.environ:
    if platform.system().lower() == "linux":
        try:
            from pyvirtualdisplay import Display
            display = Display(visible=False, size=(1920, 1080))
            display.start()
            os.environ["DISPLAY"] = display.new_display_var
        except:
            pass

from seleniumbase import SB

# ================= Configuration Area =================
PROXY = os.getenv("PROXY") or None
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
ACCOUNTS = os.getenv("BYTENUT", "")

URL_LOGIN_PANEL = "https://www.bytenut.com/auth/login"
URL_HOMEPAGE = "https://www.bytenut.com/homepage"
API_SERVER_LIST = "https://www.bytenut.com/game-panel/api/gpPanelServer/user/servers"
API_EXTENSION_INFO = "https://www.bytenut.com/game-panel/api/gp-free-server/extension-info/{}"
API_START_STATUS = "https://www.bytenut.com/game-panel/api/serverStartQueue/status/{}"

RENEW_MENU = '//li[contains(., "RENEW SERVER")]'
EXTEND_BTN = "button.extend-btn"
START_BTN = "button.start-btn"
START_VERIFY_DIALOG = "div.el-dialog"
MANAGEMENT_MENU = '//li[contains(@class,"el-sub-menu")]//span[text()="Management"]'
CONSOLE_MENU_ITEM = '//li[contains(@class,"el-menu-item")]//span[text()="Console"]'
PAGE_READY_INDICATOR = '//li[contains(@class,"el-menu-item")]'


def parse_accounts(raw: str):
    accounts = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line or "-----" not in line:
            continue
        parts = line.split("-----", 1)
        if len(parts) == 2:
            accounts.append((parts[0].strip(), parts[1].strip()))
    return accounts


class BytenutRenewal:

    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.screenshot_dir = os.path.join(self.BASE_DIR, "artifacts")
        os.makedirs(self.screenshot_dir, exist_ok=True)

    # ========== Masking Utilities ==========
    def mask_account(self, u):
        if not u:
            return "Unknown"
        u = u.strip()
        if "@" in u:
            local, domain = u.split("@", 1)
            masked_local = (
                local[:2] + "*" * (len(local) - 2)
                if len(local) > 2
                else local[0] + "*"
            )
            return f"{masked_local}@{domain}"
        return u[:2] + "*" * (len(u) - 2) if len(u) > 2 else u[0] + "*"

    def mask_server_id(self, sid):
        return "[server]"

    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] [INFO] {msg}", flush=True)

    def shot(self, sb, name):
        path = os.path.join(self.screenshot_dir, name)
        sb.save_screenshot(path)
        return path

    # ========== Telegram Notifications ==========
    def send_tg(self, icon, title, account_name, server_id,
                state_str, expiry_str, extra="", screenshot=None):
        if not TG_TOKEN or not TG_CHAT_ID:
            return
        msg = (
            f"{icon} {title}\n\n"
            f"Account: {account_name}\n"
            f"Server: {server_id}\n"
            f"Status: {state_str}\n"
            f"Expiration: {expiry_str}\n"
        )
        if extra:
            msg += f"\n{extra}\n"
        msg += "\nByteNut Auto Renewal"
        try:
            if screenshot and os.path.exists(screenshot):
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
                with open(screenshot, "rb") as f:
                    requests.post(
                        url,
                        data={"chat_id": TG_CHAT_ID, "caption": msg},
                        files={"photo": f},
                    )
            else:
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg})
        except Exception as e:
            self.log(f"TG send failed: {e}")

    # ========== Browser-side fetch (script injects variables) ==========
    def fetch_api(self, sb, url, method="GET", referer=None):
        """
        Execute fetch in browser context, with variables directly embedded in the script.
        Returns parsed data; if it fails, returns None.
        """
        if referer is None:
            referer = URL_HOMEPAGE

        # Use json.dumps to ensure strings are escaped correctly
        import json
        url_js = json.dumps(url)
        method_js = json.dumps(method)
        referer_js = json.dumps(referer)

        script = f"""
        var callback = arguments[0];
        var token = localStorage.getItem('yl-token')
                 || sessionStorage.getItem('yl-token') || '';
        var headers = {{
            'Accept': 'application/json, text/plain, */*',
            'Referer': {referer_js}
        }};
        if (token) {{ headers['Yl-Token'] = token; }}
        fetch({url_js}, {{
            method: {method_js},
            headers: headers,
            credentials: 'include'
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{ callback({{ok: true, data: data}}); }})
        .catch(function(e) {{ callback({{ok: false, error: e.toString()}}); }});
        """
        try:
            result = sb.execute_async_script(script)
            if result and result.get("ok"):
                resp = result["data"]
                if resp.get("code") == 200:
                    return resp.get("data")
                self.log(f"API business error: {resp.get('message')}")
            else:
                err = result.get("error") if result else "None"
                self.log(f"fetch failed: {err}")
        except Exception as e:
            self.log(f"fetch_api exception: {e}")
        return None

    def fetch_api_post(self, sb, url, referer=None):
        """POST version"""
        if referer is None:
            referer = URL_HOMEPAGE

        import json
        url_js = json.dumps(url)
        referer_js = json.dumps(referer)

        script = f"""
        var callback = arguments[0];
        var token = localStorage.getItem('yl-token')
                 || sessionStorage.getItem('yl-token') || '';
        var headers = {{
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': {referer_js}
        }};
        if (token) {{ headers['Yl-Token'] = token; }}
        fetch({url_js}, {{
            method: 'POST',
            headers: headers,
            credentials: 'include'
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{ callback({{ok: true, data: data}}); }})
        .catch(function(e) {{ callback({{ok: false, error: e.toString()}}); }});
        """
        try:
            result = sb.execute_async_script(script)
            if result and result.get("ok"):
                resp = result["data"]
                if resp.get("code") == 200:
                    return resp.get("data")
                self.log(f"API business error: {resp.get('message')}")
            else:
                err = result.get("error") if result else "None"
                self.log(f"fetch POST failed: {err}")
        except Exception as e:
            self.log(f"fetch_api_post exception: {e}")
        return None

    # ========== API Wrappers ==========
    def get_servers_data(self, sb):
        return self.fetch_api(sb, API_SERVER_LIST, referer=URL_HOMEPAGE)

    def get_extension_data(self, sb, server_id):
        ref = f"https://www.bytenut.com/free-gamepanel/{server_id}"
        return self.fetch_api(sb, API_EXTENSION_INFO.format(server_id),
                              referer=ref)

    def get_start_status(self, sb, server_id):
        ref = f"https://www.bytenut.com/free-gamepanel/{server_id}"
        return self.fetch_api(sb, API_START_STATUS.format(server_id),
                              referer=ref)

    # ========== Wait for Page Ready ==========
    def wait_for_panel_ready(self, sb, server_id, timeout=30):
        self.log("⏳ Waiting for page to load...")
        try:
            sb.wait_for_element_present(PAGE_READY_INDICATOR, timeout=timeout)
        except Exception:
            self.log("⚠️ Sidebar not visible, continuing...")

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if sb.is_element_present(RENEW_MENU):
                    self.log("✅ Page ready (RENEW SERVER visible)")
                    return True
            except Exception:
                pass
            self.remove_overlay_ads(sb)
            time.sleep(1)
        self.log("⚠️ Timed out waiting for RENEW SERVER")
        return False

    # ========== Poll Startup Queue ==========
    def poll_start_status(self, sb, server_id, timeout=300, interval=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            data = self.get_start_status(sb, server_id)
            if data:
                in_queue = data.get("inQueue", True)
                can_start = data.get("canStart", False)
                pos = data.get("queuePosition", 0)
                wait_sec = data.get("estimatedWaitSeconds")
                msg = data.get("statusMessage", "")
                self.log(f"  Queue: inQueue={in_queue}, pos={pos}, "
                         f"wait={wait_sec}s, msg={msg}")
                if not in_queue and can_start:
                    self.log("✅ Server started successfully (queue completed)")
                    return True, "running"
            time.sleep(interval)
        return False, "timeout"

    def wait_until_running(self, sb, server_id, timeout=120, interval=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            servers = self.get_servers_data(sb)
            if servers:
                for srv in servers:
                    if str(srv.get("id")) == str(server_id):
                        state = (srv.get("serverInfo") or {}).get(
                            "state", "unknown")
                        self.log(f"  server state: {state}")
                        if state == "running":
                            return True, state
            time.sleep(interval)
        return False, "unknown"

    def wait_until_not_expired(self, sb, server_id, timeout=120, interval=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            ext_info = self.get_extension_data(sb, server_id)
            if ext_info and ext_info.get("minutesUntilExpiration", 0) > 0:
                return True
            time.sleep(interval)
        return False

    # ========== Ad Cleanup ==========
    def remove_overlay_ads(self, sb):
        try:
            sb.execute_script("""
                (function(){
                    var a = document.getElementById('ez-accept-all');
                    if (a) a.click();
                    var keep = ['turnstile','cf-turnstile','extend-btn',
                                'adsterra-rewarded','Claim Reward','Watch Ad',
                                'start-btn','Start','Continue',
                                'RENEW SERVER','el-menu'];
                    ['ins.adsbygoogle','iframe[id^="aswift"]',
                     'div[id^="google_ads"]',
                     'div[class*="ad-"]:not([class*="adsterra-rewarded"])',
                     'div[class*="ads-"]',
                     'div[id*="ad-"]:not([id*="adsterra"])',
                     'div[id*="ads-"]','.ad-container','.ads-wrapper',
                     '.fixed-bottom-banner','.ezoic-floating-bottom',
                     '.fc-ab-root'
                    ].forEach(function(s){
                        document.querySelectorAll(s).forEach(function(el){
                            if (keep.some(function(k){
                                return el.innerHTML.indexOf(k) !== -1;
                            })) return;
                            el.style.cssText += 'display:none!important;'
                                + 'visibility:hidden!important;'
                                + 'height:0!important;width:0!important;';
                        });
                    });
                    document.body.style.overflow = 'auto';
                    document.body.style.position = 'static';
                })();
            """)
        except Exception:
            pass

    # ========== Turnstile ==========
    def is_turnstile_present(self, sb):
        try:
            return sb.execute_script("""
                return !!(document.querySelector('.cf-turnstile')
                    || document.querySelector(
                        'iframe[src*="challenges.cloudflare"]')
                    || document.querySelector(
                        'input[name="cf-turnstile-response"]'));
            """)
        except Exception:
            return False

    def wait_turnstile(self, sb, timeout=90):
        if not self.is_turnstile_present(sb):
            self.log("ℹ️ No Turnstile verification")
            return True
        self.log("⏳ Waiting for Turnstile verification...")
        start = time.time()
        last_click = 0
        while time.time() - start < timeout:
            self.remove_overlay_ads(sb)
            try:
                sb.execute_script("""
                    var e = document.querySelector('.cf-turnstile');
                    if (e) e.scrollIntoView({block:'center'});
                """)
            except Exception:
                pass
            try:
                val = sb.execute_script(
                    "return document.querySelector("
                    "\"input[name='cf-turnstile-response']\")?.value || '';"
                )
                if len(val) > 20:
                    self.log("✅ Turnstile completed")
                    return True
            except Exception:
                pass
            now = time.time()
            if now - last_click > 3:
                try:
                    sb.uc_gui_click_captcha()
                    last_click = now
                except Exception:
                    try:
                        sb.find_element(".cf-turnstile").click()
                        last_click = now
                    except Exception:
                        pass
            time.sleep(1)
        self.log("⚠️ Turnstile timed out")
        return False

    def _wait_dialog_turnstile(self, sb, timeout=30):
        self.log("⏳ Waiting for pop-up Turnstile (up to 30s)...")
        start = time.time()
        last_click = 0
        while time.time() - start < timeout:
            self.remove_overlay_ads(sb)
            if sb.execute_script(
                    "return !document.querySelector('div.el-dialog');"):
                self.log("✅ Dialog disappeared, verification completed automatically")
                return True
            if sb.execute_script("""
                var btn = document.querySelector(
                    'div.el-dialog__footer button.el-button--primary');
                return btn && !btn.disabled
                    && !btn.classList.contains('is-disabled');
            """):
                self.log("✅ Continue is enabled, Turnstile completed automatically")
                return True
            try:
                val = sb.execute_script("""
                    var d = document.querySelector('div.el-dialog');
                    if (!d) return '';
                    var i = d.querySelector(
                        'input[name="cf-turnstile-response"]');
                    return i ? i.value : '';
                """)
                if val and len(val) > 20:
                    self.log("✅ Pop-up Turnstile token filled")
                    return True
            except Exception:
                pass
            now = time.time()
            if now - last_click > 3:
                try:
                    sb.uc_gui_click_captcha()
                    last_click = now
                except Exception:
                    try:
                        sb.execute_script("""
                            var d = document.querySelector('div.el-dialog');
                            if (d) {
                                var ts = d.querySelector('.cf-turnstile');
                                if (ts) ts.click();
                            }
                        """)
                        last_click = now
                    except Exception:
                        pass
            time.sleep(1)

        # Final check after timeout
        if sb.execute_script(
                "return !document.querySelector('div.el-dialog');"):
            self.log("✅ Dialog disappeared after timeout")
            return True
        if sb.execute_script("""
            var btn = document.querySelector(
                'div.el-dialog__footer button.el-button--primary');
            return btn && !btn.disabled
                && !btn.classList.contains('is-disabled');
        """):
            self.log("✅ Continue enabled after timeout")
            return True
        self.log("⚠️ Turnstile wait ended, continuing anyway")
        return True

    # ========== Ad Verification Dialog ==========
    def handle_ad_verification(self, sb):
        try:
            if not sb.execute_script(
                "return !!document.querySelector("
                "'div.adsterra-rewarded-dialog');"
            ):
                return True
            self.log("🛡️ Handling ad verification...")
            time.sleep(1)
            sb.execute_script("""
                var btn = document.querySelector(
                    'div.adsterra-rewarded-dialog button.el-button--primary');
                if (btn) btn.click();
            """)
            time.sleep(3)
            orig = sb.driver.current_window_handle
            if len(sb.driver.window_handles) > 1:
                for h in sb.driver.window_handles:
                    if h != orig:
                        sb.driver.switch_to.window(h)
                        break
                time.sleep(12)
                sb.driver.close()
                sb.driver.switch_to.window(orig)
                time.sleep(2)
            sb.execute_script("""
                var btn = document.querySelector(
                    'div.adsterra-rewarded-dialog button.el-button--success');
                if (btn) btn.click();
            """)
            time.sleep(3)
            self.log("✅ Ad verification completed")
            return True
        except Exception as e:
            self.log(f"Ad verification exception: {e}")
            return True

    # ========== Navigation + Wait for Readiness ==========
    def navigate_to_panel(self, sb, server_id):
        url = f"https://www.bytenut.com/free-gamepanel/{server_id}"
        sb.uc_open_with_reconnect(url, reconnect_time=6)
        time.sleep(5)
        self.remove_overlay_ads(sb)
        return self.wait_for_panel_ready(sb, server_id, timeout=30)

    # ========== Click RENEW SERVER (with retry) ==========
    def click_renew_menu(self, sb, server_id, idx, max_retry=3):
        for attempt in range(1, max_retry + 1):
            try:
                sb.wait_for_element_present(RENEW_MENU, timeout=15)
                sb.wait_for_element_visible(RENEW_MENU, timeout=10)
                self.remove_overlay_ads(sb)
                sb.click(RENEW_MENU)
                time.sleep(3)
                self.log(f"✅ RENEW SERVER clicked (attempt {attempt})")
                return True
            except Exception as e:
                self.log(f"⚠️ RENEW SERVER failed (attempt {attempt}): {e}")
                if attempt < max_retry:
                    self.shot(sb, f"renew_fail_{idx}_a{attempt}.png")
                    self.log("🔄 Navigating again...")
                    self.navigate_to_panel(sb, server_id)
        self.log("❌ RENEW SERVER failed permanently")
        return False

    # ========== Renewal ==========
    def try_extend_and_verify(self, sb, server_id, old_expiry):
        if not self.wait_turnstile(sb):
            return False, ""
        self.remove_overlay_ads(sb)
        self.log("⏳ Clicking extension button...")
        try:
            if sb.is_element_visible(EXTEND_BTN):
                sb.execute_script("arguments[0].click();",
                                  sb.find_element(EXTEND_BTN))
            else:
                self.log("⚠️ Extension button not visible")
                return False, ""
        except Exception as e:
            self.log(f"Extension button click failed: {e}")
            return False, ""

        time.sleep(2)
        self.handle_ad_verification(sb)
        time.sleep(5)

        for _ in range(6):
            new_ext = self.get_extension_data(sb, server_id)
            if new_ext:
                new_expiry = new_ext.get("expiredTime", "")
                if new_expiry and new_expiry != old_expiry:
                    self.log(f"✅ Renewal took effect: {self.format_expiry(new_expiry)}")
                    return True, self.format_expiry(new_expiry)
            time.sleep(5)

        if (sb.is_element_present(EXTEND_BTN)
                and not sb.is_element_enabled(EXTEND_BTN)):
            return "cooldown", ""
        return False, ""

    # ========== UI Startup ==========
    def ui_start_server(self, sb, server_id, idx):
        self.log("🖥️ Navigating to Console page...")
        self.navigate_to_panel(sb, server_id)

        # Step 1: Expand Management
        self.log("📂 Expanding Management...")
        try:
            sb.click(MANAGEMENT_MENU)
            time.sleep(2)
        except Exception:
            try:
                sb.execute_script("""
                    document.querySelectorAll('.el-sub-menu__title span')
                    .forEach(function(el){
                        if (el.textContent.trim() === 'Management')
                            el.closest('.el-sub-menu__title').click();
                    });
                """)
                time.sleep(2)
            except Exception as e:
                self.log(f"Management expansion failed: {e}")
                return False, "management_fail"

        # Step 2: Click Console
        self.log("🖥️ Clicking Console...")
        try:
            sb.click(CONSOLE_MENU_ITEM)
            time.sleep(3)
        except Exception:
            try:
                sb.execute_script("""
                    document.querySelectorAll('.el-menu-item span')
                    .forEach(function(el){
                        if (el.textContent.trim() === 'Console')
                            el.closest('.el-menu-item').click();
                    });
                """)
                time.sleep(3)
            except Exception as e:
                self.log(f"Console click failed: {e}")

        # Step 3: Wait for Start button
        try:
            sb.wait_for_element_present(START_BTN, timeout=15)
            self.log("✅ Console page ready")
        except Exception as e:
            self.log(f"⚠️ Timed out waiting for Start: {e}")
            self.shot(sb, f"no_start_btn_{idx}.png")
            return False, "no_start_btn"

        # Step 4: Click Start
        self.log("▶️ Clicking Start...")
        self.remove_overlay_ads(sb)
        try:
            btn = sb.find_element(START_BTN)
            if btn.get_attribute("disabled"):
                self.log("⚠️ Start disabled")
                return False, "start_disabled"
            sb.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.5)
            sb.execute_script("arguments[0].click();", btn)
            self.log("  Start clicked")
            time.sleep(2)
        except Exception as e:
            self.log(f"Start click failed: {e}")
            return False, "start_click_fail"

        # Step 5: Wait for verification dialog (up to 10s)
        self.log("⏳ Waiting for verification dialog...")
        dialog_appeared = False
        for _ in range(10):
            try:
                if sb.is_element_visible(START_VERIFY_DIALOG):
                    dialog_appeared = True
                    break
            except Exception:
                pass
            data = self.get_start_status(sb, server_id)
            if data and not data.get("inQueue") and data.get("canStart"):
                self.log("✅ No dialog, server started directly")
                return True, "running"
            time.sleep(1)

        if not dialog_appeared:
            self.log("⚠️ Dialog did not appear, polling status...")
            ok, state = self.poll_start_status(sb, server_id, timeout=60)
            return (True, state) if ok else (False, "dialog_not_appeared")

        self.log("✅ Verification dialog appeared")

        # Step 6: Wait for Turnstile
        self._wait_dialog_turnstile(sb, timeout=30)

        # Step 7: Click Continue (up to 60s)
        self.log("▶️ Waiting for and clicking Continue...")
        continue_clicked = False
        for attempt in range(30):
            if sb.execute_script(
                    "return !document.querySelector('div.el-dialog');"):
                self.log("✅ Dialog disappeared automatically")
                continue_clicked = True
                break
            if sb.execute_script("""
                var btn = document.querySelector(
                    'div.el-dialog__footer button.el-button--primary');
                return btn && !btn.disabled
                    && !btn.classList.contains('is-disabled');
            """):
                sb.execute_script("""
                    document.querySelector(
                        'div.el-dialog__footer button.el-button--primary'
                    ).click();
                """)
                self.log(f"  Continue clicked (attempt {attempt + 1})")
                continue_clicked = True
                break
            if attempt % 5 == 0:
                self.log(f"  Waiting for Continue to enable... ({attempt + 1}/30)")
            time.sleep(2)

        if not continue_clicked:
            self.log("❌ Continue not enabled")
            self.shot(sb, f"continue_fail_{idx}.png")
            return False, "continue_fail"

        time.sleep(3)

        # Step 8: Handle queue dialog
        self._handle_queue_dialog(sb)

        # Step 9: Poll startup status
        self.log("⏳ Polling startup status...")
        ok, state = self.poll_start_status(
            sb, server_id, timeout=300, interval=5)
        if ok:
            self.log("⏳ Confirming runtime status...")
            is_running, final_state = self.wait_until_running(
                sb, server_id, timeout=120, interval=10)
            return True, "running" if is_running else f"started({final_state})"
        return False, "start_timeout"

    def _handle_queue_dialog(self, sb):
        try:
            has_q = False
            for _ in range(5):
                has_q = sb.execute_script(
                    "return !!document.querySelector("
                    "'div.el-message-box.queue-dialog-styled');"
                )
                if has_q:
                    break
                time.sleep(1)
            if has_q:
                self.log("📋 Queue dialog, clicking OK...")
                sb.execute_script("""
                    document.querySelectorAll(
                        'div.el-message-box.queue-dialog-styled '
                        '.el-message-box__btns button'
                    ).forEach(function(btn){
                        if (btn.textContent.trim() === 'OK') btn.click();
                    });
                """)
                time.sleep(2)
                self.log("✅ Queue dialog closed")
            else:
                self.log("ℹ️ No queue dialog")
        except Exception as e:
            self.log(f"Queue dialog exception: {e}")

    def format_expiry(self, dt_str):
        if not dt_str:
            return ""
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(dt_str, fmt).strftime(
                    "%b %d, %Y, %I:%M %p UTC")
            except ValueError:
                continue
        return dt_str

    # ========== Main Flow ==========
    def run(self):
        self.log("🚀 Starting ByteNut renewal and startup")
        accounts = parse_accounts(ACCOUNTS)
        if not accounts:
            self.log("❌ No account")
            return

        for idx, (user, pwd) in enumerate(accounts, 1):
            masked_user = self.mask_account(user)
            self.log(f"==== Account [{idx}] {masked_user} ====")

            with SB(
                uc=True, test=True, headed=True,
                chromium_arg=(
                    "--no-sandbox,--disable-dev-shm-usage,"
                    "--disable-gpu,--window-size=1280,753"
                ),
                proxy=PROXY,
            ) as sb:
                try:
                    # --- Login ---
                    sb.uc_open_with_reconnect(URL_LOGIN_PANEL, reconnect_time=5)
                    sb.wait_for_element_visible(
                        'input[placeholder="Username"]', timeout=25)
                    sb.type('input[placeholder="Username"]', user)
                    sb.type('input[placeholder="Password"]', pwd)
                    sb.click('//button[contains(., "Sign In")]')
                    time.sleep(5)
                    if "/auth/login" in sb.get_current_url():
                        self.send_tg("❌", "Login failed", user, "Unknown",
                                     "Unknown", "",
                                     screenshot=self.shot(
                                         sb, f"login_fail_{idx}.png"))
                        continue
                    self.log("✅ Login successful")

                    # Stay on homepage to stabilize Cloudflare cookies
                    sb.uc_open_with_reconnect(URL_HOMEPAGE, reconnect_time=6)
                    time.sleep(8)

                    # --- Get server information ---
                    servers = self.get_servers_data(sb)
                    if not servers:
                        self.send_tg("⚠️", "Warning", user, "Unknown",
                                     "Unknown", "API request failed",
                                     screenshot=self.shot(
                                         sb, f"no_server_{idx}.png"))
                        continue

                    server = servers[0]
                    server_id = str(server.get("id") or "")
                    server_info = server.get("serverInfo") or {}
                    state = server_info.get("state", "running")
                    expired_time = server.get("expiredTime") or ""
                    expiry_str = self.format_expiry(expired_time)
                    log_sid = self.mask_server_id(server_id)
                    self.log(f"Server {log_sid}: status={state}, expiration={expiry_str}")

                    if not server_id:
                        self.send_tg("❌", "Failed", user, "Unknown",
                                     state, expiry_str, "Server ID is invalid",
                                     screenshot=self.shot(
                                         sb, f"invalid_id_{idx}.png"))
                        continue

                    ext_info = self.get_extension_data(sb, server_id)
                    if not ext_info:
                        self.send_tg("❌", "Failed", user, server_id,
                                     state, expiry_str,
                                     extra="Unable to get extension information",
                                     screenshot=self.shot(
                                         sb, f"ext_info_fail_{idx}.png"))
                        continue

                    can_extend = ext_info.get("canExtend", False)
                    cooldown_min = ext_info.get("minutesUntilNextExtension", 0)
                    mins_until_exp = ext_info.get("minutesUntilExpiration", 9999)
                    expired = mins_until_exp <= 0
                    self.log(f"Can extend={can_extend}, cooldown={cooldown_min} min, "
                             f"time until expiration={mins_until_exp} min")

                    # ===== Offline handling =====
                    if state == "offline":
                        if can_extend:
                            self.log("🔴 Offline and extendable, renew first then start...")
                            ready = self.navigate_to_panel(sb, server_id)
                            if not ready:
                                self.send_tg("❌", "Panel load failed", user,
                                             server_id, "offline", expiry_str,
                                             screenshot=self.shot(
                                                 sb, f"panel_fail_{idx}.png"))
                                continue
                            if not self.click_renew_menu(sb, server_id, idx):
                                self.send_tg("❌", "Renew menu failed", user,
                                             server_id, "offline", expiry_str,
                                             screenshot=self.shot(
                                                 sb, f"renew_fail_{idx}.png"))
                                continue
                            result, new_time = self.try_extend_and_verify(
                                sb, server_id, expired_time)
                            if result is True:
                                if not self.wait_until_not_expired(
                                        sb, server_id):
                                    self.send_tg(
                                        "⚠️", "Renewal successful but status not updated",
                                        user, server_id, "offline", expiry_str,
                                        "Unable to start, please try again later",
                                        screenshot=self.shot(
                                            sb, f"start_fail_{idx}.png"))
                                    continue
                                ok, final = self.ui_start_server(
                                    sb, server_id, idx)
                                self.send_tg(
                                    "✅" if ok else "⚠️",
                                    "Renewal and startup successful" if ok else "Renewal successful, startup unconfirmed",
                                    user, server_id,
                                    f"offline -> {final}",
                                    f"{expiry_str} -> {new_time}",
                                    screenshot=self.shot(sb, f"ok_{idx}.png"))
                            elif result == "cooldown":
                                self.send_tg("⏳", "Cooling down after renewal", user,
                                             server_id, "offline", expiry_str,
                                             screenshot=self.shot(
                                                 sb, f"cooldown_{idx}.png"))
                            else:
                                self.send_tg("❌", "Renewal failed", user,
                                             server_id, "offline", expiry_str,
                                             screenshot=self.shot(
                                                 sb, f"extend_fail_{idx}.png"))
                        else:
                            if expired:
                                self.send_tg(
                                    "🚫", "Action unavailable", user, server_id,
                                    state, expiry_str,
                                    "Server expired and is in cooldown",
                                    screenshot=self.shot(
                                        sb, f"expired_cooldown_{idx}.png"))
                            else:
                                self.log("🔴 Offline and in cooldown, start directly via UI")
                                ok, final = self.ui_start_server(
                                    sb, server_id, idx)
                                self.send_tg(
                                    "✅" if ok else "❌",
                                    "Startup successful" if ok else "Startup failed",
                                    user, server_id,
                                    f"offline -> {final}", expiry_str,
                                    screenshot=self.shot(
                                        sb,
                                        f"{'started' if ok else 'start_fail'}"
                                        f"_{idx}.png"))
                        continue

                    # ===== Running state handling =====
                    if not can_extend:
                        extra = "Server expired but is in cooldown" if expired else ""
                        self.log(f"⏳ In cooldown ({cooldown_min} minutes)")
                        self.send_tg("⏳", "In cooldown", user, server_id,
                                     state, expiry_str, extra,
                                     screenshot=self.shot(
                                         sb, f"cooldown_{idx}.png"))
                        continue

                    self.log("✅ Extendable, performing renewal")
                    ready = self.navigate_to_panel(sb, server_id)
                    if not ready:
                        self.send_tg("❌", "Panel load failed", user, server_id,
                                     state, expiry_str,
                                     screenshot=self.shot(
                                         sb, f"panel_fail_{idx}.png"))
                        continue
                    if not self.click_renew_menu(sb, server_id, idx):
                        self.send_tg("❌", "Renew menu failed", user, server_id,
                                     state, expiry_str,
                                     screenshot=self.shot(
                                         sb, f"renew_fail_{idx}.png"))
                        continue
                    result, new_time = self.try_extend_and_verify(
                        sb, server_id, expired_time)
                    if result is True:
                        self.send_tg("✅", "Renewal successful", user, server_id,
                                     state, f"{expiry_str} -> {new_time}",
                                     screenshot=self.shot(sb, f"ok_{idx}.png"))
                    elif result == "cooldown":
                        self.send_tg("⏳", "Cooling down after renewal", user, server_id,
                                     state, expiry_str,
                                     screenshot=self.shot(
                                         sb, f"cooldown_{idx}.png"))
                    else:
                        self.send_tg("❌", "Renewal failed", user, server_id,
                                     state, expiry_str,
                                     screenshot=self.shot(
                                         sb, f"extend_fail_{idx}.png"))

                except Exception as e:
                    self.log(f"❌ Exception: {e}")
                    try:
                        self.send_tg("❌", "Exception", user, "Unknown",
                                     "Unknown", str(e),
                                     screenshot=self.shot(
                                         sb, f"error_{idx}.png"))
                    except Exception:
                        self.send_tg("❌", "Exception", user, "Unknown",
                                     "Unknown", str(e))

        self.log("✅ All accounts processed")


if __name__ == "__main__":
    BytenutRenewal().run()
