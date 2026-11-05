from datetime import date

import flet as ft


PAPER = "#F6F5EF"
MUTED = "#77807B"


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
        },
        "en": {
            "app_title": "Daily Note",
            "brand_mark": "D",
            "language_label": "Language",
            "language_tooltip": "Display language",
            "date_format": "%b %d, %Y",
        },
        "zh": {
            "app_title": "每日记录",
            "brand_mark": "记",
            "language_label": "语言",
            "language_tooltip": "选择语言",
            "date_format": "%Y年%m月%d日",
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
    content = ft.Row(
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