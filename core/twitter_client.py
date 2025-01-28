import tweepy

# Your API credentials
consumer_key = "YOUR_CONSUMER_KEY"
consumer_secret = "YOUR_CONSUMER_SECRET"
access_key = "YOUR_ACCESS_KEY"
access_secret = "YOUR_ACCESS_SECRET"

# Authenticate
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_key, access_secret)

# Create API object
api = tweepy.API(auth)

# Fetch tweets
def get_tweets(username, num_tweets=200):
    tweets = api.user_timeline(screen_name=username, count=num_tweets)
    return [tweet.text for tweet in tweets]

# Example usage
tweets = get_tweets("twitter-handle")
for tweet in tweets:
    print(tweet)
