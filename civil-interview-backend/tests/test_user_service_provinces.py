import unittest

from app.services.user_service import VALID_PROVINCES, get_provinces


class TestUserServiceProvinces(unittest.TestCase):
    def test_anhui_is_available_and_valid(self):
        provinces = get_provinces()

        self.assertIn({"code": "anhui", "name": "安徽"}, provinces)
        self.assertIn("anhui", VALID_PROVINCES)


if __name__ == "__main__":
    unittest.main()
