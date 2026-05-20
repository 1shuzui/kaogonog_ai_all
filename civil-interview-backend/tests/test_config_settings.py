import unittest

from app.core.config import settings


class SettingsCompatibilityTestCase(unittest.TestCase):
    def test_settings_exposes_llm_fields(self):
        self.assertTrue(hasattr(settings, "llm_provider"))
        self.assertTrue(hasattr(settings, "llm_api_key"))
        self.assertTrue(hasattr(settings, "llm_base_url"))
        self.assertTrue(hasattr(settings, "llm_model"))
        self.assertTrue(hasattr(settings, "llm_asr_model"))
        self.assertTrue(hasattr(settings, "qwen_api_key"))
        self.assertTrue(hasattr(settings, "qwen_base_url"))
        self.assertTrue(hasattr(settings, "qwen_model"))
        self.assertTrue(hasattr(settings, "qwen_asr_model"))
        self.assertTrue(hasattr(settings, "llm_timeout_seconds"))


if __name__ == "__main__":
    unittest.main()
