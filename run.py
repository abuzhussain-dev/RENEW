import time

import main

_orig_fetch = main.BytenutRenewal.fetch_api


def _fetch_api(self, sb, url, method="GET", referer=None):
    """fetch_api with a longer script timeout and retries (for slow proxies)."""
    try:
        sb.driver.set_script_timeout(90)
    except Exception:
        pass
    for attempt in range(1, 4):
        result = _orig_fetch(self, sb, url, method, referer)
        if result is not None:
            return result
        self.log(f"API request failed (attempt {attempt}/3), retrying...")
        time.sleep(5)
    return None


main.BytenutRenewal.fetch_api = _fetch_api

if __name__ == "__main__":
    main.BytenutRenewal().run()
