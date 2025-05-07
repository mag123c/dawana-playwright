import asyncio
import re
from urllib.parse import quote
from typing import List

from src.infra.asynchronous.coupang_fetch_and_match import CoupangHtmlFetcher
from src.parser.asynchronous.coupang_product_parser import CoupangProductParser
from src.service.coupang_product_matcher import CoupangProductMatcher
from src.domain.equipment import Equipment

class CoupangAsyncService:
    def __init__(self, max_concurrency: int = 3):
        self._sem = asyncio.Semaphore(max_concurrency)

    async def _attach_url(self, eq: Equipment) -> Equipment:
        async with self._sem:
            # # 1) 색상 제거
            # color = eq.specs.color
            # name = eq.name.replace(color, "").strip() if color else eq.name

            # 2) HTML fetch & 파싱
            html = await CoupangHtmlFetcher(quote(eq.name)).fetch_html()
            products = CoupangProductParser.parse_products(html)
            if not products:
                print("❌ 실제 상품이 하나도 없습니다.")
                return

            # 3) 매칭
            best = CoupangProductMatcher(target_name=eq.name).find_best_match(products)
            if not best:
                print("❌ 유사도가 기준 이하인 상품만 있습니다.")
                return
            
            print(f"✅ {best.name} | {best.price}원 | 리뷰{best.review_count} | 평점{best.rating}")
            eq.coupangURL = (
                f"https://www.coupang.com/vp/products/{best.product_id}"
                f"?itemId={best.item_id}&vendorItemId={best.vendor_item_id}"
            )
    
        return eq

    async def attach_urls(self, equipments: List[Equipment]) -> List[Equipment]:
        tasks = [self._attach_url(eq) for eq in equipments]
        return await asyncio.gather(*tasks)