import logging
import time

from django.core.management.base import BaseCommand

from biostar.accounts.models import User, Profile
from biostar.forum import util
from biostar.forum.models import Post, Vote, Subscription, Badge, Award
from biostar.transfer.models import UsersUser, PostsPost, PostsVote, PostsSubscription, BadgesAward

logger = logging.getLogger("engine")
from itertools import count, islice

LIMIT = None


def timer_func():
    """
    Prints progress on inserting elements.
    """

    last = time.time()

    def elapsed(msg):
        nonlocal last
        now = time.time()
        sec = round(now - last, 1)
        last = now
        print(f"{msg} in {sec} seconds")

    def progress(index, step=5000, msg=""):
        nonlocal last
        if index % step == 0:
            elapsed(f"... {index} {msg}")

    return elapsed, progress


def bulk_copy_users():
    def gen_users():
        logger.info(f"Transferring users")

        users = UsersUser.objects.order_by("id")
        # Only iterate over users that do not exist already

        elapsed, progress = timer_func()

        # Allow limiting the input
        stream = islice(zip(count(1), users), LIMIT)

        for index, user in stream:
            progress(index, msg="users")
            username = f"{user.name}{user.id}"
            # Create user
            user = User(username=username, email=user.email, password=user.password,
                        is_active=user.is_active, is_superuser=user.is_admin, is_staff=user.is_staff)
            yield user

    def gen_profile():
        logger.info(f"Transferring profiles")

        current = {user.email: user for user in User.objects.filter(profile=None)}

        # Exclude existing users from source database.
        users = UsersUser.objects.all().order_by("id")

        elapsed, progress = timer_func()

        # Allow limiting the input
        stream = islice(zip(count(1), users), LIMIT)

        for index, user in stream:
            progress(index, msg="profiles")
            text = util.strip_tags(user.profile.info)
            profile = Profile(uid=user.id, user=current.get(user.email), name=user.name,
                              role=user.type, last_login=user.last_login, html=user.profile.info,
                              date_joined=user.profile.date_joined, location=user.profile.location,
                              website=user.profile.website, scholar=user.profile.scholar, text=text,
                              score=user.score, twitter=user.profile.twitter_id, my_tags=user.profile.my_tags,
                              digest_prefs=user.profile.digest_prefs, new_messages=user.new_messages)

            yield profile

    def gen_awards():

        # Query the badges
        badges = {badge.name: badge for badge in Badge.objects.all()}
        # Query users
        users = {profile.uid: profile.user for profile in Profile.objects.all()}
        # exists = list( Award.objects.values_list("uid", flat=True) )
        source = BadgesAward.objects.all()

        stream = zip(count(1), source)
        stream = islice(stream, LIMIT)

        elapsed, progress = timer_func()
        for index, award in stream:
            progress(index, msg="awards")
            badge = badges[award.badge.name]
            user = users.get(str(award.user_id))
            if not user:
                continue
            award = Award(date=award.date, context=award.context, badge=badge,
                          user=user, uid=award.id)

            yield award

    # Bulk create the users, then profile.
    elapsed, progress = timer_func()

    User.objects.bulk_create(objs=gen_users(), batch_size=10000)
    ucount = User.objects.all().count()
    elapsed(f"transferred {ucount} users")

    Profile.objects.bulk_create(objs=gen_profile(), batch_size=10000)
    pcount = Profile.objects.all().count()
    elapsed(f"transferred {pcount} profiles")

    Award.objects.bulk_create(objs=gen_awards(), batch_size=10000)
    acount = Award.objects.all().count()
    elapsed(f"transferred {acount} awards")


def bulk_copy_votes():
    exists = list(Vote.objects.values_list("uid", flat=True))
    exists = filter(lambda uid: uid.isdigit(), exists)
    source = PostsVote.objects.exclude(id__in=exists)

    def gen_votes():
        posts = {post.uid: post for post in Post.objects.all()}
        users = {user.profile.uid: user for user in User.objects.all()}

        for vote in source:

            post = posts.get(str(vote.post_id))
            author = users.get(str(vote.author_id))
            # Skip if post or author do not exist
            if not (post and author):
                continue

            vote = Vote(post=post, author=author, type=vote.type, uid=vote.id,
                        date=vote.date)
            yield vote

    Vote.objects.bulk_create(objs=gen_votes(), batch_size=1000)

    logger.info("Copied all votes from biostar2")


