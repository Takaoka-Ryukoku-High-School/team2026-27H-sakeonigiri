import csv
import io
import json
import math
import re
import unicodedata
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import flet as ft


PAPER = "#F6F5EF"
MUTED = "#77807B"
GSI_ADDRESS_API = "https://msearch.gsi.go.jp/address-search/AddressSearch"
GSI_SHELTER_CSV = "https://hinanmap.gsi.go.jp/hinanjocp/defaultFtpData/csv/16000_1.csv"
GSI_SHELTER_SOURCE = "https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html"
MUNICIPALITIES = [
    "富山市",
    "高岡市",
    "魚津市",
    "氷見市",
    "滑川市",
    "黒部市",
    "砺波市",
    "小矢部市",
    "南砺市",
    "射水市",
    "舟橋村",
    "上市町",
    "立山町",
    "入善町",
    "朝日町",
]


class AddressNotFoundError(ValueError):
    pass


def normalize_address_part(value):
    normalized = unicodedata.normalize("NFKC", value)
    for marker in ("丁目", "番地", "番", "号"):
        normalized = normalized.replace(marker, "")
    digits = {"〇": "0", "零": "0", "一": "1", "二": "2", "三": "3",
              "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}

    def normalize_japanese_number(match):
        number = match.group()
        if not any(unit in number for unit in "十百千"):
            return "".join(digits.get(character, character) for character in number)
        total = 0
        section = 0
        digit = 0
        for character in number:
            if character in digits:
                digit = int(digits[character])
            else:
                unit = {"十": 10, "百": 100, "千": 1000}[character]
                section += (digit or 1) * unit
                digit = 0
        return str(total + section + digit)

    normalized = re.sub(r"[〇零一二三四五六七八九十百千]+", normalize_japanese_number, normalized)
    return "".join(character for character in normalized if character.isalnum())


def distance_km(latitude_a, longitude_a, latitude_b, longitude_b):
    earth_radius_km = 6371
    latitude_delta = math.radians(latitude_b - latitude_a)
    longitude_delta = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(math.radians(latitude_a))
        * math.cos(math.radians(latitude_b))
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_km * math.asin(math.sqrt(haversine))


def find_nearest_shelters(municipality, street_address):
    full_address = f"富山県{municipality}{street_address}"
    geocoder_url = f"{GSI_ADDRESS_API}?{urlencode({'q': full_address})}"
    with urlopen(geocoder_url, timeout=15) as response:
        features = json.loads(response.read().decode("utf-8"))
    if not isinstance(features, list):
        raise ValueError("The address search service returned an invalid response.")

    address_prefix = f"富山県{municipality}"
    normalized_address = normalize_address_part(street_address)
    geocoded_feature = None
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            continue
        title = properties.get("title", "")
        if isinstance(title, str) and title.startswith(address_prefix):
            candidate_address = normalize_address_part(title[len(address_prefix) :])
            if candidate_address and (
                normalized_address in candidate_address
                or candidate_address in normalized_address
            ):
                geocoded_feature = feature
                break
    if geocoded_feature is None:
        raise AddressNotFoundError

    try:
        geometry = geocoded_feature["geometry"]
        if not isinstance(geometry, dict):
            raise ValueError("The address search service returned invalid coordinates.")
        longitude, latitude = geometry["coordinates"]
        longitude = float(longitude)
        latitude = float(latitude)
    except (IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError("The address search service returned invalid coordinates.") from error

    with urlopen(GSI_SHELTER_CSV, timeout=20) as response:
        shelters = csv.DictReader(io.TextIOWrapper(response, encoding="utf-8-sig", newline=""))
        results = []
        for shelter in shelters:
            shelter_name = shelter.get("施設・場所名", "").strip()
            shelter_address = shelter.get("住所", "").strip()
            if not shelter_address.startswith("富山県") or not shelter_name:
                continue
            try:
                shelter_latitude = float(shelter["緯度"])
                shelter_longitude = float(shelter["経度"])
            except (KeyError, ValueError):
                continue
            if not math.isfinite(shelter_latitude) or not math.isfinite(shelter_longitude):
                continue
            results.append(
                {
                    "name": shelter_name,
                    "address": shelter_address,
                    "latitude": shelter_latitude,
                    "longitude": shelter_longitude,
                    "distance_km": distance_km(
                        latitude, longitude, shelter_latitude, shelter_longitude
                    ),
                }
            )

    if not results:
        raise ValueError("No shelter coordinates were found in the official data.")
    return sorted(results, key=lambda shelter: shelter["distance_km"])[:3]


def main(page: ft.Page):
    page.title = "Daily Note"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = PAPER
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    current_language = "ja"
    translations = {
        "ja": {
            "app_title": "Daily Note",
            "brand_mark": "日",
            "language_label": "言語",
            "language_tooltip": "表示言語",
            "text_size_label": "文字サイズ",
            "text_size_small": "小",
            "text_size_medium": "標準",
            "text_size_large": "大",
            "date_format": "%Y年%m月%d日",
            "address_title": "住所",
            "address_description": "富山県内の住所を入力してください。",
            "prefecture_label": "富山県",
            "municipality_label": "市町村",
            "municipality_hint": "市町村を選択",
            "street_address_label": "町名・番地",
            "street_address_hint": "例：新桜町7-38",
            "packing_title": "避難の持ち物リスト",
            "packing_items": [
                "飲料水",
                "非常食",
                "常備薬・救急用品",
                "懐中電灯・ラジオ",
                "携帯電話・充電器",
                "身分証・現金",
                "マスク・防寒用品",
            ],
            "privacy_note": "入力住所はこのアプリには保存されず、座標検索のため国土地理院の住所検索サービスに送信されます。",
            "search_button": "最寄りの避難所を検索",
            "searching": "検索中…",
            "address_required": "市町村と町名・番地を入力してください。",
            "address_not_found": "住所を確認できませんでした。選択した市町村内の住所を入力してください。",
            "search_failed": "避難所データを取得できませんでした。時間をおいて再度お試しください。",
            "shelter_title": "近くの指定避難所",
            "distance_label": "直線距離：約{distance:.1f} km",
            "map_button": "地理院地図で見る",
            "new_search_button": "別の住所で検索",
            "safety_note": "距離は直線距離です。避難所の開設状況は反映されません。また、公開データに未掲載の施設がある場合があります。災害時は自治体の避難情報と最新の指定状況を確認してください。",
            "source_label": "出典：国土地理院「指定避難所データ」",
        },
        "en": {
            "app_title": "Daily Note",
            "brand_mark": "D",
            "language_label": "Language",
            "language_tooltip": "Display language",
            "text_size_label": "Text size",
            "text_size_small": "Small",
            "text_size_medium": "Medium",
            "text_size_large": "Large",
            "date_format": "%b %d, %Y",
            "address_title": "Address",
            "address_description": "Enter an address in Toyama Prefecture.",
            "prefecture_label": "Toyama",
            "municipality_label": "Municipality",
            "municipality_hint": "Select a municipality",
            "street_address_label": "Street address",
            "street_address_hint": "e.g. 7-38 Shinsakuramachi",
            "packing_title": "Evacuation packing list",
            "packing_items": [
                "Drinking water",
                "Emergency food",
                "Medicine and first-aid supplies",
                "Flashlight and radio",
                "Mobile phone and charger",
                "ID and cash",
                "Masks and warm clothing",
            ],
            "privacy_note": "Your address is not saved by this app. It is sent to the Geospatial Information Authority of Japan address search service to find its coordinates.",
            "search_button": "Find nearby shelters",
            "searching": "Searching…",
            "address_required": "Select a municipality and enter a street address.",
            "address_not_found": "Address not found. Enter an address within the selected municipality.",
            "search_failed": "Could not retrieve shelter data. Please try again later.",
            "shelter_title": "Nearby designated shelters",
            "distance_label": "Straight-line distance: about {distance:.1f} km",
            "map_button": "View on GSI Maps",
            "new_search_button": "Search another address",
            "safety_note": "Distances are straight-line estimates; shelter opening status is not shown. Some facilities may not be included in the public data. During a disaster, check your municipality's evacuation information and current shelter designations.",
            "source_label": 'Source: Geospatial Information Authority of Japan, "Designated Evacuation Shelters"',
        },
        "zh": {
            "app_title": "每日记录",
            "brand_mark": "记",
            "language_label": "语言",
            "language_tooltip": "选择语言",
            "text_size_label": "文字大小",
            "text_size_small": "小",
            "text_size_medium": "标准",
            "text_size_large": "大",
            "date_format": "%Y年%m月%d日",
            "address_title": "地址",
            "address_description": "请输入富山县内的地址。",
            "prefecture_label": "富山县",
            "municipality_label": "市町村",
            "municipality_hint": "请选择市町村",
            "street_address_label": "町名、门牌号",
            "street_address_hint": "例如：新樱町7-38",
            "packing_title": "避难携带物品清单",
            "packing_items": [
                "饮用水",
                "应急食品",
                "常备药品和急救用品",
                "手电筒和收音机",
                "手机和充电器",
                "身份证件和现金",
                "口罩和保暖用品",
            ],
            "privacy_note": "本应用不会保存您输入的地址；为查询坐标，地址会发送至日本国土地理院的地址搜索服务。",
            "search_button": "查找最近的避难所",
            "searching": "搜索中…",
            "address_required": "请选择市町村并输入町名和门牌号。",
            "address_not_found": "未找到该地址。请输入所选市町村内的地址。",
            "search_failed": "无法获取避难所数据，请稍后重试。",
            "shelter_title": "附近的指定避难所",
            "distance_label": "直线距离：约 {distance:.1f} 公里",
            "map_button": "在国土地理院地图中查看",
            "new_search_button": "搜索其他地址",
            "safety_note": "距离为直线距离，未显示避难所开放状态。公开数据可能未收录部分设施。发生灾害时，请确认市町村的避难信息及最新指定情况。",
            "source_label": "来源：日本国土地理院“指定避难所数据”",
        },
    }

    def tr(key, **values):
        value = translations[current_language][key]
        return value.format(**values) if isinstance(value, str) else value

    def formatted_date():
        return date.today().strftime(tr("date_format"))

    page.title = tr("app_title")
    text_scale = 1.0
    base_text_sizes = {}

    def scaled_font_size(control, property_name, default_size):
        key = (id(control), property_name)
        if key not in base_text_sizes:
            value = getattr(control, property_name, None)
            if isinstance(value, ft.TextStyle):
                value = value.size
            base_text_sizes[key] = value or default_size
        return round(base_text_sizes[key] * text_scale)

    def apply_text_scale(control=None):
        if control is None:
            control = app_container
        if isinstance(control, ft.Text):
            key = (id(control), "size")
            if key not in base_text_sizes:
                base_text_sizes[key] = control.size
            base_size = base_text_sizes[key]
            control.size = round(base_size * text_scale) if base_size is not None else None
        elif isinstance(control, ft.TextField):
            control.text_size = scaled_font_size(control, "text_size", 16)
            control.label_style = ft.TextStyle(
                size=scaled_font_size(control, "label_style", 12)
            )
            control.hint_style = ft.TextStyle(
                size=scaled_font_size(control, "hint_style", 16)
            )
            control.helper_style = ft.TextStyle(
                size=scaled_font_size(control, "helper_style", 12)
            )
            control.error_style = ft.TextStyle(
                size=scaled_font_size(control, "error_style", 12)
            )
        elif isinstance(control, ft.Dropdown):
            control.text_size = scaled_font_size(control, "text_size", 16)
            control.text_style = ft.TextStyle(size=control.text_size)
            control.label_style = ft.TextStyle(
                size=scaled_font_size(control, "label_style", 12)
            )
            control.hint_style = ft.TextStyle(
                size=scaled_font_size(control, "hint_style", 16)
            )
            control.helper_style = ft.TextStyle(
                size=scaled_font_size(control, "helper_style", 12)
            )
            control.error_style = ft.TextStyle(
                size=scaled_font_size(control, "error_style", 12)
            )
        elif isinstance(control, ft.Checkbox):
            control.label_style = ft.TextStyle(
                size=scaled_font_size(control, "label_style", 14)
            )
        elif isinstance(control, (ft.FilledButton, ft.TextButton)):
            key = (id(control), "button_text")
            if key not in base_text_sizes:
                base_text_sizes[key] = 14
            control.style = ft.ButtonStyle(
                text_style=ft.TextStyle(
                    size=round(base_text_sizes[key] * text_scale)
                )
            )

        content = getattr(control, "content", None)
        if content is not None:
            apply_text_scale(content)
        for child in getattr(control, "controls", []) or []:
            apply_text_scale(child)

    def set_text_size(_event):
        nonlocal text_scale
        text_scale = {
            "small": 0.85,
            "medium": 1.0,
            "large": 1.20,
        }[text_size_selector.value or "medium"]
        apply_text_scale(app_container)
        if results_section.visible:
            render_results(found_shelters)
        page.update()

    def set_language(_event):
        nonlocal current_language
        current_language = language_selector.value or "ja"
        page.title = tr("app_title")
        brand_mark.value = tr("brand_mark")
        today.value = formatted_date()
        language_selector.label = tr("language_label")
        language_selector.tooltip = tr("language_tooltip")
        text_size_selector.label = tr("text_size_label")
        text_size_selector.options[0].text = tr("text_size_small")
        text_size_selector.options[1].text = tr("text_size_medium")
        text_size_selector.options[2].text = tr("text_size_large")
        address_title.value = tr("address_title")
        address_description.value = tr("address_description")
        municipality_selector.label = tr("municipality_label")
        municipality_selector.hint_text = tr("municipality_hint")
        street_address.label = tr("street_address_label")
        street_address.hint_text = tr("street_address_hint")
        packing_title.value = tr("packing_title")
        for checkbox, label in zip(packing_checkboxes, tr("packing_items")):
            checkbox.label = label
        privacy_note.value = tr("privacy_note")
        search_button.content = tr("search_button")
        if results_section.visible:
            render_results(found_shelters)
        page.update()

    brand_mark = ft.Text(tr("brand_mark"), color="white", size=15, weight=ft.FontWeight.BOLD)
    today = ft.Text(
        formatted_date(),
        size=12,
        color=MUTED,
    )
    language_selector = ft.Dropdown(
        label=tr("language_label"),
        value=current_language,
        options=[
            ft.DropdownOption(key="ja", text="日本語"),
            ft.DropdownOption(key="en", text="English"),
            ft.DropdownOption(key="zh", text="中文"),
        ],
        on_select=set_language,
        width=132,
        tooltip=tr("language_tooltip"),
    )
    text_size_selector = ft.Dropdown(
        label=tr("text_size_label"),
        value="medium",
        options=[
            ft.DropdownOption(key="small", text=tr("text_size_small")),
            ft.DropdownOption(key="medium", text=tr("text_size_medium")),
            ft.DropdownOption(key="large", text=tr("text_size_large")),
        ],
        on_select=set_text_size,
        width=112,
    )
    header = ft.Row(
        [
            ft.Row(
                [
                    ft.Container(
                        content=brand_mark,
                        width=28,
                        height=28,
                        bgcolor="#2E6654",
                        border_radius=14,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text("DAILY NOTE", size=12, color="#2E6654", weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            ft.Row([today, text_size_selector, language_selector], spacing=8),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    packing_title = ft.Text(tr("packing_title"), size=20, weight=ft.FontWeight.BOLD)
    packing_checkboxes = [
        ft.Checkbox(label=item)
        for item in tr("packing_items")
    ]
    packing_section = ft.Container(
        content=ft.Column(
            [
                packing_title,
                ft.Column(packing_checkboxes, spacing=2),
            ],
            spacing=8,
        ),
        padding=16,
        bgcolor="white",
        border_radius=12,
    )

    address_title = ft.Text(tr("address_title"), size=20, weight=ft.FontWeight.BOLD)
    address_description = ft.Text(tr("address_description"), size=14, color=MUTED)
    municipality_selector = ft.Dropdown(
        label=tr("municipality_label"),
        hint_text=tr("municipality_hint"),
        options=[
            ft.DropdownOption(key=municipality, text=municipality)
            for municipality in MUNICIPALITIES
        ],
        expand=True,
    )
    street_address = ft.TextField(
        label=tr("street_address_label"),
        hint_text=tr("street_address_hint"),
        expand=True,
    )
    form_error = ft.Text(color="#A33A32", size=14)
    privacy_note = ft.Text(tr("privacy_note"), size=12, color=MUTED)

    def render_results(shelters):
        results_section.controls = [
            ft.Text(tr("shelter_title"), size=20, weight=ft.FontWeight.BOLD),
            *[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                shelter["name"],
                                size=17,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(shelter["address"], size=14),
                            ft.Text(
                                tr("distance_label", distance=shelter["distance_km"]),
                                size=14,
                                color="#2E6654",
                            ),
                            ft.TextButton(
                                content=tr("map_button"),
                                url=(
                                    "https://maps.gsi.go.jp/#16/"
                                    f"{shelter['latitude']}/{shelter['longitude']}"
                                ),
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=16,
                    bgcolor="white",
                    border_radius=12,
                )
                for shelter in shelters
            ],
            ft.Text(tr("safety_note"), size=12, color=MUTED),
            ft.TextButton(content=tr("source_label"), url=GSI_SHELTER_SOURCE),
            ft.TextButton(content=tr("new_search_button"), on_click=show_address_form),
        ]
        apply_text_scale(results_section)

    found_shelters = []

    def show_address_form(_event=None):
        results_section.visible = False
        packing_section.visible = True
        address_section.visible = True
        municipality_selector.value = None
        street_address.value = ""
        form_error.value = ""
        page.update()

    def search_shelters(_event):
        nonlocal found_shelters
        municipality = municipality_selector.value
        address = (street_address.value or "").strip()
        municipality_selector.value = None
        street_address.value = ""
        if not municipality or not address:
            form_error.value = tr("address_required")
            page.update()
            return

        search_button.disabled = True
        search_button.content = tr("searching")
        form_error.value = ""
        page.update()
        try:
            found_shelters = find_nearest_shelters(municipality, address)
        except AddressNotFoundError:
            form_error.value = tr("address_not_found")
        except HTTPError as error:
            form_error.value = f"{tr('search_failed')} (HTTP {error.code})"
        except (URLError, TimeoutError, json.JSONDecodeError, csv.Error, UnicodeDecodeError) as error:
            form_error.value = f"{tr('search_failed')} ({error})"
        except ValueError as error:
            form_error.value = f"{tr('search_failed')} ({error})"
        else:
            packing_section.visible = False
            address_section.visible = False
            render_results(found_shelters)
            results_section.visible = True
        finally:
            search_button.disabled = False
            search_button.content = tr("search_button")
            page.update()

    address_section = ft.Column(
        [
            address_title,
            address_description,
            ft.Row(
                [
                    ft.Text(tr("prefecture_label"), size=14, weight=ft.FontWeight.BOLD),
                    municipality_selector,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            street_address,
            privacy_note,
            form_error,
            ft.FilledButton(
                content=tr("search_button"),
                on_click=search_shelters,
            ),
        ],
        spacing=12,
    )
    search_button = address_section.controls[-1]
    results_section = ft.Column(visible=False, spacing=16)
    content = ft.Column(
        [header, packing_section, address_section, results_section],
        width=700,
        spacing=28,
    )
    app_container = ft.Container(content=content, width=700, padding=ft.Padding.only(top=18, bottom=32))
    apply_text_scale(app_container)

    def resize_page(event):
        viewport_width = page.width or 748
        page.padding = 12 if viewport_width < 520 else 24
        content_width = min(700, max(272, viewport_width - page.padding * 2))
        app_container.width = content_width
        content.width = content_width
        page.update()

    page.on_resize = resize_page
    page.add(app_container)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)