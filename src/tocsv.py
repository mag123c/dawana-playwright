import os
import json
import csv
from datetime import datetime
from dataclasses import fields
from src.domain.equipment_spec import EquipmentSpecs

# 라벨 매핑 (한글 헤더)
spec_label_map = {
    "size": "크기",
    "capacity": "용량",
    "weight": "무게",
    "voltage": "전압",
    "features": "기능",
    "temperature_range": "온도 범위",
    "power_consumption": "소비전력",
    "description": "기타 설명",
    "material": "재질",
    "color": "색상",
    "usage": "용도",
    "insulation": "보냉효력",
    "inner_volume": "내부용량",
    "extra": "기타",
    "has_wheel": "바퀴",
    "has_drain": "물배출구",
    "has_table": "테이블",
    "has_inner_basket": "내부수납",
    "has_lid_open": "뚜껑개폐",
    "has_lid_cup": "뚜껑컵",
    "has_shoulder_strap": "어깨끈",
    "has_smartphone_connect": "스마트폰연동",
    "has_movable_wheel": "이동식바퀴",
    "has_handle": "손잡이",
    "has_charging_port": "충전포트",
    "has_temp_display": "온도표시",
    "has_inner_led": "내부LED",
    "has_cup_holder": "컵홀더",
}

# EquipmentSpecs 클래스의 필드 이름 리스트
def get_spec_fields_from_model() -> list[str]:
    return [f.name for f in fields(EquipmentSpecs)]

# 현재 파일에서 실제 값이 존재하는 spec 필드만 추출
def collect_effective_spec_keys(items: list[dict], all_spec_keys: list[str]) -> list[str]:
    effective = []
    for key in all_spec_keys:
        if any(item.get("specs", {}).get(key) not in (None, "", [], {}, "null") for item in items):
            effective.append(key)
    return effective

# JSON 하나를 CSV로 변환
def convert_json_to_csv(json_path: str):
    csv_path = json_path.replace(".json", ".csv")

    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    spec_keys_from_model = get_spec_fields_from_model()
    used_spec_keys = collect_effective_spec_keys(items, spec_keys_from_model)

    base_fields = [
        ("id", "제품 ID"),
        ("name", "제품명"),
        ("main_category", "메인카테고리"),
        ("sub_category", "서브카테고리"),
        ("price", "가격"),
        ("maker", "제조사"),
        ("registered_date", "등록일"),
        ("review_count", "리뷰 수"),
        ("score_count", "평점"),
        ("detail_url", "상세 페이지"),
        ("image_url", "이미지 URL"),
        ("raw_specs", "원시 스펙 정보"),
    ]

    spec_fields = [(key, spec_label_map.get(key, key)) for key in used_spec_keys]
    all_fields = base_fields + spec_fields
    field_labels = [label for _, label in all_fields]

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=field_labels)
        writer.writeheader()

        for item in items:
            row = {}
            for key, label in base_fields:
                row[label] = item.get(key, "")

            specs = item.get("specs", {})
            for key, label in spec_fields:
                row[label] = specs.get(key, "")

            writer.writerow(row)

    print(f"✅ 변환 완료: {csv_path}")

# 전체 디렉토리 순회
def main():
    today_str = datetime.now().strftime("%Y%m%d")
    base_dir = f"danawa_{today_str}"

    if not os.path.exists(base_dir):
        print(f"❗ 디렉토리 없음: {base_dir}")
        return

    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".json"):
                full_path = os.path.join(root, file)
                convert_json_to_csv(full_path)

if __name__ == "__main__":
    main()
