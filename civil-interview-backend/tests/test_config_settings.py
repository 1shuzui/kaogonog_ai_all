"""
配置兼容测试确认 `.env` 恢复后仍能暴露现网需要的关键字段。

项目从 Whisper 切到 FunASR、从模拟支付切到微信虚拟支付、从 SQLite 开发切到 MySQL 后，配置字段数量明显增加。
这个测试不验证字段值是否正确，只防止重构 Settings 时删掉运行链路仍会读取的属性。

@param: 无；直接读取 `app.core.config.settings`。
@return: 无直接返回；断言通过表示配置对象仍保留必要属性。
@raises ImportError: 配置模块或 pydantic 设置依赖异常时，导入阶段会失败。
"""
import unittest

from app.core.config import settings


class SettingsCompatibilityTestCase(unittest.TestCase):
    """
    配置兼容用例集合，确认关键配置字段在 Settings 重构后仍可被读取。

    这不是配置值正确性测试，而是“字段存在性”护栏；字段缺失会让服务在运行时才爆，而不是启动时提醒。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 任一关键配置字段被删掉或改名时由断言报告。
    """
    def test_settings_exposes_llm_fields(self):
        """
        LLM、Redis 和 FunASR 相关字段必须继续挂在 settings 上。

        后端多处代码直接读取这些字段；即使默认值以后调整，字段本身也不能在没有迁移的情况下消失。

        @param: 无；直接检查全局 settings 实例。
        @return: None；所有被运行链路读取的字段存在时通过。
        @raises AssertionError: 配置字段缺失时失败。
        """
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
        self.assertTrue(hasattr(settings, "redis_url"))
        self.assertTrue(hasattr(settings, "redis_cache_ttl_questions"))
        self.assertTrue(hasattr(settings, "redis_cache_ttl_llm"))
        self.assertTrue(hasattr(settings, "redis_cache_ttl_transcript"))
        self.assertTrue(hasattr(settings, "asr_provider"))
        self.assertTrue(hasattr(settings, "funasr_model_name"))
        self.assertTrue(hasattr(settings, "funasr_vad_model_name"))
        self.assertTrue(hasattr(settings, "funasr_punc_model_name"))
        self.assertTrue(hasattr(settings, "funasr_quantize"))
        self.assertTrue(hasattr(settings, "modelscope_cache"))


if __name__ == "__main__":
    unittest.main()
