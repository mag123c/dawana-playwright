import asyncio
from datetime import datetime
from typing import Optional, List
from urllib.parse import urlencode

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from src.service.reveiw_batch_collector import collect_reviews_concurrently
from src.parser.asynchronous.product_parser import ProductAsyncParser
from src.infra.asynchronous.dawana_additional_fetcher import DanawaAdditionalAsyncFetcher
from src.service.coupang_async_service import CoupangAsyncService
from src.domain.equipment import Equipment

class DanawaAsyncScraper:
    def __init__(
        self,
        group_code: str,
        category_code: str,
        referer_code: str,
        sub_category: str,
        depth: str = "3",
        end_page: int = 100,
        base_dir: Optional[str] = None
    ):
        self.group_code = group_code
        self.category_code = category_code
        self.referer_code = referer_code
        self.sub_category = sub_category
        self.depth = depth
        self.end_page = end_page
        self.base_dir = base_dir or f"danawa_output"

    async def scrape(self) -> List[Equipment]:
        url = "https://prod.danawa.com/list/ajax/getProductList.ajax.php"
        all_results: List[Equipment] = []
        coupang_service = CoupangAsyncService(max_concurrency=3)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            fetcher = DanawaAdditionalAsyncFetcher(page, self.referer_code)

            try:
                for page_num in range(1, self.end_page + 1):
                    print(f"📄 페이지 {page_num} 수집 중…")

                    # Danawa 상품 리스트 요청
                    params = {
                        "btnAllOptUse": "false",
                        "page": str(page_num),
                        "listCategoryCode": self.category_code,
                        "categoryCode": self.category_code,
                        "viewMethod": "LIST",
                        "sortMethod": "BoardCount",
                        "listCount": "90",
                        "group": self.group_code,
                        "depth": self.depth,
                    }
                    response = await page.request.post(
                        url,
                        data=urlencode(params),
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Referer": f"https://prod.danawa.com/list/?cate={self.referer_code}",
                            "X-Requested-With": "XMLHttpRequest",
                        },
                        timeout=10000,
                    )
                    if response.status != 200:
                        print(f"❗ 페이지 {page_num} 요청 실패: status {response.status}")
                        break

                    soup = BeautifulSoup(await response.text(), "html.parser")
                    items = soup.select(".prod_item")
                    if not items:
                        print(f"❗ 페이지 {page_num}에서 항목 없음. 종료")
                        break

                    # 1) 파서로 Equipment 생성
                    equipment_list: List[Equipment] = []
                    product_ids: List[str] = []
                    for item in items:
                        try:
                            eq = ProductAsyncParser.parse_product_item(item, self.sub_category)
                            equipment_list.append(eq)
                            pid = eq.id.replace("productItem", "")
                            product_ids.append(pid)
                        except Exception as e:
                            print(f"⚠️ 파싱 오류: {e}")

                    # 2) 리뷰 메타데이터 추가
                    review_data = await fetcher.fetch(product_ids, self.group_code)
                    for eq in equipment_list:
                        pid = eq.id.replace("productItem", "")
                        info = review_data.get(pid, {})
                        eq.review_count = info.get("review_count", 0)
                        eq.score_count = info.get("score_count")

                    # 3) 리뷰 본문 병렬 수집
                    review_targets = [e for e in equipment_list if (e.review_count or 0) > 0]
                    if review_targets:
                        review_results = await collect_reviews_concurrently(
                            product_list=review_targets,
                            sub_category=self.sub_category,
                            base_dir=self.base_dir,
                        )
                        # 리뷰를 라벨링 데이터에 추가
                        # for eq in equipment_list:
                        #     pid = eq.id.replace("productItem", "")
                        #     eq.reviews = review_results.get(pid, [])

                        # 4) 페이지별 쿠팡 URL 병렬 매칭
                        equipment_page = await coupang_service.attach_urls(equipment_list)

                        # 5) 결과 누적
                        all_results.extend(equipment_page)

            finally:
                await page.close()
                await context.close()
                await browser.close()

        return all_results