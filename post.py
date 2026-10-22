"""Publish one approved post to the Reddit user profile u/KreuzbergAudio.

Kreuzberg Audio (https://kreuzberg-audio.com) develops audio plugins in Berlin. Our
internal planning tool runs this script after the owner, Frank Hahn, has approved a
post. One run publishes one post to our own profile and does nothing else: no posts or
comments in communities, no votes, no messages, no reading of other users' content.

    python post.py entry.json

entry.json:

    {"title": "...", "body": "Markdown text", "media": ["clip.mp4"], "thumbnail": "clip.jpg"}

"media" is optional: one video (needs "thumbnail"), one image, or 2 to 20 images as a
gallery. Credentials come from environment variables (REDDIT_CLIENT_ID,
REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD), never from this repository.
"""

import datetime as dt
import json
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

PROFILE = "u_KreuzbergAudio"
USER_AGENT = "script:com.kreuzberg-audio.profile-poster:v1.0 (by /u/KreuzbergAudio)"
MAX_POSTS_PER_DAY = 1
TZ = ZoneInfo("Europe/Berlin")
LOG = Path(os.environ.get("POSTER_LOG", "posted.jsonl"))
VIDEO = {".mp4", ".mov"}
IMAGE = {".jpg", ".jpeg", ".png", ".gif"}


class Refused(Exception):
    """Not sent. The script made no request to Reddit."""


def read_log(log):
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def kind(path):
    suffix = path.suffix.lower()
    return "video" if suffix in VIDEO else "image" if suffix in IMAGE else "other"


def check(entry, log, today):
    done = read_log(log)
    if sum(1 for p in done if p["date"] == today) >= MAX_POSTS_PER_DAY:
        raise Refused(f"already {MAX_POSTS_PER_DAY} post(s) today")
    title = str(entry.get("title", "")).strip()
    if not title or len(title) > 300:
        raise Refused("title missing or longer than 300 characters")
    if any(p["title"] == title for p in done):
        raise Refused("this title was posted before, no reposts")
    media = [Path(m) for m in entry.get("media", [])]
    for m in media:
        if not m.is_file():
            raise Refused(f"file not found: {m}")
    kinds = {kind(m) for m in media}
    if "other" in kinds or len(kinds) > 1 or len(media) > 20 or ("video" in kinds and len(media) > 1):
        raise Refused("media must be one video, one image or 2 to 20 images")
    if "video" in kinds and not Path(entry.get("thumbnail", "")).is_file():
        raise Refused("a video needs a thumbnail image")
    return title, str(entry.get("body", "")), media, kinds


def media_args(media, kinds, thumbnail):
    from praw.models import PostMedia

    if not media:
        return {}
    if "video" in kinds:
        return {"video": {"media": PostMedia(str(media[0])), "thumbnail": PostMedia(thumbnail)}}
    if len(media) == 1:
        return {"image": PostMedia(str(media[0]))}
    return {"gallery": [PostMedia(str(m)) for m in media]}


def client():
    import praw

    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
        user_agent=USER_AGENT,
        ratelimit_seconds=0,  # on a rate limit, stop instead of waiting and retrying
    )


def publish(entry, reddit=None, log=None, now=None):
    log = log or LOG
    today = (now or dt.datetime.now(TZ)).date().isoformat()
    title, body, media, kinds = check(entry, log, today)
    reddit = reddit or client()
    submission = reddit.subreddit(PROFILE).submit(
        title, selftext=body, **media_args(media, kinds, entry.get("thumbnail"))
    )
    url = "https://www.reddit.com" + submission.permalink
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"date": today, "id": submission.id, "title": title, "url": url}) + "\n")
    return url


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        print(publish(json.loads(Path(argv[1]).read_text(encoding="utf-8"))))
    except Exception as e:  # no retry: report and stop
        print(f"not posted: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
