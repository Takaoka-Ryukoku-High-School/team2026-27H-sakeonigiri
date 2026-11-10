import csv
import io
import json
import math
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
        if (
            isinstance(title, str)
            and title.startswith(address_prefix)
            and normalized_address
            in normalize_address_part(title[len(address_prefix) :])
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
            "date_format": "%Y年%m月%d日",
            "address_title": "住所",
            "address_description": "富山県内の住所を入力してください。",
            "prefecture_label": "富山県",
            "municipality_label": "市町村",
            "municipality_hint": "市町村を選択",
            "street_address_label": "町名・番地",
            "street_address_hint": "例：新桜町7-38",
            "privacy_note": "入力住所は座標検索のため国土地理院の住所検索サービスに送信されます。",
            "search_button": "最寄りの避難所を検索",
            "searching": "検索中…",
            "address_required": "市町村と町名・番地を入力してください。",
            "address_not_found": "住所を確認できませんでした。選択した市町村内の住所を入力してください。",
            "search_failed": "避難所データを取得できませんでした。時間をおいて再度お試しください。",
            "shelter_title": "近くの指定避難所",
            "distance_label": "直線距離：約{distance:.1f} km",
            "map_button": "地理院地図で見る",
            "back_button": "住所入力に戻る",
            "safety_note": "距離は直線距離です。避難所の開設状況は反映されません。また、公開データに未掲載の施設がある場合があります。災害時は自治体の避難情報と最新の指定状況を確認してください。",
            "source_label": "出典：国土地理院「指定避難所データ」",
        },
        "en": {
            "app_title": "Daily Note",
            "brand_mark": "D",
            "language_label": "Language",
            "language_tooltip": "Display language",
            "date_format": "%b %d, %Y",
            "address_title": "Address",
            "address_description": "Enter an address in Toyama Prefecture.",
            "prefecture_label": "Toyama",
            "municipality_label": "Municipality",
            "municipality_hint": "Select a municipality",
            "street_address_label": "Street address",
            "street_address_hint": "e.g. 7-38 Shinsakuramachi",
            "privacy_note": "Your address is sent to the Geospatial Information Authority of Japan address search service to find its coordinates.",
            "search_button": "Find nearby shelters",
            "searching": "Searching…",
            "address_required": "Select a municipality and enter a street address.",
            "address_not_found": "Address not found. Enter an address within the selected municipality.",
            "search_failed": "Could not retrieve shelter data. Please try again later.",
            "shelter_title": "Nearby designated shelters",
            "distance_label": "Straight-line distance: about {distance:.1f} km",
            "map_button": "View on GSI Maps",
            "back_button": "Back to address",
            "safety_note": "Distances are straight-line estimates; shelter opening status is not shown. Some facilities may not be included in the public data. During a disaster, check your municipality's evacuation information and current shelter designations.",
            "source_label": 'Source: Geospatial Information Authority of Japan, "Designated Evacuation Shelters"',
        },
        "zh": {
            "app_title": "每日记录",
            "brand_mark": "记",
            "language_label": "语言",
            "language_tooltip": "选择语言",
            "date_format": "%Y年%m月%d日",
            "address_title": "地址",
            "address_description": "请输入富山县内的地址。",
            "prefecture_label": "富山县",
            "municipality_label": "市町村",
            "municipality_hint": "请选择市町村",
            "street_address_label": "町名、门牌号",
            "street_address_hint": "例如：新樱町7-38",
            "privacy_note": "为查询坐标，输入的地址会发送至日本国土地理院的地址搜索服务。",
            "search_button": "查找最近的避难所",
            "searching": "搜索中…",
            "address_required": "请选择市町村并输入町名和门牌号。",
            "address_not_found": "未找到该地址。请输入所选市町村内的地址。",
            "search_failed": "无法获取避难所数据，请稍后重试。",
            "shelter_title": "附近的指定避难所",
            "distance_label": "直线距离：约 {distance:.1f} 公里",
            "map_button": "在国土地理院地图中查看",
            "back_button": "返回地址输入",
            "safety_note": "距离为直线距离，未显示避难所开放状态。公开数据可能未收录部分设施。发生灾害时，请确认市町村的避难信息及最新指定情况。",
            "source_label": "来源：日本国土地理院“指定避难所数据”",
        },
    }

    def tr(key, **values):
        return translations[current_language][key].format(**values)

    def formatted_date():
        return date.today().strftime(tr("date_format"))

    page.title = tr("app_title")

    def set_language(_event):
        nonlocal current_language
        current_language = language_selector.value or "ja"
        page.title = tr("app_title")
        brand_mark.value = tr("brand_mark")
        today.value = formatted_date()
        language_selector.label = tr("language_label")
        language_selector.tooltip = tr("language_tooltip")
        address_title.value = tr("address_title")
        address_description.value = tr("address_description")
        municipality_selector.label = tr("municipality_label")
        municipality_selector.hint_text = tr("municipality_hint")
        street_address.label = tr("street_address_label")
        street_address.hint_text = tr("street_address_hint")
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
            ft.Row([today, language_selector], spacing=8),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
            ft.TextButton(content=tr("back_button"), on_click=show_address_form),
        ]

    found_shelters = []

    def show_address_form(_event=None):
        results_section.visible = False
        address_section.visible = True
        page.update()

    def search_shelters(_event):
        nonlocal found_shelters
        municipality = municipality_selector.value
        address = (street_address.value or "").strip()
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
        [header, address_section, results_section],
        width=700,
        spacing=28,
    )
    app_container = ft.Container(content=content, width=700, padding=ft.Padding.only(top=18, bottom=32))

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