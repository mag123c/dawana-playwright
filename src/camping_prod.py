import os
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
from pathlib import Path

def scrape_products(group_code: str, cate_name: str, category_code: str, referer_cate_code: str, depth: str = "2", end_page: int = 100, output_dir: str = "."):
    url = "https://prod.danawa.com/list/ajax/getProductList.ajax.php"
    all_items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for page_num in range(1, end_page + 1):
            print(f"📄 페이지 {page_num} 수집 중...")

            params = {
                "btnAllOptUse": "false",
                "priceRangeMinPrice": "",
                "priceRangeMaxPrice": "",
                "page": str(page_num),
                "listCategoryCode": category_code,
                "categoryCode": category_code,
                "viewMethod": "LIST",
                "sortMethod": "BEST",
                "listCount": "90",
                "group": group_code,
                "depth": depth,
            }

            form_data = urlencode(params)

            response = page.request.post(
                url,
                data=form_data,
                headers={
                    "Accept": "text/html, */*; q=0.01",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Connection": "keep-alive",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Host": "prod.danawa.com",
                    "Origin": "https://prod.danawa.com",
                    "Referer": f"https://prod.danawa.com/list/?cate={referer_cate_code}",
                    "Sec-Ch-Ua": "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Google Chrome\";v=\"134\"",
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": "\"Windows\"",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    "X-Requested-With": "XMLHttpRequest"
                }
            )
            html = response.text()
            soup = BeautifulSoup(html, "html.parser")

            items = []
            for item in soup.select(".prod_item"):
                try:
                    if not item.get("id"):
                        continue

                    image_tag = item.select_one(".thumb_image img")
                    image_url = image_tag.get("src") or image_tag.get("data-original")
                    if image_url and not image_url.startswith("http"):
                        image_url = "https:" + image_url

                    options = item.select(".spec_list a, .spec_list span, .spec_list div")
                    option_texts = [opt.get_text(strip=True) for opt in options]

                    items.append({
                        "id": item.get("id"),
                        "category_code": item.select_one("input[id^=productItem_categoryInfo]").get("value", ""),
                        "category": cate_name,
                        "name": item.select_one(".prod_name a").get_text(strip=True),
                        "url": item.select_one(".prod_name a").get("href"),
                        "image": image_url,
                        "spec": item.select_one(".spec_list").get_text(" / ", strip=True) if item.select_one(".spec_list") else "",
                        "price": item.select_one(".price_sect strong").get_text(strip=True),
                        "date": item.select_one(".meta_item.mt_date dd").get_text(strip=True) if item.select_one(".meta_item.mt_date dd") else None,
                        "option": option_texts,
                        "maker": item.select_one(".price_sect button[data-maker-name]").get("data-maker-name", "") if item.select_one(".price_sect button[data-maker-name]") else None,
                    })
                except Exception as e:
                    print(f"⚠️ 파싱 실패: {e}")

            if not items:
                print("🛑 더 이상 상품이 없습니다. 중단합니다.")
                break

            all_items.extend(items)

        browser.close()

    # 저장
    safe_name = "".join(c for c in cate_name if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
    filename = f"products_{safe_name}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)

    print(f"✅ {cate_name} → {len(all_items)}개 저장 완료: {filepath}")
    return all_items


if __name__ == "__main__":
    group_code = "13"
    cate_name = "텐트"
    cate_code = "437"
    ref_cate_code = "132437"
    end_page = 100

    scrape_products(group_code, cate_name, cate_code, ref_cate_code, end_page=end_page)
