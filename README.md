# DrillBot - The Telegram Menu Bot

## Table of contents

- [Introduction](#introduction)
- [Installing](#installing)
- [Usage](#usage)
- [License](#license)

## Introduction

DrillBot (short for menu **drill**down **bot**) is a library to help create remote-control-like Telegram apps.

Here's a sample of the kind of bot you can create:

![Demo: UniversalRemoteBot.py](https://github.com/davidtorosyan/telegram-drillbot/raw/master/examples/images/universalremotebot-lights.gif)

## Installing

Add the repo into your project as a git submodule.

```sh
$ mkdir mybot
$ cd mybot
$ git init
$ git submodule add https://github.com/davidtorosyan/telegram-drillbot telegram_drillbot
```

## Usage

To create your bot, import `DrillBot` and create a subclass.

```py
from telegram_drillbot.drillbot.drillbot import DrillBot
from telegram_drillbot.drillbot.transition import MenuTransition

# <define 'home_state' and 'transitions'>

class MyBot(DrillBot):
    def __init__(self, token):
        super().__init__(token, home_state, transitions)

# <define 'token'>

MyBot(token).start_bot()
```

To see a full example, see [here](examples/).


## License
[MIT](https://choosealicense.com/licenses/mit/)
