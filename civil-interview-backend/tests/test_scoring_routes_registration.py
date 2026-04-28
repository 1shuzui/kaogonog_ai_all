import unittest

from app.api.v1 import api_router


class ScoringRouteRegistrationTestCase(unittest.TestCase):
    def test_scoring_routes_are_registered(self):
        route_paths = {route.path for route in api_router.routes}

        self.assertIn("/scoring/transcribe", route_paths)
        self.assertIn("/scoring/evaluate", route_paths)
        self.assertIn("/scoring/result/{exam_id}/{question_id}", route_paths)


if __name__ == "__main__":
    unittest.main()
