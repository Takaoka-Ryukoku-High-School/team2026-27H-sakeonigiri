from datetime import date
from pathlib import Path

import flet as ft


ADDRESS_FILE = Path.home() / ".daily_note_address.txt"
GREEN = "#2E6654"
PAPER = "#F6F5EF"
INK = "#202C2A"
MUTED = "#77807B"
CORAL = "#CF6048"


def load_address():
    try:
        return ADDRESS_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def main(page: ft.Page):
    page.title = "住所の回答 | Address"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = PAPER
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    current_language = "ja"
    translations = {
        "ja": {
            "app_title": "住所の回答 | Address",
            "brand_mark": "日",
            "today": "住所の回答",
            "tagline": "住所を入力して保存できます。",
            "language_tooltip": "表示言語",
            "date_format": "%Y年%m月%d日",
            "address_title": "住所の回答",
            "address_hint": "住所を入力してください",
            "address_save": "住所を保存",
            "address_saved": "住所を保存しました。",
            "address_save_error": "住所を保存できませんでした。書き込み権限をご確認ください。",
        },
        "en": {
            "app_title": "Address | Daily Note",
            "brand_mark": "D",
            "today": "Address answer",
            "tagline": "Enter and save an address.",
            "language_tooltip": "Display language",
            "date_format": "%b %d, %Y",
            "address_title": "Address answer",
            "address_hint": "Enter an address",
            "address_save": "Save address",
            "address_saved": "Address saved.",
            "address_save_error": "Could not save the address. Check your file permissions.",
        },
    }

    address_status = ""

    def tr(key, **values):
        return translations[current_language][key].format(**values)

    def formatted_date():
        return date.today().strftime(tr("date_format"))

    def save_address(_event):
        nonlocal address_status
        try:
            ADDRESS_FILE.write_text(
                address_input.value.strip(),
                encoding="utf-8",
            )
        except OSError:
            address_status = "error"
        else:
            address_status = "saved"
        update_address_status()
        page.update()

    def update_address_status():
        address_status_text.value = (
            tr("address_saved")
            if address_status == "saved"
            else tr("address_save_error")
            if address_status == "error"
            else ""
        )
        address_status_text.color = CORAL if address_status == "error" else GREEN

    page.title = tr("app_title")

    def set_language(_event):
        nonlocal current_language
        current_language = language_selector.value or "ja"
        page.title = tr("app_title")
        brand_mark.value = tr("brand_mark")
        title_text.value = tr("today")
        tagline_text.value = tr("tagline")
        address_title.value = tr("address_title")
        address_input.hint_text = tr("address_hint")
        address_save_button.content = tr("address_save")
        update_address_status()
        today.value = formatted_date()
        language_selector.tooltip = tr("language_tooltip")
        render()

    address_title = ft.Text(
        tr("address_title"),
        size=18,
        color=INK,
        weight=ft.FontWeight.W_600,
    )
    address_input = ft.TextField(
        value=load_address(),
        hint_text=tr("address_hint"),
        multiline=True,
        min_lines=2,
        max_lines=3,
        expand=True,
        border_radius=6,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor="#FFFEFA",
        text_size=15,
    )
    address_status_text = ft.Text(size=12)
    address_save_button = ft.Button(
        tr("address_save"),
        on_click=save_address,
        bgcolor=GREEN,
        color="white",
        height=44,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
    )
    address_card = ft.Container(
        content=ft.Column(
            [
                address_title,
                ft.Row([address_input, address_save_button], spacing=10),
                address_status_text,
            ],
            spacing=10,
        ),
        padding=18,
        bgcolor="#FFFEFA",
        border=ft.Border.all(1, "#E3E3D9"),
        border_radius=8,
    )
    title_text = ft.Text(tr("today"), size=38, color=INK, weight=ft.FontWeight.W_600)
    tagline_text = ft.Text(tr("tagline"), size=13, color=MUTED)
    brand_mark = ft.Text(tr("brand_mark"), color="white", size=15, weight=ft.FontWeight.BOLD)
    today = ft.Text(
        formatted_date(),
        size=12,
        color=MUTED,
    )
    language_selector = ft.Dropdown(
        value=current_language,
        options=[
            ft.DropdownOption(key="ja", text="日本語"),
            ft.DropdownOption(key="en", text="English"),
        ],
        on_select=set_language,
        width=132,
        tooltip=tr("language_tooltip"),
    )
    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=brand_mark,
                                width=28,
                                height=28,
                                bgcolor=GREEN,
                                border_radius=14,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Text("DAILY NOTE", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=10,
                    ),
                    ft.Row([today, language_selector], spacing=8),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Column(
                [
                    title_text,
                    tagline_text,
                ],
                spacing=4,
            ),
            address_card,
        ],
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