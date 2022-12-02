from web3 import Web3
import yaml 
import requests
from setup import app

with open('config.yaml') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

print("test if it is added")



@app.route("/ethereum/")
def ether():
    return "Welcome to the API of connect-fast"