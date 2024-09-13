![Embed Fixer](https://i.imgur.com/919Gum1.png)  

![GitHub issues](https://img.shields.io/github/issues/seriaati/embed-fixer)
![GitHub pull requests](https://img.shields.io/github/issues-pr/seriaati/embed-fixer)
![GitHub Repo stars](https://img.shields.io/github/stars/seriaati/embed-fixer)
![GitHub forks](https://img.shields.io/github/forks/seriaati/embed-fixer)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/seriaati/embed-fixer)
![GitHub](https://img.shields.io/github/license/seriaati/embed-fixer)
![Discord](https://img.shields.io/discord/1000727526194298910?label=Support%20Server&color=5865F2)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# Embed Fixer

[**Bot invitation link**](https://discord.com/oauth2/authorize?client_id=770144963735453696)

As we know, social media embeds on Discord are bad:  

- Pixiv embeds don't show the full artwork
- X/Twitter sometimes doesn't even embed
- Instagram doesn't show the image/video
- Reddit doesn't show the full thread
- Tiktok doesn't show the video
- Twitch clip embeds don't play the clips
- And so on...
  
Worry no more, this Discord bot fixes all of those issues.

# Features

## Embed Fixing

Fixings are currently available for:  

- Pixiv with [phixiv](https://github.com/HazelTheWitch/phixiv)
- Twitter/X with [fxtwitter](https://github.com/FixTweet/FxTwitter)
- Instagram with [instafix](https://github.com/Wikidepia/InstaFix)
- Reddit with [fxreddit](https://github.com/MinnDevelopment/fxreddit)
- Tiktok wtih [vxtiktok](https://github.com/dylanpdx/vxtiktok)
- Furaffinity with [xfuraffinity](https://github.com/FirraWoof/xfuraffinity)
- Twitch clips with [fxtwitch](https://github.com/seriaati/fxtwitch)
- Iwara with [fxiwara](https://github.com/seriaati/fxiwara)

If your message contains link(s) that are of any of the social medias above, it gets deleted and resent using a webhook with your name and avatar containing the fix. There is also a "Delete" button that only you and/or users with "Manage Messages" permission can click on to delete the message.  

![image](https://github.com/seriaati/embed-fixer/assets/61446626/caf322dc-ffcf-4f9c-a041-75a0da55b957)  

> [!NOTE]
> If the link is sent in a non-NSFW channel AND is from Pixiv AND the artwork contains the "#R-18" tag, the Embed Fixer will **NOT** fix the embed as this will show the NSFW image.

## Webhook Replying

When you reply to a webhook, it replies to the webhook, not the original author. The bot fixes this by tagging the original author with the same name of the webhook.  
![image](https://github.com/seriaati/embed-fixer/assets/61446626/e7db4d9d-817d-4fba-95bb-a058c094a95d)

## Media Extracting

This feature currently only supports Twitter, X, and Pixiv. When you send a pixiv artwork link into channel(s) with this feature on, the bot resend all of the images/videos in the link in a nice gallery-like layout.  

![image](https://github.com/seriaati/embed-fixer/assets/61446626/443fce84-f51f-451f-99b0-63f0164d98a0)  

> [!NOTE]
> If the link is sent in a NSFW channel then the extracted media will be spoilered automatically.

## Very Customizable

*All settings are unique to the server*  
  
Below are settings you can change with the `/settings` command:  

- Disable embed fixes: Disable specific embed fixes
- Language: Change language of the bot
- Media extraction channels: Channels to enable the media extraction feature mentioned above
- Disable embed fix channels: Channels to disable embed fixing
- Toggle webhook reply: Toggle the webhook reply feature mentioned above  
  
![image](https://github.com/seriaati/embed-fixer/assets/61446626/b0bf6f0a-c3e6-42ca-b726-7fe989f29898)

# Questions, Issues, Feedback, Contributions

Whether you want a new fix to be added, to request a new feature, to report a bug, or to contribute to translations. You can do so by creating an issue or a pull request.  
If GitHub is not your type, you can find me on [Discord](https://discord.com/invite/b22kMKuwbS), my username is @seria_ati.
