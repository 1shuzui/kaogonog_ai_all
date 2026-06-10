"""
省份配置测试确认用户引导里仍能选择已经支持的省份。

题库分类重构后，省份不再等同于考试体系，但注册偏好、首页推荐和定向备面仍需要合法省份列表。
这个用例单独锁定安徽可用，是为了防止新增分类树时把真实省份从用户配置里误删。

@param: 无；直接读取用户服务暴露的省份配置。
@return: 无直接返回；断言通过表示省份入口仍可被注册和偏好流程使用。
@raises ImportError: 用户服务或配置依赖缺失时会失败。
"""
import unittest

from app.services.user_service import VALID_PROVINCES, get_provinces


class TestUserServiceProvinces(unittest.TestCase):
    """
    用户省份配置用例集合，确认注册引导和偏好配置仍能选择真实省份。

    定向备面分类树可以按考试体系重排，但用户偏好里的省份列表不能因此缺项。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 已支持省份从展示列表或合法代码集合中丢失时由断言报告。
    """
    def test_anhui_is_available_and_valid(self):
        """
        安徽必须同时存在于展示列表和合法省份代码集合中。

        省份展示列表和校验集合任一缺失，都会导致用户能看见但不能保存，或后端能保存但前端无法选择。

        @param: 无；直接读取 `get_provinces` 和 `VALID_PROVINCES`。
        @return: None；展示和校验两边都包含安徽时通过。
        @raises AssertionError: 安徽入口缺失或校验不通过时失败。
        """
        provinces = get_provinces()

        self.assertIn({"code": "anhui", "name": "安徽"}, provinces)
        self.assertIn("anhui", VALID_PROVINCES)


if __name__ == "__main__":
    unittest.main()
