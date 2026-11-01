# SPDX-License-Identifier: MIT
"""Backend services for the XYZ Fetcher desktop tool."""

from __future__ import annotations

import csv
import json
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

import pymongo
from PyQt6.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    QRunnable,
    QThreadPool,
    pyqtSignal,
)

from config import ConfigFile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "data" / "config.toml"


def parse_target(value: str) -> tuple[str | None, str | None]:
    """Return (kind, id) for a Xiaoyuzhou podcast/episode URL or explicit ID."""
    value = value.strip()
    match = re.search(r"xiaoyuzhoufm\.com/(podcast|episode)/([0-9a-fA-F]{24})", value)
    if match:
        return match.group(1), match.group(2).lower()
    match = re.fullmatch(r"(pid|eid)[:=]([0-9a-fA-F]{24})", value, re.IGNORECASE)
    if match:
        kind = "podcast" if match.group(1).lower() == "pid" else "episode"
        return kind, match.group(2).lower()
    return None, None


def format_ms(value: int | float | None, srt: bool = False) -> str:
    total_ms = max(0, int(value or 0))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    if srt:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_duration(seconds: int | float | None) -> str:
    return format_ms((seconds or 0) * 1000)


class Repository:
    """Read-only access to the existing xyz-data MongoDB database."""

    def __init__(self, config_path: Path | str = DEFAULT_CONFIG):
        self.config_path = Path(config_path)
        self.cfg = ConfigFile(str(self.config_path))
        self.cfg.load()
        self.client = pymongo.MongoClient(
            host=self.cfg.database_host,
            port=self.cfg.database_port,
            username=self.cfg.database_username,
            password=self.cfg.database_password,
            authSource=self.cfg.database_auth_source,
            serverSelectionTimeoutMS=3000,
        )
        self.db = self.client[self.cfg.database_database_name]

    @property
    def database_label(self) -> str:
        return (
            f"{self.cfg.database_host}:{self.cfg.database_port}/"
            f"{self.cfg.database_database_name}"
        )

    def test_connection(self) -> str:
        return self.client.server_info()["version"]

    def token_status(self) -> dict:
        token_path = self.config_path.parent / self.cfg.fetcher_token_filename
        result = {
            "path": str(token_path),
            "exists": token_path.exists(),
            "access_token": False,
            "refresh_token": False,
            "modified": "-",
        }
        if token_path.exists():
            tokens = json.loads(token_path.read_text(encoding="utf-8"))
            result["access_token"] = bool(tokens.get("access_token"))
            result["refresh_token"] = bool(tokens.get("refresh_token"))
            result["modified"] = datetime.fromtimestamp(
                token_path.stat().st_mtime
            ).strftime("%Y-%m-%d %H:%M:%S")
        return result

    def list_podcasts(self) -> list[dict]:
        result = []
        for pid in self.db.podcast.distinct("pid"):
            podcast = self.db.podcast.find_one(
                {"pid": pid}, sort=[("__insert_time", -1)]
            )
            if not podcast:
                continue
            result.append(
                {
                    "pid": pid,
                    "title": podcast.get("title") or pid,
                    "brief": podcast.get("brief") or podcast.get("description") or "",
                    "image": (podcast.get("image") or {}).get("smallPicUrl")
                    or (podcast.get("image") or {}).get("picUrl"),
                    "episodes": len(self.db.episode.distinct("eid", {"pid": pid})),
                    "transcripts": len(
                        self.db.transcript.distinct("eid", {"pid": pid})
                    ),
                    "declared_episodes": podcast.get("episodeCount") or 0,
                    "latestEpisodePubDate": podcast.get("latestEpisodePubDate") or "",
                }
            )
        result.sort(key=lambda item: item["latestEpisodePubDate"], reverse=True)
        return result

    def list_episodes(self, pid: str) -> list[dict]:
        pipeline = [
            {"$match": {"pid": pid}},
            {"$sort": {"__insert_time": -1}},
            {
                "$group": {
                    "_id": "$eid",
                    "doc": {"$first": "$$ROOT"},
                }
            },
            {"$replaceRoot": {"newRoot": "$doc"}},
            {
                "$project": {
                    "_id": 0,
                    "eid": 1,
                    "pid": 1,
                    "title": 1,
                    "pubDate": 1,
                    "duration": 1,
                    "commentCount": 1,
                    "transcriptMediaId": 1,
                }
            },
            {"$sort": {"pubDate": -1}},
        ]
        episodes = list(self.db.episode.aggregate(pipeline))
        transcript_eids = set(self.db.transcript.distinct("eid", {"pid": pid}))
        comments = {
            item["_id"]: item["count"]
            for item in self.db.comment.aggregate(
                [
                    {"$match": {"eid": {"$exists": True}}},
                    {"$group": {"_id": "$eid", "count": {"$sum": 1}}},
                ]
            )
            if item["_id"] in {episode["eid"] for episode in episodes}
        }
        for episode in episodes:
            episode["has_transcript"] = episode["eid"] in transcript_eids
            episode["fetched_comments"] = comments.get(episode["eid"], 0)
        return episodes

    def latest_eid(self, pid: str) -> str | None:
        episode = self.db.episode.find_one(
            {"pid": pid}, {"eid": 1}, sort=[("pubDate", -1)]
        )
        return episode.get("eid") if episode else None

    def episode_bundle(self, eid: str) -> dict:
        episode = self.db.episode.find_one(
            {"eid": eid}, sort=[("__insert_time", -1)]
        )
        if not episode:
            raise ValueError(f"未找到节目：{eid}")
        transcript = self.db.transcript.find_one(
            {"eid": eid}, sort=[("__insert_time", -1)]
        )
        comments = list(
            self.db.comment.find({"eid": eid}).sort("_id", 1).limit(5000)
        )
        return {
            "episode": episode,
            "transcript": transcript,
            "comments": comments,
        }

    def close(self):
        self.client.close()


