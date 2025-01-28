CREATE TABLE IF NOT EXISTS reddit_posts (
    post_id VARCHAR(50) PRIMARY KEY,  -- Reddit's post ID
    subreddit VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    author VARCHAR(100),
    created_utc TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    llm_tags JSONB,  -- Store extracted tags as JSON
    discussion_summary TEXT,
    url TEXT,
    score INTEGER,
    num_comments INTEGER
);