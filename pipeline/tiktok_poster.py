"""TikTok auto-posting via browser automation (Playwright).

NOT an official API — drives the TikTok web upload UI directly.
This violates TikTok's Terms of Service (anti-automation clause) and risks
account suspension. Used here at the user's explicit request. Selectors
are based on the TikTok Studio upload page as of 2026 and WILL break when
TikTok changes its UI — if posting silently fails, the page markup likely
changed and selectors below need updating.
"""
import os
import time

_SESSION_FILE = os.path.join('data', 'tiktok_session.json')
_UPLOAD_URL   = 'https://www.tiktok.com/tiktokstudio/upload?from=upload'


def has_session() -> bool:
    return os.path.exists(_SESSION_FILE)


def login_setup() -> None:
    """Opens a real browser window for the user to log in manually (handles
    captcha/2FA), then saves the session (cookies + storage) for reuse."""
    from playwright.sync_api import sync_playwright

    os.makedirs('data', exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto('https://www.tiktok.com/login')
        print('Log in to TikTok in the opened browser window.')
        print('Once you reach your feed/profile (fully logged in), press Enter here...')
        input()
        context.storage_state(path=_SESSION_FILE)
        browser.close()
    print(f'Session saved to {_SESSION_FILE}')


def post(video_path: str, title: str, log) -> None:
    if not has_session():
        raise RuntimeError(
            'No saved TikTok session. Run `python -c "from pipeline import '
            'tiktok_poster; tiktok_poster.login_setup()"` once to log in manually.'
        )

    from playwright.sync_api import sync_playwright

    abs_path = os.path.abspath(video_path)
    log('  -> Launching browser for TikTok upload...', 'post')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=_SESSION_FILE)
        page = context.new_page()
        try:
            page.goto(_UPLOAD_URL, timeout=60000)

            log('  -> Uploading video file...', 'post')
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(abs_path)

            # TikTok needs time to transcode/preview before the caption box
            # and Post button become interactable.
            page.wait_for_selector('[data-e2e="post-button"], [data-e2e="post_video_button"]',
                                    timeout=180000)
            time.sleep(2)

            log('  -> Setting caption...', 'post')
            caption_box = page.locator('[data-e2e="creator-tab"] [contenteditable="true"]').first
            if caption_box.count() == 0:
                caption_box = page.locator('[contenteditable="true"]').first
            caption_box.click()
            page.keyboard.press('Control+A')
            page.keyboard.type(title[:2200])

            log('  -> Publishing...', 'post')
            post_btn = page.locator('[data-e2e="post-button"], [data-e2e="post_video_button"]').first
            post_btn.click()

            page.wait_for_selector('text=/Your video is being uploaded|Manage your post/i',
                                    timeout=60000)
            log('  -> TikTok upload confirmed', 'post')
        except Exception as exc:
            raise RuntimeError(f'TikTok browser-automation post failed: {exc}')
        finally:
            context.storage_state(path=_SESSION_FILE)
            browser.close()