def episode_markdown(bundle: dict) -> str:
    episode = bundle["episode"]
    transcript = bundle.get("transcript")
    comments = bundle.get("comments") or []
    lines = [
        f"# {episode.get('title', episode['eid'])}",
        "",
        f"- 节目链接：https://www.xiaoyuzhoufm.com/episode/{episode['eid']}",
        f"- 发布时间：{episode.get('pubDate', '-')}",
        f"- 时长：{format_duration(episode.get('duration'))}",
        "",
        "## 节目简介",
        "",
        episode.get("description") or "无",
        "",
    ]
    if episode.get("shownotes"):
        lines.extend(["## Shownotes", "", episode["shownotes"], ""])
    lines.extend(["## 逐字稿", ""])
    if transcript:
        if transcript.get("vendorDeclaration"):
            lines.extend([f"> {transcript['vendorDeclaration']}", ""])
        for segment in transcript.get("segments") or []:
            lines.append(f"[{format_ms(segment.get('startMs'))}] {segment.get('text', '')}")
    else:
        lines.append("未抓取逐字稿。")
    lines.extend(["", f"## 评论（{len(comments)}）", ""])
    for comment in comments:
        likes = comment.get("likeCount", 0)
        lines.append(f"- {comment.get('text', '')}（{likes} 赞）")
    return "\n".join(lines) + "\n"


def episode_srt(bundle: dict) -> str:
    transcript = bundle.get("transcript")
    if not transcript:
        return ""
    blocks = []
    segments = transcript.get("segments") or []
    for index, segment in enumerate(segments):
        start = segment.get("startMs") or 0
        end = segment.get("endMs")
        if end is None:
            next_start = (
                segments[index + 1].get("startMs")
                if index + 1 < len(segments)
                else start + 3000
            )
            end = max(start + 500, next_start or start + 3000)
        blocks.append(
            f"{index + 1}\n{format_ms(start, srt=True)} --> "
            f"{format_ms(end, srt=True)}\n{segment.get('text', '')}\n"
        )
    return "\n".join(blocks)


def export_episode(bundle: dict, path: Path | str, fmt: str):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        content = json.dumps(bundle, ensure_ascii=False, indent=2, default=str)
    elif fmt == "srt":
        content = episode_srt(bundle)
    else:
        content = episode_markdown(bundle)
    path.write_text(content, encoding="utf-8")


def export_episode_csv(episodes: list[dict], path: Path | str):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["eid", "title", "pubDate", "duration", "hasTranscript", "fetchedComments"]
        )
        for episode in episodes:
            writer.writerow(
                [
                    episode.get("eid"),
                    episode.get("title"),
                    episode.get("pubDate"),
                    episode.get("duration"),
                    episode.get("has_transcript"),
                    episode.get("fetched_comments"),
                ]
            )


