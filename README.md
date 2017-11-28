# twitter-wordcloud-bot

[![Build Status](https://travis-ci.org/cygnan/twitter-wordcloud-bot.svg?branch=master)](https://travis-ci.org/cygnan/twitter-wordcloud-bot)
[![Maintainability](https://api.codeclimate.com/v1/badges/6302b1e5c142245d7d6a/maintainability)](https://codeclimate.com/github/cygnan/twitter-wordcloud-bot/maintainability)
[![Hound](https://camo.githubusercontent.com/23ee7a697b291798079e258bbc25434c4fac4f8b/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f50726f7465637465645f62792d486f756e642d6138373364312e737667)](https://houndci.com)

A Twitter bot with Python and Heroku to generate a wordcloud from the tweets that match a search query.

## Requirements

- A free Heroku account (No credit card required)
- Heroku CLI
- A Twitter account

## How to deploy to Heroku

1. Clone this repository

   ```bash
   git clone https://github.com/cygnan/twitter-wordcloud-bot
   cd twitter-wordcloud-bot
   ```

1. Create a Heroku app and add some configs

   ```bash
   heroku create {APP_NAME}
   heroku config:set LD_LIBRARY_PATH=/app/.linuxbrew/lib
   heroku config:set MECAB_PATH=/app/.linuxbrew/lib/libmecab.so
   heroku buildpacks:set https://github.com/heroku/heroku-buildpack-multi
   ```

   __Note:__ Choose an unique app name for `{APP_NAME}`.

1. Get your Twitter API keys and tokens and set them.

   ```bash
   heroku config:set CONSUMER_KEY={YOUR_CONSUMER_KEY}
   heroku config:set CONSUMER_SECRET={YOUR_CONSUMER_SECRET}
   heroku config:set ACCESS_TOKEN={YOUR_ACCESS_TOKEN}
   heroku config:set ACCESS_TOKEN_SECRET={YOUR_ACCESS_TOKEN_SECRET}
   ```

   You can get these keys and tokens from [https://apps.twitter.com/app/new](https://apps.twitter.com/app/new).

1. Deploy your app

   ```bash
   git push heroku master
   heroku ps:scale worker=1
   ```

## Usage

Tweet a search query to your Twitter bot. Then it will search tweets and reply with a wordcloud image.

## License

Copyright © 2017 Cygnan  
Licensed under the MIT License with the exception of a font, see [LICENSE.md](LICENSE.md).
