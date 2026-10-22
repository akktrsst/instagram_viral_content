import argparse
import sys

from sqlalchemy import select

from app.services.gemini import GenerationUnavailable
from bot.db.models import Post
from bot.db.session import get_session, init_db
from bot.media.ai_images import MediaError
from bot.posts import PostStateError, approve_post, create_post, reject_post
from bot.skills import SkillError
from bot.writer.writer import compose_caption


def make(args: argparse.Namespace) -> int:
    print(f"Writing a {args.format} about {args.topic!r}...")
    init_db()
    with get_session() as session:
        try:
            post = create_post(
                session,
                args.topic,
                args.format,
                tier=args.tier,
                render=not args.no_render,
                skill_id=args.skill,
                target_seconds=args.seconds,
                language=args.language,
                style=args.style,
                progress=lambda step, percent, message: print(f"  [{percent:3d}%] {message}"),
            )
        except (GenerationUnavailable, MediaError, SkillError) as exc:
            print(f"Generation failed: {exc}", file=sys.stderr)
            return 1

    print(f"\nPost #{post.id} saved as draft")
    for path in post.media_paths:
        print(f"  {path}")
    if post.collaborators:
        print(f"Suggested collaborators: {', '.join('@' + c for c in post.collaborators)}")
        print("  (only invited if you pass them to `approve --collab`)")
    if post.manual_post:
        print("Needs a trending sound: post this reel manually from the Instagram app.")
    print(f"\n{compose_caption(post.caption, post.hashtags)}")
    return 0


def list_posts(args: argparse.Namespace) -> int:
    init_db()
    query = select(Post).order_by(Post.id.desc()).limit(args.limit)
    if args.status:
        query = query.where(Post.status == args.status)
    with get_session() as session:
        for post in session.scalars(query):
            print(f"#{post.id:<4} {post.status:<10} {post.format:<9} {post.topic[:60]}")
    return 0


def approve(args: argparse.Namespace) -> int:
    with get_session() as session:
        post = _get_post(session, args.post_id)
        if post is None:
            return _fail(f"Post #{args.post_id} not found.", None)
        suggested = post.collaborators
        try:
            approve_post(session, post, args.collab)
        except PostStateError as exc:
            return _fail(str(exc), None)
        print(f"Post #{post.id} approved.")
        print(f"Collaborators to invite: {', '.join(post.collaborators) or 'none'}")
        if suggested and not args.collab:
            print(f"(Gemini suggested {', '.join(suggested)}; pass --collab to invite them.)")
    return 0


def reject(args: argparse.Namespace) -> int:
    with get_session() as session:
        post = _get_post(session, args.post_id)
        if post is None:
            return _fail(f"Post #{args.post_id} not found.", None)
        try:
            reject_post(session, post)
        except PostStateError as exc:
            return _fail(str(exc), None)
    print(f"Post #{args.post_id} rejected.")
    return 0


def publish(args: argparse.Namespace) -> int:
    from bot.publisher.graph_api import InstagramError
    from bot.publisher.publish import publish_post

    with get_session() as session:
        post = _get_post(session, args.post_id)
        if post is None:
            return _fail(f"Post #{args.post_id} not found.", None)
        try:
            media_id = publish_post(session, post)
        except InstagramError as exc:
            print(f"Publish failed: {exc}", file=sys.stderr)
            return 1
    print(f"Post #{args.post_id} published to Instagram (media id {media_id}).")
    return 0


def ig_check(args: argparse.Namespace) -> int:
    from bot.publisher.graph_api import InstagramClient, InstagramError

    try:
        client = InstagramClient()
        account = client.account()
        limit = client.publishing_limit()
    except InstagramError as exc:
        print(f"Instagram check failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Connected as @{account.get('username')} ({account.get('account_type')}), "
        f"user id {account.get('user_id')}"
    )
    if account.get("user_id") and str(account["user_id"]) != str(client.user_id):
        print(f"Warning: IG_USER_ID in .env should be {account['user_id']}.")
    quota = limit.get("config", {}).get("quota_total")
    print(f"Posts published in the last 24h: {limit.get('quota_usage', '?')} / {quota or '?'}")
    return 0


def sync(args: argparse.Namespace) -> int:
    from bot.analytics.insights import sync_insights
    from bot.publisher.graph_api import InstagramError

    init_db()
    with get_session() as session:
        try:
            result = sync_insights(session)
        except InstagramError as exc:
            print(f"Sync failed: {exc}", file=sys.stderr)
            return 1
    print(f"Synced: {result['followers']} followers, {result['media_synced']} posts.")
    return 0


