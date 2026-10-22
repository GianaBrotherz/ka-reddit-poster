# ka-reddit-poster

The script that publishes Kreuzberg Audio's own posts to our Reddit user profile, [u/KreuzbergAudio](https://www.reddit.com/user/KreuzbergAudio/). We develop audio plugins in Berlin ([kreuzberg-audio.com](https://kreuzberg-audio.com)).

This repository holds the complete part of our internal tool that talks to the Reddit API, published for Reddit's API review.

## What it does

- Publishes one post per run to r/u_KreuzbergAudio: a title, Markdown text and optionally one video, one image or a gallery of our own images.
- The owner, Frank Hahn, approves every post in our planning tool before the tool runs the script.
- It stores the ID, title and URL of the post it just made in `posted.jsonl`. Nothing else is stored.

## What it does not do

- No posts or comments in communities, no votes, no messages, no follows.
- No reading, storing or scraping of other users' content.
- No AI training, no selling or sharing of Reddit data.

## Limits

- At most one post per day (`MAX_POSTS_PER_DAY`), checked before any request is made.
- A title that was posted before is refused, so nothing is reposted.
- User-Agent: `script:com.kreuzberg-audio.profile-poster:v1.0 (by /u/KreuzbergAudio)`.
- PRAW follows Reddit's rate-limit headers. With `ratelimit_seconds=0` a rate-limit error ends the run instead of waiting and retrying. Any error ends the run with exit code 1 and no retry.

## Use

```
pip install -r requirements.txt
export REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=... REDDIT_USERNAME=KreuzbergAudio REDDIT_PASSWORD=...
python post.py entry.json
```

Credentials live only in the environment of the machine that runs the script, never in this repository.

```json
{"title": "KA-303: morphing between saw and square", "body": "Two paragraphs about the synth.", "media": ["morph.mp4"], "thumbnail": "morph.jpg"}
```

Tests: `pip install pytest && pytest`
