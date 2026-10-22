# -*- coding: utf-8 -*-
"""
CyberScore — Automated Test Suite
Run with:
    python cyberscore/tests.py
or:
    python -m pytest cyberscore/tests.py -v
"""

import sys
import os
import json
import tempfile
import unittest
from pathlib import Path

# Ensure local imports resolve
sys.path.insert(0, str(Path(__file__).parent))

import scoring as sc
import db
import url_analyzer as ua
import pdf_report


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _best_answers() -> dict:
    """Return answers that pick the best option for every question."""
    answers = {}
    for q_key, _, point_map in sc.QUESTIONS:
        best_key = max(point_map, key=point_map.get)
        answers[q_key] = best_key
    return answers


def _worst_answers() -> dict:
    """Return answers that pick the worst option for every question."""
    answers = {}
    for q_key, _, point_map in sc.QUESTIONS:
        worst_key = min(point_map, key=point_map.get)
        answers[q_key] = worst_key
    return answers


def _mid_answers() -> dict:
    """Return answers that pick the middle option for every question."""
    answers = {}
    for q_key, _, point_map in sc.QUESTIONS:
        keys = list(point_map.keys())
        answers[q_key] = keys[len(keys) // 2]
    return answers


# ══════════════════════════════════════════════════════════════════════════════
#  1. Scoring Engine Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestScoringEngine(unittest.TestCase):

    # ── Score bounds ───────────────────────────────────────────────────────
    def test_best_answers_yield_100(self):
        result = sc.compute_score(_best_answers())
        self.assertAlmostEqual(result.overall, 100.0, places=1,
                               msg="Best answers must yield overall=100")

    def test_worst_answers_yield_0(self):
        result = sc.compute_score(_worst_answers())
        self.assertAlmostEqual(result.overall, 0.0, places=1,
                               msg="Worst answers must yield overall=0")

    def test_mid_answers_in_range(self):
        result = sc.compute_score(_mid_answers())
        self.assertGreater(result.overall, 0)
        self.assertLess(result.overall, 100)

    def test_overall_always_in_0_100(self):
        for answers in [_best_answers(), _worst_answers(), _mid_answers(), {}]:
            result = sc.compute_score(answers)
            self.assertGreaterEqual(result.overall, 0.0)
            self.assertLessEqual(result.overall, 100.0)

    # ── Category coverage ──────────────────────────────────────────────────
    def test_all_categories_present(self):
        result = sc.compute_score(_mid_answers())
        for cat in sc.CATEGORIES:
            self.assertIn(cat, result.cat_scores,
                          f"Category '{cat}' missing from cat_scores")

    def test_cat_scores_in_0_100(self):
        result = sc.compute_score(_mid_answers())
        for cat, score in result.cat_scores.items():
            self.assertGreaterEqual(score, 0.0, f"{cat} score below 0")
            self.assertLessEqual(score, 100.0, f"{cat} score above 100")

    def test_cat_details_present(self):
        result = sc.compute_score(_best_answers())
        for cat in sc.CATEGORIES:
            self.assertIn(cat, result.cat_details)
            self.assertGreater(len(result.cat_details[cat]), 0)

    # ── Weights sum to 1.0 ─────────────────────────────────────────────────
    def test_weights_sum_to_one(self):
        total = sum(meta["weight"] for meta in sc.CATEGORIES.values())
        self.assertAlmostEqual(total, 1.0, places=5,
                               msg="Category weights must sum to 1.0")

    # ── Weighted formula correctness ───────────────────────────────────────
    def test_weighted_formula(self):
        result = sc.compute_score(_best_answers())
        expected = sum(
            result.cat_scores[cat] * sc.CATEGORIES[cat]["weight"]
            for cat in sc.CATEGORIES
        )
        self.assertAlmostEqual(result.overall, round(expected, 1), places=1)

    # ── Empty answers default to 0 ─────────────────────────────────────────
    def test_empty_answers_give_zero(self):
        result = sc.compute_score({})
        self.assertEqual(result.overall, 0.0)

    # ── Unknown answer values treated as 0 ────────────────────────────────
    def test_unknown_answer_treated_as_zero(self):
        answers = {q: "INVALID_KEY" for q, _, _ in sc.QUESTIONS}
        result = sc.compute_score(answers)
        self.assertEqual(result.overall, 0.0)

    # ── Risk levels ────────────────────────────────────────────────────────
    def test_risk_level_boundaries(self):
        cases = [
            (0,   "Critical"),
            (29,  "Critical"),
            (30,  "High"),
            (49,  "High"),
            (50,  "Medium"),
            (64,  "Medium"),
            (65,  "Low"),
            (79,  "Low"),
            (80,  "Minimal"),
            (100, "Minimal"),
        ]
        for score, expected_label in cases:
            label, _, _ = sc.risk_level(score)
            self.assertEqual(label, expected_label,
                             f"score={score}: expected {expected_label}, got {label}")

    def test_risk_level_returns_three_values(self):
        label, css_class, color = sc.risk_level(50)
        self.assertIsInstance(label, str)
        self.assertTrue(css_class.startswith("risk-"))
        self.assertTrue(color.startswith("#"))

    # ── Recommendations ────────────────────────────────────────────────────
    def test_recommendations_returned_for_worst(self):
        answers = _worst_answers()
        result  = sc.compute_score(answers)
        recs    = sc.generate_recommendations(answers, result.cat_scores)
        self.assertGreater(len(recs), 0)

    def test_recommendations_sorted_by_priority(self):
        answers = _worst_answers()
        result  = sc.compute_score(answers)
        recs    = sc.generate_recommendations(answers, result.cat_scores)
        order   = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        priorities = [order[r["priority"]] for r in recs]
        self.assertEqual(priorities, sorted(priorities),
                         "Recommendations must be sorted critical→low")

    def test_recommendations_have_required_keys(self):
        answers = _worst_answers()
        result  = sc.compute_score(answers)
        recs    = sc.generate_recommendations(answers, result.cat_scores)
        for rec in recs:
            for key in ("priority", "icon", "title", "body"):
                self.assertIn(key, rec, f"Rec missing key '{key}'")

    def test_no_recommendations_for_perfect_score(self):
        answers = _best_answers()
        result  = sc.compute_score(answers)
        recs    = sc.generate_recommendations(answers, result.cat_scores)
        # Should get the "Excellent" fallback rec
        self.assertTrue(any(r["priority"] == "low" for r in recs))

    # ── Strengths / Weaknesses ─────────────────────────────────────────────
    def test_strengths_weaknesses_types(self):
        result = sc.compute_score(_mid_answers())
        strong, weak = sc.strengths_weaknesses(result.cat_scores)
        self.assertIsInstance(strong, list)
        self.assertIsInstance(weak, list)

    def test_strengths_are_high_scoring(self):
        result = sc.compute_score(_best_answers())
        strong, _ = sc.strengths_weaknesses(result.cat_scores)
        for cat in strong:
            self.assertGreaterEqual(result.cat_scores[cat], 70)

    def test_weaknesses_are_low_scoring(self):
        result = sc.compute_score(_worst_answers())
        _, weak = sc.strengths_weaknesses(result.cat_scores)
        for cat in weak:
            self.assertLess(result.cat_scores[cat], 50)


# ══════════════════════════════════════════════════════════════════════════════
#  2. Database Tests (use a temp DB to avoid polluting production data)
# ══════════════════════════════════════════════════════════════════════════════

class TestDatabase(unittest.TestCase):

    def setUp(self):
        # Redirect DB to a temp file for isolation
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._orig_path = db.DB_PATH
        db.DB_PATH = Path(self._tmp.name)
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self._orig_path
        self._tmp.close()
        try:
            os.unlink(self._tmp.name)
        except Exception:
            pass

    # ── Assessment CRUD ────────────────────────────────────────────────────
    def test_save_and_load_assessment(self):
        cat_scores = {"Account Security": 75.0, "Phishing Awareness": 60.0,
                      "Device Security": 50.0, "Privacy": 80.0, "Backup Readiness": 45.0}
        answers    = {"acc_unique_pw": "always"}
        row_id = db.save_assessment(72.3, cat_scores, answers)
        self.assertIsInstance(row_id, int)
        self.assertGreater(row_id, 0)

        records = db.load_assessments()
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertAlmostEqual(r["overall"], 72.3, places=1)
        self.assertEqual(r["cat_scores"]["Account Security"], 75.0)
        self.assertEqual(r["answers"]["acc_unique_pw"], "always")

    def test_multiple_assessments_ordered_newest_first(self):
        import time
        for score in [40.0, 55.0, 70.0]:
            db.save_assessment(score, {}, {})
            time.sleep(0.01)   # ensure distinct timestamps
        records = db.load_assessments()
        self.assertEqual(len(records), 3)
        # Newest first: taken_at of record[0] >= taken_at of record[-1]
        self.assertGreaterEqual(records[0]["taken_at"], records[-1]["taken_at"])
        # And the last-inserted score (70.0) should be first
        self.assertAlmostEqual(records[0]["overall"], 70.0, places=1)

    def test_delete_all_assessments(self):
        db.save_assessment(50.0, {}, {})
        db.save_assessment(60.0, {}, {})
        n = db.delete_all_assessments()
        self.assertEqual(n, 2)
        self.assertEqual(db.load_assessments(), [])

    def test_empty_load_returns_empty_list(self):
        self.assertEqual(db.load_assessments(), [])

    # ── Task CRUD ──────────────────────────────────────────────────────────
    def test_add_and_load_task(self):
        tid = db.add_task("Enable MFA", "Turn on 2FA", "high", "Account Security")
        self.assertIsInstance(tid, int)
        tasks = db.load_tasks()
        self.assertEqual(len(tasks), 1)
        t = tasks[0]
        self.assertEqual(t["title"], "Enable MFA")
        self.assertEqual(t["priority"], "high")
        self.assertEqual(t["done"], 0)

    def test_toggle_task_done(self):
        tid = db.add_task("Test task")
        db.toggle_task(tid, True)
        tasks = db.load_tasks()
        self.assertEqual(tasks[0]["done"], 1)
        self.assertIsNotNone(tasks[0]["done_at"])

    def test_toggle_task_undone(self):
        tid = db.add_task("Test task")
        db.toggle_task(tid, True)
        db.toggle_task(tid, False)
        tasks = db.load_tasks()
        self.assertEqual(tasks[0]["done"], 0)
        self.assertIsNone(tasks[0]["done_at"])

    def test_delete_task(self):
        tid = db.add_task("To delete")
        db.delete_task(tid)
        self.assertEqual(db.load_tasks(), [])

    def test_delete_all_tasks(self):
        db.add_task("Task 1")
        db.add_task("Task 2")
        n = db.delete_all_tasks()
        self.assertEqual(n, 2)
        self.assertEqual(db.load_tasks(), [])

    def test_seed_tasks_no_duplicates(self):
        recs = [
            {"title": "Enable MFA", "body": "desc", "priority": "critical", "category": "Account Security"},
            {"title": "Use VPN",    "body": "desc", "priority": "high",     "category": "Privacy"},
        ]
        db.seed_tasks_from_recs(recs)
        db.seed_tasks_from_recs(recs)  # second call must not duplicate
        tasks = db.load_tasks()
        titles = [t["title"] for t in tasks]
        self.assertEqual(len(titles), len(set(titles)), "Duplicate tasks were created")

    def test_sql_injection_safe(self):
        """Parameterised queries must not raise on injection-style input."""
        nasty = "' OR '1'='1'; DROP TABLE tasks; --"
        tid = db.add_task(nasty, nasty, "low", nasty)
        tasks = db.load_tasks()
        self.assertEqual(tasks[0]["title"], nasty)
        db.delete_task(tid)


# ══════════════════════════════════════════════════════════════════════════════
#  3. URL Analyzer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestUrlAnalyzer(unittest.TestCase):

    def _codes(self, result) -> set:
        return {f.code for f in result.findings}

    # ── Clean URL ──────────────────────────────────────────────────────────
    def test_clean_https_url(self):
        r = ua.analyze_url("https://www.example.com/page")
        self.assertTrue(r.valid)
        self.assertEqual(r.scheme, "https")
        self.assertNotIn("no_https", self._codes(r))
        self.assertIn(r.verdict, ("clean", "caution", "suspicious"))

    # ── HTTP flagged ───────────────────────────────────────────────────────
    def test_http_flagged(self):
        r = ua.analyze_url("http://www.example.com/login")
        self.assertIn("no_https", self._codes(r))

    # ── IP address ────────────────────────────────────────────────────────
    def test_ip_address_flagged(self):
        r = ua.analyze_url("http://192.168.1.1/admin")
        self.assertIn("ip_address", self._codes(r))

    # ── URL shortener ──────────────────────────────────────────────────────
    def test_url_shortener_flagged(self):
        r = ua.analyze_url("https://bit.ly/3xAbCd")
        self.assertIn("url_shortener", self._codes(r))

    # ── @ in URL ──────────────────────────────────────────────────────────
    def test_at_symbol_flagged(self):
        r = ua.analyze_url("https://paypal.com@evil.com/login")
        self.assertIn("at_in_url", self._codes(r))

    # ── Brand in subdomain ─────────────────────────────────────────────────
    def test_brand_in_subdomain_flagged(self):
        r = ua.analyze_url("https://paypal.com.verify.evil.com/login")
        self.assertIn("brand_in_subdomain", self._codes(r))

    # ── Suspicious TLD ─────────────────────────────────────────────────────
    def test_suspicious_tld_flagged(self):
        r = ua.analyze_url("https://example.tk/page")
        self.assertIn("suspicious_tld", self._codes(r))

    # ── Excessive encoding ─────────────────────────────────────────────────
    def test_heavy_encoding_flagged(self):
        encoded = "https://example.com/" + "%41" * 10
        r = ua.analyze_url(encoded)
        self.assertIn("heavy_encoding", self._codes(r))

    # ── Long URL ──────────────────────────────────────────────────────────
    def test_long_url_flagged(self):
        long_url = "https://example.com/" + "a" * 200
        r = ua.analyze_url(long_url)
        self.assertIn("long_url", self._codes(r))

    # ── Empty input ───────────────────────────────────────────────────────
    def test_empty_input(self):
        r = ua.analyze_url("")
        self.assertFalse(r.valid)
        self.assertIn("empty", self._codes(r))

    # ── Verdict logic ─────────────────────────────────────────────────────
    def test_dangerous_verdict_for_bad_url(self):
        r = ua.analyze_url("http://192.168.1.1@evil.tk/%41%42%43")
        self.assertIn(r.verdict, ("dangerous", "suspicious"))

    def test_verdict_values_are_valid(self):
        valid_verdicts = {"clean", "caution", "suspicious", "dangerous", "unknown"}
        for url in ["https://google.com", "http://192.0.0.1", "", "bit.ly/abc"]:
            r = ua.analyze_url(url)
            self.assertIn(r.verdict, valid_verdicts, f"Invalid verdict for {url!r}")

    # ── Result fields ──────────────────────────────────────────────────────
    def test_result_has_all_fields(self):
        r = ua.analyze_url("https://example.com")
        self.assertIsNotNone(r.raw_url)
        self.assertIsNotNone(r.verdict)
        self.assertIsInstance(r.findings, list)
        self.assertIsInstance(r.danger_count, int)
        self.assertIsInstance(r.warning_count, int)
        self.assertIsInstance(r.score, int)

    def test_no_network_requests(self):
        """Analyzer must complete without any network I/O.
        We verify by patching socket — if it tries to connect it will raise."""
        import socket
        orig = socket.getaddrinfo
        def _no_network(*a, **kw):
            raise AssertionError("URL analyzer made a network call!")
        socket.getaddrinfo = _no_network
        try:
            ua.analyze_url("https://paypal.verify.evil.tk/login?user=test")
        finally:
            socket.getaddrinfo = orig


# ══════════════════════════════════════════════════════════════════════════════
#  4. PDF Report Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPdfReport(unittest.TestCase):

    def _sample_recs(self):
        return [
            {"priority": "critical", "icon": "🔑", "title": "Enable MFA",
             "body": "Turn on multi-factor authentication."},
            {"priority": "high",     "icon": "🔄", "title": "Update Software",
             "body": "Apply all pending OS and app updates."},
            {"priority": "medium",   "icon": "💾", "title": "Set Up Backups",
             "body": "Create automated offsite backups."},
        ]

    def test_pdf_returns_bytes(self):
        pdf = pdf_report.build_pdf(
            overall=65.0,
            cat_scores={"Account Security": 70.0, "Phishing Awareness": 60.0,
                        "Device Security": 65.0, "Privacy": 55.0, "Backup Readiness": 75.0},
            recommendations=self._sample_recs(),
        )
        self.assertIsInstance(pdf, bytes)

    def test_pdf_starts_with_header(self):
        pdf = pdf_report.build_pdf(72.0, {}, [])
        # All PDFs start with %PDF-
        self.assertTrue(pdf[:5] == b"%PDF-", "Output is not a valid PDF")

    def test_pdf_non_empty(self):
        pdf = pdf_report.build_pdf(50.0, {}, self._sample_recs())
        self.assertGreater(len(pdf), 1024, "PDF too small — likely corrupt")

    def test_pdf_with_zero_score(self):
        pdf = pdf_report.build_pdf(0.0, {}, self._sample_recs())
        self.assertTrue(pdf[:5] == b"%PDF-")

    def test_pdf_with_perfect_score(self):
        cat_scores = {cat: 100.0 for cat in sc.CATEGORIES}
        pdf = pdf_report.build_pdf(100.0, cat_scores, [])
        self.assertTrue(pdf[:5] == b"%PDF-")

    def test_pdf_with_all_rec_priorities(self):
        recs = [
            {"priority": p, "icon": "✅", "title": f"{p} title", "body": "body"}
            for p in ["critical", "high", "medium", "low"]
        ]
        pdf = pdf_report.build_pdf(55.0, {}, recs)
        self.assertTrue(pdf[:5] == b"%PDF-")

    def test_pdf_accepts_custom_date(self):
        pdf = pdf_report.build_pdf(75.0, {}, [], taken_at="01 January 2025, 12:00")
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf[:5] == b"%PDF-")


