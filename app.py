from flask import Flask
from flask_cors import CORS
import tweepy
import yaml 
import requests
import numpy


#installing stuff for analyzing the tweets, 
import snscrape.modules.twitter as twitter
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from scipy.special import softmax

app = Flask(__name__)
CORS(app)

with open('config.yaml') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)


client = tweepy.Client(config["twitter"]["bearer_token"])
hed = {'Authorization': 'Bearer ' + config["twitter"]["bearer_token"]}
baseurl = "https://api.twitter.com/"


query = "python"
limit = 1000

tweetje = "@legender, lets get bullish on matic @ home https://testingisd.com"
def tweetConversion(tweet):
    tweet_words = []
    for word in tweet.split(' '):
        if word.startswith('@') and len(word) > 1:
            word = '@user'
        elif word.startswith('http'):
            word = 'http'

        tweet_words.append(word)
    newTweet = " ".join(tweet_words)
    return newTweet


def getId(user):
    data = username(user)
    url = baseurl + "2/users/by/username/" + user
    response = requests.get(url=url, headers=hed);
    data = response.json()
    print(data['data']['id'])
    return data['data']['id']

#load model and tokenizer. 
roberta = "cardiffnlp/twitter-roberta-base-sentiment"
model = AutoModelForSequenceClassification.from_pretrained(roberta)

tokenizer = AutoTokenizer.from_pretrained(roberta)
labels = ['Negative', 'Neutral', 'Positive']

#sentimaent analyses
def sentimentAnalyses(tweet):
    encoded_tweet = tokenizer(tweet, return_tensors='pt')
    output = model(**encoded_tweet)
    scores = output[0][0].detach().numpy()
    highscore = numpy.argmax(scores)
    return highscore

@app.route("/")
def index():
    return "Welcome to the API of connect-fast"

@app.route('/username/<string:username>/')
def username(username):
    url = "https://api.twitter.com/2/users/by/username/" + username
    response = requests.get(url=url, headers=hed)
    data = response.json()
    return data

@app.route('/followers/<string:username>/')
def followers(username):
    id = getId(username)
    url= "https://api.twitter.com/2/users/" + id + "/followers"
    response = requests.get(url=url, headers=hed)
    data = response.json()
    return data

@app.route('/tweets/<string:username>/')
def twittertweets(username):
    tweets = []
    positiveCount = 0
    negativeCount = 0
    for tweet in twitter.TwitterSearchScraper(username).get_items():
        if len(tweets) == limit:
            print("negative count: ", negativeCount)
            print("postive count: ", positiveCount)
            return tweets
        else:
            #here we want to anakyze the twee context
            newString = tweetConversion(tweet.content)
            result = sentimentAnalyses(newString)
            if result == 0:
                negativeCount += 1
            elif result == 2:
                positiveCount += 1
            
            tweets.append([tweet.date, tweet.user.username, newString])



@app.route('/analyze/tweet')
def tweetAnalyze():
    newString = tweetConversion(tweetje)
    result = sentimentAnalyses(newString)
    
    print(result)
    return newString

@app.route("/likes/<string:username>/")
def likes(username): 
    id= getId(username)
    url = "https://api.twitter.com/2/users/"+id+"/liked_tweets/"
    response = requests.get(url=url, headers=hed)
    data = response.json()
    return data

@app.route("/analyze/profile/<string:username>/")
def analyzeProfile(username): 
    try:
        user = twitter.TwitterUserScraper(username)
    except ValueError:
        return "Sorry, {} is not a valid username, tru again".format(username)
    #we need a check if the username exists or not. 
    print(user)
    userDetails = user._get_entity()
    return userDetails.profileImageUrl


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=9000)