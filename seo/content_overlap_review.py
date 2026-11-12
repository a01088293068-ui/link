#!/usr/bin/env python3
"""Find existing guides with overlapping text before making more SEO articles.

This is a local editorial review, not an automated deletion, Search Console
ranking result or Google duplicate-content verdict. Ignore common template
boilerplate. Only review genuine published Markdown files.
"""
import argparse
from collections import Counter
from itertools import combinations
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MIN_LENGTH = 250
SIMILAR_THRESHOLD = 0.36
COMMON_EXCLUSIONS = (
    "링크위키의 등록 설명은",
    "링크위키는 외부",
    "목록에 등록",
)


def normalize(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"[#*_~|>`\[\](){}.,:;!?\-–—]+", " ", text)
    return " ".join(text.casefold().split())


def article(path):
    body = path.read_text(encoding="utf-8-sig")
    if len(body.strip()) < MIN_LENGTH or not body.lstrip().startswith("# "):
        return None
    title = body.splitlines()[0].lstrip("# ").strip()
    paragraphs = []
    for segment in re.split(r"\n\s*\n", body):
        line = segment.strip()
        if not line or line.startswith(("#", "|", "- [", "- ", "* ")):
            continue
        normalized = normalize(line)
        if len(normalized) >= 70 and not any(
                normalized.startswith(normalize(prefix)) for prefix in COMMON_EXCLUSIONS):
            paragraphs.append(normalized)
    return {"slug": path.stem, "title": title, "paragraphs": paragraphs}


def shingles(value, size=9):
    txt = normalize(value).replace(" ", "")
    return {txt[i:i + size] for i in range(max(0, len(txt) - size + 1))}


def analyze(folder):
    docs = [item for item in (article(file) for file in sorted(folder.glob("*.md")))
            if item is not None]
    if not docs:
        raise ValueError("no published Markdown content found")
    paragraph_counts = Counter(p for doc in docs for p in set(doc["paragraphs"]))
    useful = {}
    for doc in docs:
        # Shared repetitive template is not original article substance.
        unique_body = " ".join(
            p for p in doc["paragraphs"] if paragraph_counts[p] <= 2
        )
        useful[doc["slug"]] = shingles(unique_body)
    candidates = []
    for a, b in combinations(docs, 2):
        aa, bb = useful[a["slug"]], useful[b["slug"]]
        if not aa or not bb:
            continue
        overlap = len(aa & bb) / len(aa | bb)
        if overlap >= SIMILAR_THRESHOLD:
            candidates.append({
                "a": a["slug"], "b": b["slug"],
                "a_title": a["title"], "b_title": b["title"],
                "body_shingle_jaccard": round(overlap, 3),
            })
    candidates.sort(key=lambda r: (-r["body_shingle_jaccard"], r["a"], r["b"]))
    repeated = [
        {"sample": text[:120], "article_count": count}
        for text, count in paragraph_counts.items()
        if count >= 3 and len(text) >= 70
    ]
    repeated.sort(key=lambda r: (-r["article_count"], r["sample"]))
    return {
        "article_count": len(docs),
        "pairs_compared": len(docs) * (len(docs) - 1) // 2,
        "threshold": SIMILAR_THRESHOLD,
        "review_candidates": candidates,
        "repeated_boilerplate": repeated[:15],
        "limitations": (
            "Similarity highlights possible editorial overlap, not proof of "
            "Google canonicalization or SEO ranking penalties. Do not delete "
            "or redirect published articles without inspecting their intent, "
            "actual GSC URL-level performance, and internal links."
        ),
    }


def render(report):
    lines = [
        "# 링크위키 가이드 검색의도·본문 중복 점검",
        "",
        f"- 실제 발행 글: {report['article_count']}개",
        f"- 비교한 쌍: {report['pairs_compared']}개",
        f"- 검토 대상: {len(report['review_candidates'])}쌍",
        "- 성격: 오프라인 편집 검토용으로, Google의 중복 판정이나 검색순위 측정이 아닙니다.",
        "",
        "## 본문 유사도 재검토 후보",
        "",
        "| 글 A | 글 B | 본문 문자 구간 유사도 |",
        "|---|---|---:|",
    ]
    for item in report["review_candidates"][:25]:
        lines.append(
            f"| {item['a']} | {item['b']} | "
            f"{item['body_shingle_jaccard']:.3f} |")
    if not report["review_candidates"]:
        lines.append("| (검토 기준 이상 없음) | — | — |")
    lines += ["", "## 자주 반복되는 공통 문단(본문 판단에서 제외)", ""]
    for item in report["repeated_boilerplate"][:12]:
        lines.append(f"- {item['article_count']}개 글: {item['sample']}")
    if not report["repeated_boilerplate"]:
        lines.append("- 반복 공통 문단 없음")
    lines += ["", "## 편집 권고", "",
              "1. 비슷한 검색어를 겨냥한 두 글의 독립적인 이용 목적과 실제 사용 가치를 확인합니다.",
              "2. 중복으로 판단되면 성과와 링크를 살펴보고 통합·수정 여부를 결정합니다.",
              "3. Google 색인 여부와 실제 검색 유입을 확인하지 않고 대량 삭제하지 않습니다.",
              "4. 이 결과만으로 검색순위 개선이나 페널티 해소를 주장하지 않습니다.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--content", type=Path, default=ROOT / "content")
    parser.add_argument("--report", type=Path,
                        default=ROOT / "seo" / "content-overlap-review.md")
    parser.add_argument("--json", type=Path,
                        default=ROOT / "seo" / "content-overlap-observations.json")
    args = parser.parse_args()
    result = analyze(args.content)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render(result), encoding="utf-8")
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    print(f"ARTICLE_OVERLAP_AUDIT: {result['article_count']} posts, "
          f"{result['pairs_compared']} pairs, "
          f"{len(result['review_candidates'])} editorial review candidates")
    print("NOTE: no article was deleted, redirected or tagged as Google-duplicate.")


if __name__ == "__main__":
    main()