# ══════════════════════════════════════════════════════════════════════════════
#  5. Integration: full assessment → save → load → PDF
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._orig_path = db.DB_PATH
        db.DB_PATH = Path(self._tmp.name)
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self._orig_path
        self._tmp.close()
        try:
            os.unlink(self._tmp.name)
        except Exception:
            pass

    def test_full_workflow(self):
        # 1. Score a realistic mid-range assessment
        answers = _mid_answers()
        result  = sc.compute_score(answers)
        self.assertGreater(result.overall, 0)
        self.assertLess(result.overall, 100)

        # 2. Generate recommendations
        recs = sc.generate_recommendations(answers, result.cat_scores)
        self.assertIsInstance(recs, list)

        # 3. Save to DB
        row_id = db.save_assessment(result.overall, result.cat_scores, answers)
        self.assertGreater(row_id, 0)

        # 4. Reload and verify round-trip
        records = db.load_assessments()
        self.assertEqual(len(records), 1)
        self.assertAlmostEqual(records[0]["overall"], result.overall, places=1)

        # 5. Seed tasks from recs
        db.seed_tasks_from_recs(recs)
        tasks = db.load_tasks()
        self.assertGreater(len(tasks), 0)

        # 6. Toggle a task done
        db.toggle_task(tasks[0]["id"], True)
        reloaded = db.load_tasks()
        done_task = next(t for t in reloaded if t["id"] == tasks[0]["id"])
        self.assertEqual(done_task["done"], 1)

        # 7. Generate PDF
        pdf = pdf_report.build_pdf(result.overall, result.cat_scores, recs)
        self.assertTrue(pdf[:5] == b"%PDF-")

        # 8. Analyze a URL
        url_result = ua.analyze_url("https://www.example.com/secure-page")
        self.assertTrue(url_result.valid)

        # 9. Clean up
        n_assess = db.delete_all_assessments()
        n_tasks  = db.delete_all_tasks()
        self.assertEqual(n_assess, 1)
        self.assertEqual(n_tasks, len(tasks))


# ══════════════════════════════════════════════════════════════════════════════
#  Runner
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [TestScoringEngine, TestDatabase, TestUrlAnalyzer,
                TestPdfReport, TestIntegration]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
