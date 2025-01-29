"""Tests for Reddit scraping functionality."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import pytz
import praw

from backend.api.reddit import RedditScraper, RedditPost, RedditPostConfig, scraper_singleton


class MockRedditSubmission:
    """Mock Reddit submission for testing."""
    
    def __init__(
        self,
        post_id: str,
        title: str,
        selftext: str,
        subreddit_name: str,
        author_name: str,
        score: int = 100,
        num_comments: int = 10,
        created_utc: float = None,
        url: str = None
    ):
        """Initialize mock submission.
        
        Args:
            post_id: Unique post identifier
            title: Post title
            selftext: Post content
            subreddit_name: Name of subreddit
            author_name: Username of post author
            score: Post score/upvotes
            num_comments: Number of comments
            created_utc: Post creation timestamp (UTC)
            url: Post URL
        """
        self.id = post_id
        self.title = title
        self.selftext = selftext
        self.score = score
        self.num_comments = num_comments
        self.created_utc = created_utc or datetime.now(pytz.utc).timestamp()
        self.url = url or f"https://reddit.com/r/{subreddit_name}/{post_id}"
        
        # Create mock subreddit
        self.subreddit = MagicMock()
        self.subreddit.display_name = subreddit_name
        
        # Create mock author
        self.author = MagicMock()
        self.author.__str__.return_value = author_name

        # Create mock comments with PRAW-like structure
        self.comments = MagicMock()
        comments_list = []
        for i in range(3):  # Add 3 mock comments
            comment = MagicMock()
            comment.body = f"Test comment {i+1}"
            comments_list.append(comment)
        self.comments.__iter__.return_value = iter(comments_list)
        self.comments.__getitem__.side_effect = lambda i: comments_list[i]
        self.comments.replace_more = MagicMock()  # Mock the replace_more method
    
    def __str__(self) -> str:
        """String representation of mock submission."""
        return f"{self.title} - {self.subreddit.display_name}"


class MockReddit:
    """Mock Reddit client for testing."""

    def __init__(self):
        """Initialize mock Reddit client with test data."""
        self.posts = {}  # Dict to store mock posts by subreddit
        self._setup_test_data()
    
    def _setup_test_data(self):
        """Create test posts for different subreddits."""
        # Create timestamps for old and new posts
        now = datetime.now(pytz.utc)
        old_timestamp = (now - timedelta(days=3)).timestamp()
        recent_timestamp = (now - timedelta(hours=6)).timestamp()
        
        # Create posts for 'python' subreddit
        python_posts = [
            MockRedditSubmission(
                "py1", "Learning Python", "Getting started with Python",
                "python", "user1", score=150, num_comments=15,
                created_utc=old_timestamp
            ),
            MockRedditSubmission(
                "py2", "Advanced Python Tips", "Here are some advanced tips",
                "python", "user2", score=200, num_comments=25,
                created_utc=recent_timestamp
            ),
        ]
        
        # Create posts for 'programming' subreddit
        programming_posts = [
            MockRedditSubmission(
                "prog1", "Clean Code", "Principles of clean coding",
                "programming", "user3", score=300, num_comments=30,
                created_utc=old_timestamp
            ),
            MockRedditSubmission(
                "prog2", "Software Design", "Design patterns discussion",
                "programming", "user4", score=250, num_comments=20,
                created_utc=recent_timestamp
            ),
        ]
        
        self.posts = {
            "python": python_posts,
            "programming": programming_posts
        }
    
    def subreddit(self, name: str) -> MagicMock:
        """Get mock subreddit instance.
        
        Args:
            name: Subreddit name
            
        Returns:
            Mock subreddit with hot posts method
        """
        mock_subreddit = MagicMock()
        
        def mock_hot(limit=None):
            """Mock implementation of hot posts."""
            posts = self.posts.get(name, [])
            return posts[:limit] if limit else posts
            
        mock_subreddit.hot = mock_hot
        return mock_subreddit


@pytest.fixture
def mock_reddit():
    """Fixture providing mock Reddit instance."""
    return MockReddit()


@pytest.fixture
def reddit_scraper(mock_reddit):
    """Fixture providing RedditScraper with mock Reddit client."""
    config = RedditPostConfig(
        hot_posts_limit=10,
        top_comments_limit=5,
        posts_per_subreddit=5,
        time_window=24
    )
    return RedditScraper(mock_reddit, config)


class TestRedditPost:
    """Test suite for RedditPost class."""

    def test_initialization(self):
        """Test RedditPost initialization and basic properties."""
        mock_submission = MockRedditSubmission(
            "test1", "Test Title", "Test Content",
            "testsubreddit", "testuser"
        )
        post = RedditPost(mock_submission)
        
        assert post.post.id == "test1"
        assert post.post.title == "Test Title"
        assert post.post.selftext == "Test Content"
        assert post.post.subreddit.display_name == "testsubreddit"
        assert str(post.post.author) == "testuser"
    
    def test_to_dict(self):
        """Test RedditPost to_dict method."""
        created_time = datetime.now(pytz.utc)
        mock_submission = MockRedditSubmission(
            "test1", "Test Title", "Test Content",
            "testsubreddit", "testuser",
            created_utc=created_time.timestamp()
        )
        post = RedditPost(mock_submission)
        post_dict = post.to_dict()
        
        assert post_dict["post_id"] == "test1"
        assert post_dict["title"] == "Test Title"
        assert post_dict["text"] == "Test Content"
        assert post_dict["subreddit"] == "testsubreddit"
        assert post_dict["author"] == "testuser"
        assert "created_utc" in post_dict
        assert "pretty_text" in post_dict
    
    def test_pretty_text_formatting(self):
        """Test pretty text formatting with comments."""
        mock_submission = MockRedditSubmission(
            "test1", "Test Title", "Test Content",
            "testsubreddit", "testuser"
        )
        post = RedditPost(mock_submission)
        pretty_text = post._get_readable_format()
        
        assert "Title: Test Title" in pretty_text
        assert "Content:\nTest Content" in pretty_text
        assert "Comment 1: Test comment 1" in pretty_text
        assert "Comment 2: Test comment 2" in pretty_text
    
    def test_pretty_text_formatting_with_error(self):
        """Test pretty text formatting error handling."""
        # Create submission with comments that will raise an error
        mock_submission = MockRedditSubmission(
            "test1", "Error Test", "Test Content",
            "testsubreddit", "testuser"
        )
        mock_submission.comments.replace_more.side_effect = Exception("Comment error")
        
        post = RedditPost(mock_submission)
        pretty_text = post._get_readable_format()
        
        # Should fall back to basic format without comments
        assert "Title: Error Test" in pretty_text
        assert "Content:\nTest Content" in pretty_text
        assert "Comment" not in pretty_text  # No comments due to error
    
    def test_link_replacement(self):
        """Test URL replacement in text content."""
        text = "Check this link https://example.com and this https://test.com"
        mock_submission = MockRedditSubmission(
            "test1", "Test Title", text,
            "testsubreddit", "testuser"
        )
        post = RedditPost(mock_submission)
        replaced_text = post._replace_links(text)
        
        assert "https://example.com" not in replaced_text
        assert "https://test.com" not in replaced_text
        assert "<outgoing_link>" in replaced_text


class TestRedditScraper:
    """Test suite for RedditScraper class."""

    def test_get_posts_since(self, reddit_scraper):
        """Test fetching posts since specific time."""
        since_time = datetime.now(pytz.utc) - timedelta(hours=12)
        posts = reddit_scraper.get_posts_since(["python", "programming"], since_time)
        
        assert len(posts) > 0
        # Posts should be sorted by score
        scores = [post.post.score for post in posts]
        assert scores == sorted(scores, reverse=True)
    
    def test_get_subreddit_posts(self, reddit_scraper):
        """Test fetching posts from single subreddit."""
        since_time = datetime.now(pytz.utc) - timedelta(hours=12)
        posts = reddit_scraper._get_subreddit_posts("python", since_time)
        
        assert len(posts) > 0
        assert all(isinstance(post, RedditPost) for post in posts)
        assert all(post.post.subreddit.display_name == "python" for post in posts)
    
    def test_post_filtering_by_time(self, reddit_scraper):
        """Test filtering posts by creation time."""
        # Check posts from 2 days ago (should include all posts)
        old_time = datetime.now(pytz.utc) - timedelta(days=4)
        old_posts = reddit_scraper.get_posts_since(["python"], old_time)
        assert len(old_posts) == 2  # Should get both old and recent posts
        
        # Check posts from 12 hours ago (should only include recent posts)
        recent_time = datetime.now(pytz.utc) - timedelta(hours=12)
        recent_posts = reddit_scraper.get_posts_since(["python"], recent_time)
        assert len(recent_posts) == 1  # Should only get the recent post
        
        # Check posts from 1 hour ago (should get no posts)
        very_recent_time = datetime.now(pytz.utc) - timedelta(hours=1)
        very_recent_posts = reddit_scraper.get_posts_since(["python"], very_recent_time)
        assert len(very_recent_posts) == 0  # Should get no posts
    
    def test_nonexistent_subreddit(self, reddit_scraper):
        """Test handling of nonexistent subreddit."""
        since_time = datetime.now(pytz.utc) - timedelta(hours=12)
        posts = reddit_scraper.get_posts_since(["nonexistent"], since_time)
        assert len(posts) == 0
    
    def test_subreddit_processing_error(self, reddit_scraper):
        """Test error handling in subreddit processing."""
        since_time = datetime.now(pytz.utc) - timedelta(hours=12)
        
        # Create a mock subreddit that raises an exception
        error_subreddit = MagicMock()
        error_subreddit.hot.side_effect = Exception("API Error")
        
        # Patch the subreddit method to return our error-raising mock
        with patch.object(reddit_scraper.reddit, 'subreddit', return_value=error_subreddit):
            
            # Error should be logged and re-raised
            with pytest.raises(Exception) as exc_info:
                reddit_scraper._get_subreddit_posts("python", since_time)
            
            assert str(exc_info.value) == "API Error"
    
    def test_from_credentials_factory(self):
        """Test RedditScraper.from_credentials factory method."""
        with patch('praw.Reddit') as mock_praw:
            mock_praw.return_value = MockReddit()
            scraper = RedditScraper.from_credentials(
                "test_client_id",
                "test_secret",
                "test_agent"
            )
            assert isinstance(scraper, RedditScraper)
            mock_praw.assert_called_once_with(
                client_id="test_client_id",
                client_secret="test_secret",
                user_agent="test_agent"
            )


def test_scraper_singleton():
    """Test scraper singleton instance."""
    assert isinstance(scraper_singleton, RedditScraper)
    
    # Create new instance and verify it's different
    new_scraper = RedditScraper(MockReddit())
    assert scraper_singleton is not new_scraper