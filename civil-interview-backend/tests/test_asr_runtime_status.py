import unittest
from unittest.mock import patch

from app.core import ai


class AsrRuntimeStatusTestCase(unittest.TestCase):
    def test_local_whisper_ready_when_dependencies_exist(self):
        with (
            patch.object(ai.settings, "llm_api_key", ""),
            patch.object(ai.settings, "llm_asr_model", ""),
            patch.object(ai.settings, "asr_provider", "whisper"),
            patch.object(ai, "_dependency_available", side_effect=lambda name: name in {"whisper", "torch"}),
            patch.object(ai.shutil, "which", return_value="/usr/bin/ffmpeg"),
        ):
            status = ai.get_asr_runtime_status()

        self.assertTrue(status["ready"])
        self.assertEqual(status["mode"], "local_whisper")
        self.assertTrue(status["localWhisper"]["dependencies"]["openaiWhisper"])
        self.assertTrue(status["localWhisper"]["dependencies"]["torch"])
        self.assertTrue(status["localWhisper"]["dependencies"]["ffmpeg"])

    def test_local_whisper_reports_missing_dependencies(self):
        with (
            patch.object(ai.settings, "llm_api_key", ""),
            patch.object(ai.settings, "llm_asr_model", ""),
            patch.object(ai.settings, "asr_provider", "whisper"),
            patch.object(ai, "_dependency_available", return_value=False),
            patch.object(ai.shutil, "which", return_value=""),
        ):
            status = ai.get_asr_runtime_status()

        self.assertFalse(status["ready"])
        self.assertEqual(status["mode"], "unavailable")
        self.assertIn("openai-whisper", status["message"])
        self.assertIn("torch", status["message"])
        self.assertIn("ffmpeg", status["message"])


if __name__ == "__main__":
    unittest.main()
