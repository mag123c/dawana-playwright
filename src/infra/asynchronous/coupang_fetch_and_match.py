import asyncio
from urllib.parse import quote
from playwright_stealth import stealth_async
from playwright.async_api import async_playwright
from src.parser.asynchronous.coupang_product_parser import CoupangProductParser
from src.service.coupang_product_matcher import CoupangProductMatcher
# from src.service.affiliate_link_generator import AffiliateLinkGenerator


class CoupangHtmlFetcher:
    BASE_URL = "https://www.coupang.com/np/search?q="

    def __init__(self, keyword: str):
        self.keyword = keyword

    async def fetch_html(self) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--disable-web-security',
                    '--disable-http2',                                    # HTTP/2 비활성화
                    '--disable-quic',                                     # QUIC 비활성화
                    '--disable-features=NetworkService,NetworkServiceInProcess',  
                    '--disable-blink-features=AutomationControlled',      # 자동화 탐지 차단
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--lang=ko'
                ]
            )

            context = await browser.new_context(
                locale="ko-KR",
                timezone_id="Asia/Seoul",
                permissions=["geolocation"],
                geolocation={"latitude": 37.5665, "longitude": 126.978},
                ignore_https_errors=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept": "*/*",
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Referer": "https://www.coupang.com/",
                }
            )

            await context.add_cookies([
                {"name": "PCID", "value": "17418684436306169692218", "domain": ".coupang.com", "path": "/"},
                {"name": "MARKETID", "value": "17418684436306169692218", "domain": ".coupang.com", "path": "/"},
                {"name": "x-coupang-accept-language", "value": "ko-KR", "domain": ".coupang.com", "path": "/"},
                {"name": "_fbp", "value": "fb.1.1741868445075.25325014701425710", "domain": ".coupang.com", "path": "/"},
                {"name": "delivery_toggle", "value": "false", "domain": ".coupang.com", "path": "/"},
                {"name": "sid", "value": "672c99cebb674a31b5d29dc6bf026cccfd0cf26d", "domain": ".coupang.com", "path": "/"},
                {"name": "x-coupang-target-market", "value": "KR", "domain": ".coupang.com", "path": "/"},
            ])

            page = await context.new_page()
            
            await stealth_async(page)    # 스텔스 플러그인 적용

            url = f"{self.BASE_URL}{self.keyword}"
            print(f"🔍 요청 URL: {url}")

            try:
                response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                if not response or response.status != 200:
                    print(f"❌ [GOTO 실패] URL: {url} | 응답 없음 또는 상태코드 {response.status}")
                    return ""

                # 페이지 로딩 대기
                await page.wait_for_selector('ul.search-product-list', timeout=60000)

                html = await page.content()
                await browser.close()
                return html   

            except PlaywrightTimeoutError:
                print(f"⏰ [타임아웃] URL: {url} | 60초 이내 응답 없음. 다음 키워드로 스킵합니다.")
                return ""

            except Exception as e:
                print(f"🔥 [예외 발생] {type(e).__name__}: {e}")
                return ""



async def main():
    keyword = "올리빙 도트 아이스박스 21L 민트"
    html = await CoupangHtmlFetcher(quote(keyword)).fetch_html()

    products = CoupangProductParser.parse_products(html)
    if not products:
        print("❌ 실제 상품이 하나도 없습니다.")
        return

    matcher = CoupangProductMatcher(target_name=keyword)
    best = matcher.find_best_match(products)
    if not best:
        print("❌ 유사도가 기준 이하인 상품만 있습니다.")
        return

    print(f"🎯 매칭 상품: {best}")
    print(f"https://www.coupang.com/vp/products/{best.product_id}?itemId={best.item_id}&vendorItemId={best.vendor_item_id}")

    # gen = AffiliateLinkGenerator("YOUR_AFFILIATE_ID")
    # link = gen.generate(best)
    # print(f"✅ 매칭된 상품: {best}")
    # print(f"🔗 어필리에이트 링크: {link}")


if __name__ == "__main__":
    asyncio.run(main())