class WorkerSignals(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(str)


class Worker(QRunnable):
    def __init__(self, fn: Callable):
        super().__init__()
        self.fn = fn
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.result.emit(self.fn())
        except Exception as exc:  # surfaced in the UI
            self.signals.error.emit(str(exc))


def run_async(fn: Callable, on_result: Callable, on_error: Callable | None = None):
    worker = Worker(fn)
    worker.signals.result.connect(on_result)
    if on_error:
        worker.signals.error.connect(on_error)
    QThreadPool.globalInstance().start(worker)
    return worker


@dataclass
class TaskOptions:
    fetch_transcripts: bool = True
    comments_mode: str = "none"  # none | latest | all
    episodes_max_count: int = 0


@dataclass
class TaskItem:
    kind: str
    target_id: str
    options: TaskOptions
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    status: str = "等待中"
    stage: int = 1
    log: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    cancel_requested: bool = False

    @property
    def display_name(self) -> str:
        prefix = "播客" if self.kind == "podcast" else "单期"
        return f"{prefix} {self.target_id[:8]}…"


class TaskManager(QObject):
    tasks_changed = pyqtSignal()
    task_output = pyqtSignal(str, str)
    task_finished = pyqtSignal(str, bool)
    data_changed = pyqtSignal()
    active_changed = pyqtSignal(str)

    def __init__(self, repository: Repository):
        super().__init__()
        self.repository = repository
        self.tasks: list[TaskItem] = []
        self.process: QProcess | None = None
        self.current: TaskItem | None = None
        self.shutting_down = False

    def add_task(self, kind: str, target_id: str, options: TaskOptions) -> TaskItem:
        item = TaskItem(kind=kind, target_id=target_id, options=options)
        self.tasks.append(item)
        self.tasks_changed.emit()
        self._start_next()
        return item

    def cancel_task(self, task_id: str):
        item = next((task for task in self.tasks if task.id == task_id), None)
        if not item:
            return
        if item.status == "等待中":
            item.status = "已取消"
            self.tasks_changed.emit()
        elif item == self.current and self.process:
            item.cancel_requested = True
            item.status = "正在取消"
            self.tasks_changed.emit()
            self.process.kill()

    def clear_finished(self):
        self.tasks = [
            task
            for task in self.tasks
            if task.status in {"等待中", "运行中", "正在取消"}
        ]
        self.tasks_changed.emit()

    def shutdown(self):
        """Stop the active child process and prevent queued tasks from starting."""
        self.shutting_down = True
        for task in self.tasks:
            if task.status == "等待中":
                task.status = "已取消"
        if self.process is not None:
            if self.current:
                self.current.cancel_requested = True
            self.process.kill()
            self.process.waitForFinished(3000)
        self.tasks_changed.emit()

    def _start_next(self):
        if self.shutting_down or self.process is not None:
            return
        item = next((task for task in self.tasks if task.status == "等待中"), None)
        if item is None:
            self.current = None
            self.active_changed.emit("")
            return
        self.current = item
        item.status = "运行中"
        item.stage = 1
        self.active_changed.emit(item.id)
        self.tasks_changed.emit()
        self._start_process(item)

    def _arguments(self, item: TaskItem) -> list[str]:
        args = [str(PROJECT_ROOT / "src" / "main.py"), str(DEFAULT_CONFIG)]
        if item.stage == 2:
            latest_eid = self.repository.latest_eid(item.target_id)
            if not latest_eid:
                raise RuntimeError("无法确定最新一期，评论阶段未启动")
            args.extend([f"--eid={latest_eid}", "--no-fetch-transcripts"])
            return args
        if item.kind == "podcast":
            args.append(f"--pid={item.target_id}")
            if item.options.episodes_max_count:
                args.append(
                    f"--episodes-max-count={item.options.episodes_max_count}"
                )
        else:
            args.append(f"--eid={item.target_id}")
        if not item.options.fetch_transcripts:
            args.append("--no-fetch-transcripts")
        if item.options.comments_mode == "none" or (
            item.kind == "podcast" and item.options.comments_mode == "latest"
        ):
            args.append("--no-fetch-comments")
        return args

    def _start_process(self, item: TaskItem):
        try:
            arguments = self._arguments(item)
        except Exception as exc:
            self._append_log(item, f"\n{exc}\n")
            self._finish_current(False)
            return
        process = QProcess(self)
        process.setWorkingDirectory(str(PROJECT_ROOT))
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONUNBUFFERED", "1")
        environment.insert("PYTHONIOENCODING", "utf-8")
        process.setProcessEnvironment(environment)
        process.setProgram(sys.executable)
        process.setArguments(arguments)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(
            lambda: self._read_output(process)
        )
        process.finished.connect(self._process_finished)
        process.errorOccurred.connect(self._process_error)
        self.process = process
        self._append_log(
            item,
            f"\n--- 阶段 {item.stage}：{'抓取最新一期评论' if item.stage == 2 else '抓取节目数据'} ---\n",
        )
        process.start()

    def _read_output(self, process: QProcess):
        text = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if self.current:
            self._append_log(self.current, text)

    def _append_log(self, item: TaskItem, text: str):
        item.log += text
        if len(item.log) > 500_000:
            item.log = item.log[-400_000:]
        self.task_output.emit(item.id, text)

    def _process_error(self, error: QProcess.ProcessError):
        if error == QProcess.ProcessError.FailedToStart and self.current:
            process = self.process
            self.process = None
            if process:
                process.deleteLater()
            self._append_log(self.current, "\n无法启动 Python 子进程。\n")
            self._finish_current(False)

    def _process_finished(self, exit_code: int, _exit_status):
        if self.sender() is not self.process:
            return
        process = self.process
        if process:
            self._read_output(process)
            process.deleteLater()
        self.process = None
        item = self.current
        if not item:
            return
        success = exit_code == 0 and not item.cancel_requested
        if (
            success
            and item.kind == "podcast"
            and item.options.comments_mode == "latest"
            and item.stage == 1
        ):
            item.stage = 2
            self._append_log(item, "\n节目阶段完成，开始抓取最新一期评论。\n")
            self.tasks_changed.emit()
            self._start_process(item)
            return
        self._finish_current(success)

    def _finish_current(self, success: bool):
        item = self.current
        if not item:
            return
        if item.cancel_requested:
            item.status = "已取消"
        else:
            item.status = "已完成" if success else "失败"
        self._append_log(item, f"\n任务结束：{item.status}\n")
        self.tasks_changed.emit()
        self.task_finished.emit(item.id, success)
        self.data_changed.emit()
        self.current = None
        self._start_next()