def bulk_copy_posts():
    relations = {}
    all_users = User.objects.all()

    # Walk through tree and update parent, root, post, relationships
    def gen_posts():
        logger.info("transferring posts")

        exists = list(Post.objects.values_list("uid", flat=True))
        exists = [int(post_uid) for post_uid in exists if post_uid.isdigit()]

        posts = PostsPost.objects.exclude(id__in=exists)
        users = {user.profile.uid: user for user in all_users}

        elapsed, progress = timer_func()

        stream = islice(zip(count(1), posts), LIMIT)

        for index, post in stream:
            progress(index, msg="posts")

            author = users.get(str(post.author_id))
            lastedit_user = users.get(str(post.lastedit_user_id))

            # Incomplete author information loaded.
            if not author or lastedit_user:
                continue

            content = util.strip_tags(post.content)
            new_post = Post(uid=post.id, html=post.html, type=post.type,
                            lastedit_user=lastedit_user, thread_votecount=post.thread_score,
                            author=author, status=post.status, rank=post.rank, has_accepted=post.has_accepted,
                            lastedit_date=post.lastedit_date, book_count=post.book_count, reply_count=post.reply_count,
                            content=content, title=post.title, vote_count=post.vote_count,
                            thread_score=post.reply_count,
                            creation_date=post.creation_date, tag_val=post.tag_val,
                            view_count=post.view_count)

            # Store parent and root for every post.
            relations[str(new_post.uid)] = [str(post.root_id), str(post.parent_id)]
            yield new_post

        logger.info("Copied all posts from biostar2")

    def gen_updates():
        logger.info("Updating post relations")
        posts = {post.uid: post for post in Post.objects.all()}
        for post_uid in relations:
            root_uid, parent_uid = relations[post_uid][0], relations[post_uid][1]
            post = posts[post_uid]
            root = posts.get(root_uid)
            parent = posts.get(parent_uid)
            if not (root and parent):
                continue
            post.root = root
            post.parent = parent
            yield post

        logger.info("Updated all posts from biostar2")

    def update_threadusers():
        logger.info("Updating thread users.")
        roots = Post.objects.filter(type__in=Post.TOP_LEVEL)
        roots = {root: Post.objects.filter(root=root) for root in roots}

        roots = {post: User.objects.filter(pk__in=roots[post].values_list("author")) for post in roots}

        for post in roots:
            users = roots[post]
            if post.root.thread_users.filter(pk__in=users):
                continue

            post.thread_users.add(*users)

    elapsed, progress = timer_func()
    Post.objects.bulk_create(objs=gen_posts(), batch_size=1000)
    pcount = User.objects.all().count()
    elapsed(f"transferred {pcount} posts")

    Post.objects.bulk_update(objs=gen_updates(), fields=["root", "parent"], batch_size=1000)
    update_threadusers()
    elapsed(f"updated {pcount} post threads")

def bulk_copy_subs():
    def generate():
        users = {user.profile.uid: user for user in User.objects.all()}
        posts = {post.uid: post for post in Post.objects.all()}
        exists = list(Subscription.objects.values_list("uid", flat=True))
        exists = filter(lambda uid: uid.isdigit(), exists)
        source = PostsSubscription.objects.exclude(id__in=exists)
        logger.info("Copying subscriptions")
        for subs in source:
            user = users[str(subs.user_id)]
            post = posts[str(subs.post_id)]
            sub = Subscription(uid=subs.id, type=subs.type, user=user, post=post, date=subs.date)

            yield sub

    def update_counts():
        logger.info("Updating post subs_count")
        # Recompute subs_count for
        posts = {post: post.subs.exclude(user=post.author).count() for post in Post.objects.all()}
        for post in posts:
            post.subs_count = posts[post]
            yield post

    Subscription.objects.bulk_create(objs=generate(), batch_size=1000)
    Post.objects.bulk_update(objs=update_counts(), fields=["subs_count"], batch_size=1000)

    logger.info("Load all subscriptions")
    return


class Command(BaseCommand):
    help = "Migrate users from one database to another."

    def add_arguments(self, parser):
        # Give the database file
        parser.add_argument('--posts', action="store_true", help="Transfer posts from source database to target.")
        parser.add_argument('--users', action="store_true", help="Transfer users from source database to target.")
        parser.add_argument('--votes', action="store_true", help="Transfer votes from source database to target.")
        parser.add_argument('--subs', action="store_true", help="Transfer subs from source database to target.")
        pass

    def handle(self, *args, **options):

        load_posts = options["posts"]
        load_users = options["users"]
        load_votes = options["votes"]
        load_subs = options["subs"]

        if load_posts:
            bulk_copy_posts()
            return
        if load_votes:
            bulk_copy_votes()
            return
        if load_users:
            bulk_copy_users()
            return
        if load_subs:
            bulk_copy_subs()
            return

        # Copy everything
        bulk_copy_users()

        bulk_copy_posts()

        bulk_copy_votes()

        bulk_copy_subs()

        return