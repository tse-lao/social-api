import base64
import hashlib
import json
import os
import random
import re

import numpy
#compare images. 
import openai
import requests
#installing stuff for analyzing the tweets, 
import snscrape.modules.twitter as twitterScrape
import tweepy
import tweets
import yaml
from flask import Flask, redirect, render_template, request, session, url_for
from flask_cors import CORS
from requests.auth import AuthBase, HTTPBasicAuth
from requests_oauthlib import OAuth2Session, TokenUpdated
from scipy.special import softmax
from transformers import AutoModelForSequenceClassification, AutoTokenizer

app = Flask(__name__)
CORS(app)

with open('config.yaml') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)


client = tweepy.Client(config["twitter"]["bearer_token"])
hed = {'Authorization': 'Bearer ' + config["twitter"]["bearer_token"]}
baseurl = "https://api.twitter.com/"


query = "python"
limit = 100

tweetje = "@legender, lets get bullish on matic @ home https://testingisd.com"



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

    return float(highscore), float(scores[0]), float(scores[1]), float(scores[2])

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
    followers = []
    for user in data["data"]:
        followers.append(user['username'])

    return followers

@app.route('/tweets/<string:search>/')
def twittertweets(search):
    tweets = []
    positiveCount = 0
    negativeCount = 0
    for tweet in twitterScrape.TwitterSearchScraper(search).get_items():
        if len(tweets) == limit:
            print("negative count: ", negativeCount)
            print("postive count: ", positiveCount)
            print("total count:", len(tweets))
            return {"tweets": tweets, "positive": int(positiveCount), "negative": int(negativeCount), "total": int(len(tweets))}
        else:
            #here we want to anakyze the twee context
            newString = tweetConversion(tweet.content)
            result = sentimentAnalyses(newString)
            if result[0] == 0:
                negativeCount += 1
            elif result[0] == 2:
                positiveCount += 1
            
            tweets.append([tweet.date, tweet.user.username, newString, result])
    print("negative count: ", negativeCount)
    print("postive count: ", positiveCount)
    print("total count:", len(tweets))
    return {"tweets": tweets, "positive": int(positiveCount), "negative": int(negativeCount), "total": int(len(tweets))}

@app.route('/analyze/tweet')
def tweetAnalyze():
    newString = tweetConversion(tweetje)
    result = sentimentAnalyses(newString)
    
    print(result)
    return newString


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



#lets try here the authenticated parts. 
client_id = config["twitter"]["client_id"]
client_secret = config["twitter"]["client_secret"]
auth_url = "https://twitter.com/i/oauth2/authorize"
token_url = "https://api.twitter.com/2/oauth2/token"
redirect_uri = config["twitter"]["redirect_uri"]
scopes = ["tweet.read", "users.read", "tweet.write", "offline.access"]
code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8")
code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)
code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
code_challenge = code_challenge.replace("=", "")

def make_token():
    return OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)

@app.route('/twitter/authorize/')
def login():
    global twitter
    twitter = make_token()
    authorization_url, state = twitter.authorization_url(
        auth_url, code_challenge=code_challenge, code_challenge_method="S256"
    )
    session["oauth_state"] = state
    return redirect(authorization_url)


@app.route("/oauth/callback", methods=["GET"])
def callback():
    code = request.args.get("code")
    token = twitter.fetch_token(
        token_url=token_url,
        client_secret=client_secret,
        code_verifier=code_verifier,
        code=code,
    )

    #get all the users their tweet and print them out in the comment line. 

    doggie_fact = "BOT2: Trying something new here, we need to tweet this from connect-fast.com"

    payload = {"text": "{}".format(doggie_fact)}
    response = tweets.post_tweet(payload, token).json()
    return response



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

    #now we want to loop through all the chains with the 
    userDetails = user._get_entity()
    url = userDetails.profileImageUrl.replace("_normal", "_400x400")
    
    print(userDetails.profileImageUrl)
    return url

@app.route("/ai/<string:text>/")
def createImage(text):
    openai.api_key = config['openai']['token']
    print(text)
    response = openai.Image.create(
    prompt=text,
    n=1,
    size="1024x1024"
    )
    image_url = response['data'][0]['url']
    print(image_url)
    return image_url


@app.route("/nft/<string:address>/")
def nfts(address): 
    print("Lets get all these users address")
    print(address)
    nft = []
    api = config["web3"]['alchemy']
    polapi = config["web3"]["polygon"]
    url = "https://eth-mainnet.g.alchemy.com/nft/v2/" + api + "/getNFTs/?owner=" + address
    poly = "https://polygon-mainnet.g.alchemy.com/v2/"+ polapi + "/getNFTs/?owner=" + address
    print(url)
    get = requests.get(url)
    polyNFT = requests.get(poly)
    print(get.json())
    print(polyNFT.json())
    nft.append(get.json())
    nft.append(polyNFT.json())
    return nft
