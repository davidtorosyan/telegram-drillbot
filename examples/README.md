# DrillBot Examples

## Table of contents

- [Introduction](#introduction)
- [Examples](#examples)
  - [UniversalRemoteBot](#universalremotebot)

## Introduction

Below you can find some basic examples of what DrillBot can do.

You should be able to run the examples with something like:
```sh
$ python examples/universalremotebot.py <token>
```

You'll have to create a bot and get the token on your own. See here: [Telegram Bots FAQ - How do I create a bot?](https://core.telegram.org/bots/faq#how-do-i-create-a-bot)

Note that the `telegram_drillbot` folder here is to simulate a submodule, and leads to a symlink of the drillbot code.

## Examples

### [UniversalRemoteBot](universalremotebot.py)

Simulates a universal remote that can control music and lights. Demonstrates navigational menus and user input.

Here's what it looks like in action:

![Demo: greet](https://github.com/davidtorosyan/telegram-drillbot/raw/master/examples/images/universalremotebot-greet.gif)

And here's a snippet showcasing its nested menu system:

![Demo: lights](https://github.com/davidtorosyan/telegram-drillbot/raw/master/examples/images/universalremotebot-lights.gif)