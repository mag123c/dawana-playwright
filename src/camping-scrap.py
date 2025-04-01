# camping-run.py
from camping_category import get_camping_categories
from camping_prod import scrape_products
from datetime import datetime
import os


def run_all():
    today_str = datetime.now().strftime("%Y%m%d")
    root_dir = f"dawana_{today_str}"
    os.makedirs(root_dir, exist_ok=True)

    result = get_camping_categories()
    categories = result["categories"]

    for cate in categories:
        children = cate.get("children", [])

        if not children:
            print(f"[2뎁스 단독] {cate['name']} / {cate['cate']}")
            sub_dir = os.path.join(root_dir, cate["name"])
            os.makedirs(sub_dir, exist_ok=True)

            scrape_products(
                group_code=cate.get("group"),
                cate_name=cate["name"],
                category_code=cate.get("category_code"),
                referer_cate_code=cate["cate"],
                depth=cate.get("depth", "2"),
                output_dir=sub_dir
            )

        else:
            for sub in children:
                print(f"[3뎁스] {sub['name']} / {sub['cate']}")
                sub_dir = os.path.join(root_dir, cate["name"])
                os.makedirs(sub_dir, exist_ok=True)

                scrape_products(
                    group_code=sub.get("group"),
                    cate_name=sub["name"],
                    category_code=sub.get("category_code"),
                    referer_cate_code=sub["cate"],
                    depth=sub.get("depth", "3"),
                    output_dir=sub_dir
                )

    print(f"\n✅ 모든 카테고리 수집 및 저장 완료: {root_dir}")

if __name__ == "__main__":
    run_all()
