# SPDX-License-Identifier: MIT

import json
import tempfile
import unittest
from pathlib import Path

from gui_app.backend import (
    episode_markdown,
    episode_srt,
    export_episode,
    export_episode_csv,
    format_ms,
    parse_target,
    TaskManager,
    TaskOptions,
)


class TargetParsingTests(unittest.TestCase):
    def test_podcast_url(self):
        self.assertEqual(
            parse_target("https://www.xiaoyuzhoufm.com/podcast/5e5c52c9418a84a04625e6cc"),
            ("podcast", "5e5c52c9418a84a04625e6cc"),
        )

    def test_episode_url_with_query(self):
        self.assertEqual(
            parse_target("https://www.xiaoyuzhoufm.com/episode/6ae27fabe9f449d465057f00?from=share"),
            ("episode", "6ae27fabe9f449d465057f00"),
        )

    def test_explicit_id(self):
        self.assertEqual(
            parse_target("eid:6AE27FABE9F449D465057F00"),
            ("episode", "6ae27fabe9f449d465057f00"),
        )

    def test_invalid_input(self):
        self.assertEqual(parse_target("not a url"), (None, None))


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.bundle = {
            "episode": {
                "eid": "e" * 24,
                "pid": "p" * 24,
                "title": "测试节目",
                "pubDate": "2026-01-02T03:04:05.000Z",
                "duration": 65,
                "description": "简介",
            },
            "transcript": {
                "vendorDeclaration": "测试文稿",
                "segments": [
                    {"startMs": 0, "text": "第一段"},
                    {"startMs": 1500, "text": "第二段"},
                ],
            },
            "comments": [{"id": "c1", "text": "评论", "likeCount": 2}],
        }

    def test_format_ms(self):
        self.assertEqual(format_ms(65_000), "01:05")
        self.assertEqual(format_ms(3_665_007, srt=True), "01:01:05,007")

    def test_markdown(self):
        content = episode_markdown(self.bundle)
        self.assertIn("# 测试节目", content)
        self.assertIn("[00:00] 第一段", content)
        self.assertIn("评论（1）", content)

    def test_srt(self):
        content = episode_srt(self.bundle)
        self.assertIn("00:00:00,000 --> 00:00:01,500", content)
        self.assertIn("第二段", content)

    def test_export_json_and_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "episode.json"
            export_episode(self.bundle, json_path, "json")
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["episode"]["title"], "测试节目")
            csv_path = Path(directory) / "episodes.csv"
            export_episode_csv(
                [{"eid": "e1", "title": "标题", "has_transcript": True}], csv_path
            )
            self.assertIn("e1", csv_path.read_text(encoding="utf-8-sig"))


class TaskArgumentTests(unittest.TestCase):
    def setUp(self):
        self.manager = TaskManager(repository=None)
        self.manager.shutting_down = True  # inspect arguments without starting subprocesses

    def test_latest_comments_uses_no_comments_in_first_stage(self):
        item = self.manager.add_task(
            "podcast", "p" * 24, TaskOptions(comments_mode="latest")
        )
        args = self.manager._arguments(item)
        self.assertIn("--no-fetch-comments", args)
        self.assertNotIn("--no-fetch-transcripts", args)

    def test_all_comments_and_episode_limit(self):
        item = self.manager.add_task(
            "podcast", "p" * 24, TaskOptions(comments_mode="all", episodes_max_count=40)
        )
        args = self.manager._arguments(item)
        self.assertNotIn("--no-fetch-comments", args)
        self.assertIn("--episodes-max-count=40", args)

    def test_single_episode_without_transcript(self):
        item = self.manager.add_task(
            "episode", "e" * 24, TaskOptions(fetch_transcripts=False, comments_mode="all")
        )
        args = self.manager._arguments(item)
        self.assertIn(f"--eid={'e' * 24}", args)
        self.assertIn("--no-fetch-transcripts", args)
        self.assertNotIn("--no-fetch-comments", args)


if __name__ == "__main__":
    unittest.main()
