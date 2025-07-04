![Embed Fixer](https://i.imgur.com/919Gum1.png)

![GitHub issues](https://img.shields.io/github/issues/seriaati/embed-fixer)
![GitHub pull requests](https://img.shields.io/github/issues-pr/seriaati/embed-fixer)
![GitHub Repo stars](https://img.shields.io/github/stars/seriaati/embed-fixer)
![GitHub forks](https://img.shields.io/github/forks/seriaati/embed-fixer)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/seriaati/embed-fixer)
![Lines of code](https://tokei.rs/b1/github/seriaati/embed-fixer?style=flat&category=code&type=Python)
![GitHub](https://img.shields.io/github/license/seriaati/embed-fixer)
![Discord](https://img.shields.io/discord/1000727526194298910?label=Support%20Server&color=5865F2)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# Embed Fixer

## Add Bot

[**Bot invitation link**](https://discord.com/oauth2/authorize?client_id=770144963735453696)

Available as both a user and server app.  
When installed as a user app, you can right click a message to fix its embed or extract its media.

## Support

- [Request new fix](https://github.com/seriaati/embed-fixer/issues/new?template=new-embed-fix-request.md)
- [Report a bug](https://github.com/seriaati/embed-fixer/issues/new?template=bug_report.md)
- [Request a new feature](https://github.com/seriaati/embed-fixer/issues/new?template=feature_request.md)
- [Contribute to translations](https://app.transifex.com/seria/embed-fixer/)
- [Contact me on Discord](https://discord.com/invite/b22kMKuwbS) (my username is @seria_ati)

## Motive

As we know, social media embeds on Discord are bad:

- Pixiv embeds don't show the full artwork
- X/Twitter sometimes doesn't embed
- Instagram doesn't show the image/video
- Reddit doesn't show the images
- Tiktok doesn't show the video
- Twitch clip doesn't play the clips
- And so on...
  
Worry no more, this Discord bot fixes all of those issues.

# Features

## Embed Fixing

Fixings are currently available for:

- **Twitter/X**: [FxEmbed](https://github.com/FxEmbed/FxEmbed)/[BetterTwitFix](https://github.com/dylanpdx/BetterTwitFix)
- **Pixiv**: [Phixiv](https://github.com/thelaao/phixiv)
- **TikTok**: [fxTikTok](https://github.com/okdargy/fxTikTok)/[vxtiktok](https://github.com/dylanpdx/vxtiktok)
- **Reddit**: [FixReddit](https://github.com/MinnDevelopment/fxreddit)/[vxReddit](https://github.com/dylanpdx/vxReddit)
- **Instagram**: [InstaFix](https://github.com/Wikidepia/InstaFix)/[EmbedEZ](https://github.com/seriaati/embedez)/KKInstagram
- **FurAffinity**: [xfuraffinity](https://github.com/FirraWoof/xfuraffinity)
- **Twitch Clips**: [fxtwitch](https://github.com/seriaati/fxtwitch)
- **Iwara**: [fxiwara](https://github.com/seriaati/fxiwara)
- **Bluesky**: [VixBluesky](https://github.com/Lexedia/VixBluesky)/[FxEmbed](https://github.com/FxEmbed/FxEmbed)
- **Kemono**: Media extraction only, no embed fixing
- **Facebook**: [EmbedEZ](https://github.com/seriaati/embedez)/[fxfacebook](https://github.com/seriaati/fxfacebook)
- **Bilibili**: [fxbilibili](https://github.com/seriaati/fxbilibili)/[EmbedEZ](https://github.com/seriaati/embedez)/[BiliFix](https://vxbilibili.com)
- **Tumblr**: [fxtumblr](https://github.com/knuxify/fxtumblr)
- **Threads**: [FixThreads](https://github.com/milanmdev/fixthreads)/[vxThreads](https://github.com/everettsouthwick/vxThreads)

If your message contains link(s) that are of any of the social medias above, it gets deleted and resent using a webhook with your name and avatar containing the fix. There is also a ❌ reaction made to the message, so that the author of the message can click on and delete the message. The emoji used can be changed with the `/settings` command.

![image](https://github.com/user-attachments/assets/e7c4469b-c5dd-44e8-b923-c8137397a64b)

> [!TIP]
> You can disable embed fixing for a specific link by adding `$` at the beginning of the link. For example, `$https://twitter.com/...` will not be fixed.

### About Pixiv Embed Fixing

If the link is sent in a non-NSFW channel AND is from Pixiv AND the artwork contains the "#R-18" tag, the Embed Fixer will **NOT** fix the embed as this will show the NSFW image.

## Webhook Replying

When you reply to a webhook, it replies to the webhook, not the original author. The bot fixes this by tagging the original author with the same name of the webhook.

![image](https://iili.io/2RPjJ0Q.png)

## Media Extracting

The following platforms are supported:

- Twitter/X
- Pixiv
- Iwara
- Kemono
- Bluesky

When you send a link that is from one of the platforms above in channel(s) with this feature on, the bot resends all of the images/videos in the link in a nice gallery-like layout.  

![image](https://iili.io/2RPwDMb.png)  

If the link is sent in a NSFW channel, then the extracted media will be spoilered automatically (changeable).

Also, if you wrap the URL with spoiler tags, like ||<https://x.com/...>||, the extracted image(s) will be spoilered automatically.

## Very Customizable

*All settings are unique to each server*  

Below are settings you can change with the `/settings` command:

- **Language**: Change the language of the bot
- **Disable Embed Fixes for Websites**: Disable embed fixes for specific websites
- **Media Extraction Channels**: Images/Videos from Twitter/X/Pixiv links sent in these channels will be extracted
- **Embed Fix Channel Blacklist**: Channels here will not receive embed fixes, whitelist has priority over blacklist
- **Embed Fix Channel Whitelist**: Only channels set here will receive embed fixes, whitelist has priority over blacklist
- **Toggle Webhook Reply**: Toggle the ping to the original author when replying to a webhook
- **Disable Automatic Spoilering in NSFW Channels**: For the media extraction feature, NSFW channels selected here will not have medias automatically spoilered
- **Toggle Delete Reaction**: Add a emoji reaction to messages to delete them
- **Show Post Content Channels**: If media extraction is enabled, channels selected here will show the content of the post
- **Emoji used for deleting messages**: delete_msg_emoji_desc
- **Choose embed fix service**: Choose the embed fix service to use for different websites
- **Bot Visibility**: If enabled, Embed Fixer will fix embeds sent by other bots. If disabled, it will only fix embeds sent by users.
- **Funnel to Target Channel**: If set, all fixed embeds and extract medias will be sent to the target channel instead of the original channel.
- **Whitelist Roles**: If set, only users that have one of these roles will have their embeds fixed. Leave empty to disable.

# Self Hosting

1. Create a [Discord application](https://discord.com/developers/applications)
1. On the **Bot** page, generate a token and save it for later
1. Enable **Message Content Intent**
1. Run the application with your bot token as the `DISCORD_TOKEN` environment variable
1. Invite your bot with the invite link in the logs

## Syncing Commands

The command prefix is the bot's mention by default. For example, if your bot's name is `Embed Fixer`, the prefix would be `@Embed Fixer`.  
Run `@Embed Fixer sync` to sync the commands, you need to restart your client to see the changes.

## Database Migrations

Changes to the database schema can be found in `/migrations/embed_fixer`.  
To apply the changes, run `aerich upgrade` (only supports PostgreSQL; for other databases like SQLite, you need to migrate manually).

## Docker

```sh
docker run -v /my/mnt/logs:/app/logs -v /my/mnt/data:/data -e DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN ghcr.io/seriaati/embed-fixer:latest
```

### Volumes

- `/app/logs`: the logfiles produced by the program
- `/data`: the default location for the `embed_fixer.db` SQLite database file

### Environment Variables

- `DISCORD_TOKEN`: your Discord bot token
- `DB_URI`: defaults to `sqlite:///data/embed_fixer.db`, available to customize the database location
- `ENV`: defaults to `prod`, can be set to `dev` for development mode
- `REDIS_URL`: if set, uses Redis for caching instead of SQLite

## Local

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
1. Clone the repository
1. Create a `.env` file:

```env
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
ENV=prod
```

1. `uv run run.py`
