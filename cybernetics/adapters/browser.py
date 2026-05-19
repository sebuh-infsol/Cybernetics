"""Browser DevTools adapter via Playwright websocket CDP."""

import base64
from typing import Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from cybernetics.adapters.base import MCPAdapter
from cybernetics.config.settings import settings
from cybernetics.circuit.breaker import circuit
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.adapters.browser")


class BrowserAdapter(MCPAdapter):
    name = "browser"
    description = "Browser DevTools — navigate, evaluate JS, screenshot, network, full CDP via Playwright"

    def __init__(self):
        super().__init__()
        self.cdp_url = f"http://{settings.browser_cdp_host}:{settings.browser_cdp_port}"
        self._playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None
        self.register_tool("browser_navigate", "Navigate to a URL", {"url": {"type": "string"}}, ["url"], self._navigate)
        self.register_tool("browser_evaluate", "Evaluate JavaScript", {"expression": {"type": "string"}}, ["expression"], self._evaluate)
        self.register_tool("browser_screenshot", "Take a screenshot", {"format": {"type": "string"}, "full_page": {"type": "boolean"}}, [], self._screenshot)
        self.register_tool("browser_get_network_log", "Get network request log", {}, [], self._get_network)
        self.register_tool("browser_clear_cache", "Clear browser cache", {}, [], self._clear_cache)
        self.register_tool("browser_get_console_log", "Get console logs", {}, [], self._get_console)

    async def _ensure_browser(self):
        if self._browser:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(self.cdp_url)
        self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
        logger.info("browser_connected", cdp=self.cdp_url)

    @circuit("browser", failure_threshold=3, recovery_timeout=30)
    async def _navigate(self, url: str) -> Dict[str, Any]:
        await self._ensure_browser()
        page: Page = await self._context.new_page()
        resp = await page.goto(url, wait_until="networkidle", timeout=30000)
        status = resp.status if resp else 0
        title = await page.title()
        return {"url": url, "status": status, "title": title, "page_id": str(id(page))}

    @circuit("browser", failure_threshold=3, recovery_timeout=30)
    async def _evaluate(self, expression: str) -> Dict[str, Any]:
        await self._ensure_browser()
        page: Page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        result = await page.evaluate(expression)
        return {"result": result}

    @circuit("browser", failure_threshold=3, recovery_timeout=30)
    async def _screenshot(self, format: str = "png", full_page: bool = False) -> Dict[str, Any]:
        await self._ensure_browser()
        page: Page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        path = f"/tmp/screenshot.{format}"
        await page.screenshot(path=path, full_page=full_page, type=format)
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return {"format": format, "full_page": full_page, "base64": b64}

    @circuit("browser", failure_threshold=3, recovery_timeout=30)
    async def _get_network(self) -> List[Dict[str, Any]]:
        await self._ensure_browser()
        page: Page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        # Playwright route monitoring
        logs = []
        async def handle_route(route, request):
            logs.append({
                "url": request.url,
                "method": request.method,
                "headers": dict(request.headers),
            })
            await route.continue_()
        await page.route("**/*", handle_route)
        return logs

    @circuit("browser", failure_threshold=3, recovery_timeout=30)
    async def _clear_cache(self) -> None:
        await self._ensure_browser()
        await self._context.clear_cookies()
        # Clear local/session storage on all pages
        for page in self._context.pages:
            await page.evaluate("localStorage.clear(); sessionStorage.clear();")

    @circuit("browser", failure_threshold=3, recovery_timeout=30)
    async def _get_console(self) -> List[Dict[str, Any]]:
        await self._ensure_browser()
        page: Page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        logs = []
        page.on("console", lambda msg: logs.append({"type": msg.type, "text": msg.text}))
        return logs

    async def health(self) -> Dict[str, Any]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(f"{self.cdp_url}/json/version")
                r.raise_for_status()
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