def run_job(args: argparse.Namespace) -> int:
    import logging

    from bot.jobs import run

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run(args.post_id, args.render_only)
    return 0


def list_skills_cmd(args: argparse.Namespace) -> int:
    from bot.skills import list_skills

    init_db()
    with get_session() as session:
        for skill in list_skills(session):
            origin = "built-in" if skill.builtin else "custom"
            print(f"{skill.id:<22} {skill.kind:<10} {origin:<9} {skill.name}")
    return 0


def create_skill_cmd(args: argparse.Namespace) -> int:
    from bot.skills import create_skill

    init_db()
    with get_session() as session:
        try:
            skill = create_skill(session, args.description)
        except GenerationUnavailable as exc:
            print(f"Couldn't create the skill: {exc}", file=sys.stderr)
            return 1
    print(f"Created skill '{skill.name}' ({skill.id}, {skill.kind})\n\n{skill.instructions}")
    return 0


def _get_post(session, post_id: int) -> Post | None:
    init_db()
    return session.get(Post, post_id)


def _fail(message: str, post: Post | None) -> int:
    suffix = f" (status: {post.status})" if post else ""
    print(message + suffix, file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bot", description="Instagram content bot")
    commands = parser.add_subparsers(dest="command", required=True)

    make_cmd = commands.add_parser("make", help="Write and render a post from a topic")
    make_cmd.add_argument("topic")
    make_cmd.add_argument(
        "-f",
        "--format",
        choices=["carousel", "image", "photo", "reel", "explainer", "story"],
        default="carousel",
    )
    make_cmd.add_argument("--skill", help="Skill id (see `skills list`)")
    make_cmd.add_argument(
        "--style",
        choices=["cinematic", "movie"],
        help="Story videos: cinematic (stills + motion) or movie (all real clips, lip-sync)",
    )
    make_cmd.add_argument(
        "--language", help="Language code, e.g. hi, bho, hinglish, ta (default: match the brief)"
    )
    make_cmd.add_argument(
        "--seconds", type=int, help="Story video length, 20-120 seconds (story format only)"
    )
    make_cmd.add_argument("--tier", choices=["lite", "standard", "pro"], help="Override the model")
    make_cmd.add_argument("--no-render", action="store_true", help="Skip image rendering")
    make_cmd.set_defaults(func=make)

    list_cmd = commands.add_parser("list", help="List saved posts")
    list_cmd.add_argument("--status")
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.set_defaults(func=list_posts)

    approve_cmd = commands.add_parser("approve", help="Approve a draft for publishing")
    approve_cmd.add_argument("post_id", type=int)
    approve_cmd.add_argument(
        "--collab", action="append", help="Username to invite as collaborator (repeat, max 3)"
    )
    approve_cmd.set_defaults(func=approve)

    reject_cmd = commands.add_parser("reject", help="Reject a draft")
    reject_cmd.add_argument("post_id", type=int)
    reject_cmd.set_defaults(func=reject)

    publish_cmd = commands.add_parser("publish", help="Publish an approved post to Instagram")
    publish_cmd.add_argument("post_id", type=int)
    publish_cmd.set_defaults(func=publish)

    check_cmd = commands.add_parser("ig-check", help="Verify the Instagram token and quota")
    check_cmd.set_defaults(func=ig_check)

    sync_cmd = commands.add_parser("sync-insights", help="Snapshot account and post insights")
    sync_cmd.set_defaults(func=sync)

    skills_cmd = commands.add_parser("skills", help="List or create content skills")
    skills_sub = skills_cmd.add_subparsers(dest="skills_command", required=True)
    skills_sub.add_parser("list", help="List skills").set_defaults(func=list_skills_cmd)
    new_skill = skills_sub.add_parser("create", help="Design a new skill from a description")
    new_skill.add_argument("description")
    new_skill.set_defaults(func=create_skill_cmd)

    job_cmd = commands.add_parser("run-job", help="Generate one post (used by the cloud job)")
    job_cmd.add_argument("post_id", type=int)
    job_cmd.add_argument("--render-only", action="store_true")
    job_cmd.set_defaults(func=run_job)

    init_cmd = commands.add_parser("init-db", help="Create database tables")
    init_cmd.set_defaults(func=lambda _: (init_db(), print("Tables ready."))[0] or 0)

    args = parser.parse_args(argv)
    return args.func(args)
