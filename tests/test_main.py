import io
import json
import unittest
from unittest.mock import patch

import flet as ft
import main


class FakePage:
    def add(self, *controls):
        self.controls = list(controls)

    def update(self):
        pass


def walk_controls(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from walk_controls(content)
    for child in getattr(control, "controls", []) or []:
        yield from walk_controls(child)


class FindNearestSheltersTests(unittest.TestCase):
    def test_accepts_geocoder_result_that_is_shorter_than_requested_address(self):
        features = [
            {
                "properties": {"title": "富山県高岡市広小路７番"},
                "geometry": {"coordinates": [136.99, 36.75]},
            }
        ]
        shelter_csv = (
            "施設・場所名,住所,緯度,経度\n"
            "指定避難所,富山県高岡市広小路,36.75,136.99\n"
        )

        with patch(
            "main.urlopen",
            side_effect=[
                io.BytesIO(json.dumps(features).encode("utf-8")),
                io.BytesIO(shelter_csv.encode("utf-8")),
            ],
        ):
            results = main.find_nearest_shelters("高岡市", "広小路7-50")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "指定避難所")

    def test_accepts_japanese_numerals_in_geocoder_result(self):
        features = [
            {
                "properties": {"title": "富山県魚津市釈迦堂一丁目１０番"},
                "geometry": {"coordinates": [137.40, 36.82]},
            }
        ]
        shelter_csv = (
            "施設・場所名,住所,緯度,経度\n"
            "指定避難所,富山県魚津市釈迦堂,36.82,137.40\n"
        )

        with patch(
            "main.urlopen",
            side_effect=[
                io.BytesIO(json.dumps(features).encode("utf-8")),
                io.BytesIO(shelter_csv.encode("utf-8")),
            ],
        ):
            results = main.find_nearest_shelters("魚津市", "釈迦堂1-10-1")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "指定避難所")

    def test_rejects_geocoder_result_for_a_different_address(self):
        features = [
            {
                "properties": {"title": "富山県高岡市片原町７番"},
                "geometry": {"coordinates": [136.99, 36.75]},
            }
        ]

        with patch(
            "main.urlopen",
            return_value=io.BytesIO(json.dumps(features).encode("utf-8")),
        ) as open_url:
            with self.assertRaises(main.AddressNotFoundError):
                main.find_nearest_shelters("高岡市", "広小路7-50")

        open_url.assert_called_once()

    def test_clears_address_fields_before_sending_search_request(self):
        page = FakePage()
        main.main(page)
        controls = [
            control
            for root in page.controls
            for control in walk_controls(root)
        ]
        municipality_selector = next(
            control
            for control in controls
            if isinstance(control, ft.Dropdown) and control.label == "市町村"
        )
        street_address = next(
            control
            for control in controls
            if isinstance(control, ft.TextField) and control.label == "町名・番地"
        )
        search_button = next(
            control for control in controls if isinstance(control, ft.FilledButton)
        )
        municipality_selector.value = "高岡市"
        street_address.value = "広小路7-50"

        def find_shelters(municipality, address):
            self.assertIsNone(municipality_selector.value)
            self.assertEqual(street_address.value, "")
            return []

        with patch("main.find_nearest_shelters", side_effect=find_shelters) as search:
            search_button.on_click(None)

        search.assert_called_once_with("高岡市", "広小路7-50")

    def test_text_size_selector_has_three_options(self):
        page = FakePage()
        main.main(page)
        controls = [
            control
            for root in page.controls
            for control in walk_controls(root)
        ]
        text_size_selector = next(
            control
            for control in controls
            if isinstance(control, ft.Dropdown) and control.label == "文字サイズ"
        )

        self.assertEqual(
            [option.key for option in text_size_selector.options],
            ["small", "medium", "large"],
        )

    def test_text_size_selection_scales_text_and_form_controls(self):
        page = FakePage()
        main.main(page)
        controls = [
            control
            for root in page.controls
            for control in walk_controls(root)
        ]
        text_size_selector = next(
            control
            for control in controls
            if isinstance(control, ft.Dropdown) and control.label == "文字サイズ"
        )
        text_field = next(control for control in controls if isinstance(control, ft.TextField))
        municipality_selector = next(
            control
            for control in controls
            if isinstance(control, ft.Dropdown) and control.label == "市町村"
        )
        checkbox = next(control for control in controls if isinstance(control, ft.Checkbox))
        button = next(control for control in controls if isinstance(control, ft.FilledButton))
        brand_mark = next(
            control
            for control in controls
            if isinstance(control, ft.Text) and control.value == "日"
        )

        text_size_selector.value = "large"
        text_size_selector.on_select(None)

        self.assertEqual(brand_mark.size, 18)
        self.assertEqual(text_field.text_size, 19)
        self.assertEqual(municipality_selector.text_size, 19)
        self.assertEqual(municipality_selector.label_style.size, 14)
        self.assertEqual(checkbox.label_style.size, 17)
        self.assertEqual(button.style.text_style.size, 17)


if __name__ == "__main__":
    unittest.main()
