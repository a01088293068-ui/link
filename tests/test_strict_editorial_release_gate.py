"""Ensure new automated SEO articles cannot bypass structured and honest review."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "auto_seo_release_gate", ROOT / "seo" / "auto_seo.py"
)
seo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seo)


def sample():
    parts = [
        "표시된 주소가 공식 운영 주체가 안내하는 주소인지 먼저 비교할 필요가 있습니다.",
        "검색 기능이 등록된 항목에만 작동한다는 제한을 염두에 두고 검색어를 조정합니다.",
        "사이트 이름의 약칭과 정식 명칭을 각각 확인하고 결과 설명을 비교합니다.",
        "분야별 목록을 열어 실제 제공하는 기능과 필요 목적이 일치하는지 확인합니다.",
        "모바일 환경은 버전별 배치가 다를 수 있으므로 실제 주소를 점검합니다.",
        "계정 정보를 입력하기 전 서비스 이용 조건과 운영자 공지를 찾아보세요.",
        "접속하지 못하는 경우에는 오류 화면과 공식 공지를 구분하여 확인합니다.",
        "비슷한 이름의 서비스가 있을 수 있으므로 도메인 전체를 확인합니다.",
    ]
    return {
        "title": "링크모음 사이트 비교 기준",
        "description": "링크모음 사이트를 비교하는 구체적인 기준과 안전한 주소 확인 단계 및 실수하기 쉬운 점검 방법을 정리한 실용적인 이용 가이드입니다.",
        "introduction": "연결 주소와 사이트 분류가 서로 일치하는지 구체적으로 확인합니다. " * 8,
        "sections": [
            {"heading": f"상황 점검 {i}", "paragraphs": [
                parts[2 * i] * 3, parts[2 * i + 1] * 3
            ]} for i in range(4)
        ],
        "faq": [
            {"question": f"확인 방법 {i}", "answer":
             "등록된 서비스의 운영 주체와 도메인 주소를 대조합니다. "
             "경고가 표시되면 진행하지 말고 공식 안내를 확인합니다."}
            for i in range(3)
        ],
    }


TABLE = {
    "headers": ["상황", "확인 항목", "다음 행동"],
    "rows": [
        ["이름이 비슷한 경우", "운영자 공지 주소", "공식 도메인 비교"],
        ["연결 오류 발생", "현재 주소와 오류", "관련 안내 확인"],
        ["목록 선택 문제", "등록 항목 분류", "분야 목록 비교"],
    ],
}
CHECKLIST = [
    "서비스 이름과 실제 주소를 각각 확인했나요?",
    "공식 운영자의 주소 안내를 다시 대조했나요?",
    "입력하려는 개인정보의 이용 목적을 확인했나요?",
]


class StrictEditorialReleaseGateTests(unittest.TestCase):
    def review(self, article, strict=True):
        return seo.deterministic_review(
            "링크모음 사이트 비교 기준", article, seo.render(article),
            [], require_structured=strict
        )

    def test_existing_drafts_remain_compatible_for_nonpublishing_checks(self):
        article = sample()
        reasons = self.review(article, strict=False)
        self.assertNotIn("new drafts require a comparison table", reasons)
        self.assertNotIn("new drafts require an actionable checklist", reasons)

    def test_publish_gate_requires_both_structures(self):
        article = sample()
        reasons = self.review(article)
        self.assertIn("new drafts require a comparison table", reasons)
        self.assertIn("new drafts require an actionable checklist", reasons)
        article["decision_table"] = TABLE
        reasons = self.review(article)
        self.assertNotIn("new drafts require a comparison table", reasons)
        self.assertIn("new drafts require an actionable checklist", reasons)
        article["checklist"] = CHECKLIST
        reasons = self.review(article)
        self.assertNotIn("new drafts require a comparison table", reasons)
        self.assertNotIn("new drafts require an actionable checklist", reasons)
        self.assertNotIn("decision table incomplete or unsupported", reasons)
        self.assertNotIn("action checklist incomplete", reasons)

    def test_claimed_field_test_is_blocked(self):
        article = sample()
        article["decision_table"] = TABLE
        article["checklist"] = CHECKLIST
        article["introduction"] += " 제가 직접 테스트해 봤는데 모든 결과가 같았습니다."
        self.assertIn("unsupported first-person test or experience claim", self.review(article))

    def test_hypothetical_troubleshooting_is_allowed(self):
        article = sample()
        article["decision_table"] = TABLE
        article["checklist"] = CHECKLIST
        article["introduction"] += " 검색 결과가 나오지 않는다면 우선 이름과 도메인을 확인하세요."
        self.assertNotIn("unsupported first-person test or experience claim", self.review(article))

    def test_main_uses_strict_gate_before_independent_review(self):
        source = (ROOT / "seo" / "auto_seo.py").read_text(encoding="utf-8")
        self.assertIn("markdown, titles, require_structured=True)", source)
        self.assertLess(source.index("issues = deterministic_review(", source.index("def main():")),
                        source.index("independent_review(topic, article, markdown)", source.index("def main():")))


if __name__ == "__main__":
    unittest.main()
