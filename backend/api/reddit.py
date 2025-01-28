import logging
from datetime import datetime, timedelta
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pytz
import praw
from tqdm import tqdm

from backend.api.consts import REDDIT_APP_NAME, REDDIT_CLIENT_ID, REDDIT_SECRET

logger = logging.getLogger(__name__)


@dataclass
class RedditPostConfig:
    """Configuration for Reddit post collection.

    Attributes:
        hot_posts_limit: Number of hot posts to fetch initially
        top_comments_limit: Number of top comments to fetch per post
        posts_per_subreddit: Number of top posts to keep per subreddit
        time_window: Time window for post collection in hours
    """
    hot_posts_limit: int = 50
    top_comments_limit: int = 5
    posts_per_subreddit: int = 10
    time_window: int = 24


class RedditPost:
    """Represents a Reddit post with its content and comments."""

    def __init__(self, post: praw.models.Submission):
        self.post = post
        self.text = self._get_readable_format()

    def _get_readable_format(self, top_n_comments: int = 5) -> str:
        """Get post content with top comments in a readable format for LLM processing."""
        try:
            self.post.comments.replace_more(limit=0)
            top_comments = [
                f"Comment {i+1}: {self._replace_links(comment.body)}"
                for i, comment in enumerate(self.post.comments[:top_n_comments])
            ]

            post_content = (
                f"Title: {self.post.title}\n\n"
                f"Content:\n{self.post.selftext}\n\n"
                f"Top {len(top_comments)} comments:\n"
                + "\n".join(top_comments)
            )
            return post_content

        except Exception as e:
            logger.error("Failed to format post %s: %s", self.post.url, str(e))
            return f"Title: {self.post.title}\n\nContent:\n{self.post.selftext}"

    def _replace_links(self, text, replacement="<outgoing_link>"):
        # Define a regex pattern to match URLs starting with https
        url_pattern = re.compile(r'https://\S+')
        # Use the sub() method to replace URLs with the specified replacement text
        text_with_replaced_links = url_pattern.sub(replacement, text)
        return text_with_replaced_links

    def to_dict(self) -> Dict[str, Any]:
        return {
            'subreddit': self.post.subreddit.display_name,
            'title': self.post.title,
            'author': str(self.post.author),
            'score': self.post.score,
            'num_comments': self.post.num_comments,
            'created_utc': datetime.fromtimestamp(self.post.created_utc, pytz.utc),
            'text': self.post.selftext,
            'url': self.post.url
        }


class RedditScraper:
    """Handles Reddit post collection and filtering."""

    def __init__(
        self,
        reddit_client: praw.Reddit,
        config: Optional[RedditPostConfig] = None
    ):
        """Initialize the Reddit scraper.

        Args:
            reddit_client: Initialized PRAW Reddit client
            config: Configuration for post collection, uses defaults if None
        """
        self.reddit = reddit_client
        self.config = config or RedditPostConfig()

    def get_posts_since(
        self,
        subreddits: List[str],
        since: Optional[datetime] = None
    ) -> List[RedditPost]:
        """Get top posts from specified subreddits since given time.

        Args:
            subreddits: List of subreddit names to scrape
            since: Starting time for post collection, defaults to config.time_window hours ago

        Returns:
            List of RedditPost objects sorted by score
        """
        if since is None:
            since = datetime.now(pytz.utc) - \
                timedelta(hours=self.config.time_window)

        logger.info(
            "Fetching posts from %d subreddits since %s",
            len(subreddits),
            since.strftime('%Y-%m-%d %H:%M:%S %Z')
        )

        all_posts = []
        for subreddit_name in tqdm(subreddits, desc="Pulling Reddit Posts"):
            try:
                posts = self._get_subreddit_posts(subreddit_name, since)
                all_posts.extend(posts)
            except Exception as e:
                logger.error(
                    "Failed to fetch posts from subreddit %s: %s",
                    subreddit_name,
                    str(e)
                )

        return sorted(
            all_posts,
            key=lambda x: x.post.score,
            reverse=True
        )

    def _get_subreddit_posts(
        self,
        subreddit_name: str,
        since: datetime
    ) -> List[RedditPost]:
        """Get top posts from a single subreddit.

        Args:
            subreddit_name: Name of the subreddit to scrape
            since: Starting time for post collection

        Returns:
            List of RedditPost objects for the subreddit
        """
        logger.debug("Processing subreddit: %s", subreddit_name)

        subreddit = self.reddit.subreddit(subreddit_name)
        posts = []

        try:
            for post in tqdm(
                    subreddit.hot(limit=self.config.hot_posts_limit), desc=subreddit_name):
                created_time = datetime.fromtimestamp(
                    post.created_utc, pytz.utc)

                if created_time >= since:
                    posts.append(RedditPost(post))

            # Sort by score and take top N posts
            posts.sort(key=lambda x: x.post.score, reverse=True)
            return posts[:self.config.posts_per_subreddit]

        except Exception as e:
            logger.error(
                "Error processing subreddit %s: %s",
                subreddit_name,
                str(e)
            )
            raise

    @classmethod
    def from_credentials(
        cls,
        client_id: str,
        client_secret: str,
        user_agent: str,
        config: Optional[RedditPostConfig] = None
    ) -> 'RedditScraper':
        """Create RedditScraper instance from credentials.

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: Reddit API user agent
            config: Optional configuration override

        Returns:
            Configured RedditScraper instance
        """
        reddit_client = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        return cls(reddit_client, config)


scraper_singleton = RedditScraper.from_credentials(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_SECRET,
    user_agent=REDDIT_APP_NAME
)
