import os
import json
import time
import random
from typing import List, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page
from src.storage.file_storage import save_as_json

class DanawaReviewParser:
    BASE_REVIEW_URL = "https://prod.danawa.com/info/dpg/ajax/companyProductReview.ajax.php"

    def __init__(self, page: Page):
        self.page = page

    def get_reviews(self, product_code: str, limit: int = 100, max_pages: int = 100) -> List[dict]:
        reviews = []

        for page_num in range(1, max_pages + 1):
            print(f"📝 productItem{product_code}의 {page_num} 페이지 리뷰 수집중")

            t = f"{random.random()}"
            url = (
                f"{self.BASE_REVIEW_URL}?prodCode={product_code}"
                f"&page={page_num}&limit={limit}&score=0&t={t}"
            )
            cookies = await self.page.context.cookies()
            cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{url}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                "X-Requested-With": "XMLHttpRequest",
                "Cookie": cookie_header
            }


            try:
                response = self.page.request.get(url, timeout=30000)
                html = response.text()
                soup = BeautifulSoup(html, "html.parser")

                review_items = soup.select("li.danawa-prodBlog-companyReview-clazz-more")
                if not review_items:
                    break

                for li in review_items:
                    review = self._parse_review_item(li)
                    reviews.append(review)

                time.sleep(random.uniform(1, 3)) 

            except Exception as e:
                print(f"⚠️ 요청 실패 URL: {url}")
                print(f"❗ 페이지 {page_num} 요청 실패: {e}")
                continue 

        return reviews


    def _parse_review_item(self, li) -> dict:
        score_raw = li.select_one(".star_mask")
        score_style = score_raw.get("style", "") if score_raw else ""
        score = int(score_style.replace("width:", "").replace("%", "").strip()) // 20 if score_style else None

        seller = None
        mall_elem = li.select_one(".mall")
        if mall_elem:
            img_tag = mall_elem.select_one("img[alt]")
            if img_tag and img_tag.get("alt"):
                seller = img_tag["alt"].strip()
            else:
                span = mall_elem.select_one("span")
                if span:
                    seller = span.get_text(strip=True)

        return {
            "score": score,
            "date": li.select_one(".date").text.strip() if li.select_one(".date") else None,
            "name": li.select_one(".name").text.strip() if li.select_one(".name") else None,
            "title": li.select_one(".tit").text.strip() if li.select_one(".tit") else None,
            "content": li.select_one(".atc").text.strip() if li.select_one(".atc") else None,
            "seller": seller
        }



def fetch_and_save_reviews(product_key: str, category: str, base_dir: Optional[str] = None):
    base_dir = base_dir or f"danawa_{time.strftime('%Y%m%d')}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        parser = DanawaReviewParser(page)
        reviews = parser.get_reviews(product_key)

        save_as_json(
            data={"no": product_key, "reviews": reviews},
            category_name=category,
            file_prefix=f"{product_key}-review"
        )

        browser.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", required=True, help="productItem 숫자 ID (ex: 6062612)")
    parser.add_argument("--category", required=True, help="카테고리 이름 (ex: 아이스박스)")
    parser.add_argument("--base_dir", default=None, help="저장할 최상위 디렉토리 (기본: 오늘 날짜)")
    args = parser.parse_args()

    fetch_and_save_reviews(args.product, args.category, args.base_dir)
