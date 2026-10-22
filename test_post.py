import datetime as dt
import json

import pytest

import post

NOW = dt.datetime(2026, 10, 23, 17, 0, tzinfo=post.TZ)


class FakeSubmission:
    id = "abc123"
    permalink = "/user/KreuzbergAudio/comments/abc123/test/"


class FakeReddit:
    def __init__(self):
        self.calls = []

    def subreddit(self, name):
        self.calls.append(("subreddit", name))
        return self

    def submit(self, title, **kwargs):
        self.calls.append(("submit", title, kwargs))
        return FakeSubmission()


@pytest.fixture
def log(tmp_path):
    return tmp_path / "posted.jsonl"


def test_text_post_goes_to_own_profile_and_is_logged(log):
    reddit = FakeReddit()
    url = post.publish({"title": "KA-303 morph", "body": "Saw to square."}, reddit, log, NOW)
    assert url == "https://www.reddit.com/user/KreuzbergAudio/comments/abc123/test/"
    assert reddit.calls[0] == ("subreddit", "u_KreuzbergAudio")
    assert reddit.calls[1] == ("submit", "KA-303 morph", {"selftext": "Saw to square."})
    assert json.loads(log.read_text())["date"] == "2026-10-23"


def test_second_post_on_same_day_is_refused_without_request(log):
    post.publish({"title": "one"}, FakeReddit(), log, NOW)
    reddit = FakeReddit()
    with pytest.raises(post.Refused, match="today"):
        post.publish({"title": "two"}, reddit, log, NOW)
    assert reddit.calls == []


def test_same_title_is_never_reposted(log):
    post.publish({"title": "one"}, FakeReddit(), log, NOW)
    with pytest.raises(post.Refused, match="reposts"):
        post.publish({"title": "one"}, FakeReddit(), log, NOW + dt.timedelta(days=1))


def test_media_kinds(tmp_path, log):
    clip, still, a, b = (tmp_path / n for n in ("c.mp4", "c.jpg", "a.png", "b.png"))
    for f in (clip, still, a, b):
        f.write_bytes(b"x")
    kinds = lambda entry: set(post.media_args(*post.check(entry, log, "2026-10-23")[2:], entry.get("thumbnail")))
    assert kinds({"title": "v", "media": [str(clip)], "thumbnail": str(still)}) == {"video"}
    assert kinds({"title": "i", "media": [str(a)]}) == {"image"}
    assert kinds({"title": "g", "media": [str(a), str(b)]}) == {"gallery"}
    with pytest.raises(post.Refused, match="thumbnail"):
        post.check({"title": "v", "media": [str(clip)]}, log, "2026-10-23")
    with pytest.raises(post.Refused, match="one video"):
        post.check({"title": "m", "media": [str(clip), str(a)]}, log, "2026-10-23")


def test_error_stops_without_retry(log, monkeypatch, tmp_path, capsys):
    class Broken(FakeReddit):
        def submit(self, title, **kwargs):
            self.calls.append("submit")
            raise RuntimeError("RATELIMIT")

    broken = Broken()
    monkeypatch.setattr(post, "client", lambda: broken)
    monkeypatch.setattr(post, "LOG", log)
    entry = tmp_path / "entry.json"
    entry.write_text(json.dumps({"title": "x"}))
    assert post.main(["post.py", str(entry)]) == 1
    assert broken.calls.count("submit") == 1
    assert not log.exists()
    assert "not posted" in capsys.readouterr().err
