# **Privacy Policy**

**Effective Date:** 7th October 2026

## 1. **Introduction**

This Privacy Policy outlines how Embed Fixer collects, uses, stores, and protects data related to its operation as a Discord bot. By using Embed Fixer, you agree to the collection and use of information in accordance with this policy.

## 2. **Data Collection**

At the time of writing, Embed Fixer stores the following data in its database:

- **Guild Settings:** The guild ID and the settings configured with `/settings` and `/translang`, such as language, disabled websites, chosen fix services, fix mode, and the channel and role IDs used by channel blacklists/whitelists, media extraction, spoilers, post content, the funnel target channel, and the role whitelist.
- **User Settings:** The user ID and the settings configured with `/user-settings`: language, fix mode, and whether to receive a DM when someone reacts to your fixed message.
- **Opt-Out List:** The user IDs of users who opted out of embed fixing with `/ignore-me`.
- **Fixed Message Records:** For each message sent by the bot as a fix, the message ID, guild ID, channel ID, the original author's user ID, how the fix was sent (e.g. webhook or reply), and when it was sent. These are used to identify the original author of a fixed message, for features such as the delete reaction, the rotate fix reaction, webhook reply mentions, and reaction notifications.

Embed Fixer does not store the content of your messages in its database. Message content is read only to find supported links, rewrite them, and resend the message with the fixed links. However, message content may temporarily appear in the following places:

- **Log Files:** URLs found in messages may be written to the bot's log files for debugging.
- **Error Reports:** When an error occurs while processing a message, an error report is sent to [Sentry](https://sentry.io), which may include parts of the message being processed, such as its content or URLs.
- **Request Cache:** Responses from third-party services (see Section 5) for links found in messages are cached.

## 3. **Data Usage**

The data collected by Embed Fixer is used to provide and customize the bot's features based on the settings configured by guilds and users, and to debug and fix errors. It is not sold, used for advertising, or used to train machine learning or AI models.

## 4. **Data Storage**

- The collected data is stored in a PostgreSQL database hosted on a server maintained by the developer, powered by Hetzner. Log files and the request cache are stored on the same server.
- The data is securely stored with password protection. However, please note that the data itself is not encrypted.

## 5. **Data Sharing**

Embed Fixer does not sell or share the collected data with third parties, except in the following cases, which are necessary for the bot to work:

- **Embed Fix Services:** Links found in messages are rewritten to point to third-party embed fix services (e.g. FxEmbed, Phixiv), which Discord then contacts to generate the embed.
- **Post Information:** To extract media, show post content, and check whether a post is NSFW, the bot requests post information for the links from third-party services, such as the website's own API (e.g. Pixiv, Bluesky, Kemono) or an embed fix service's API (e.g. FxEmbed).
- **Error Reporting:** Error reports are sent to Sentry, as described in Section 2.

## 6. **Data Retention**

- **Guild Settings, User Settings, and the Opt-Out List** are retained indefinitely unless a guild owner, authorized representative, or user requests their deletion. You can remove yourself from the opt-out list by running `/ignore-me` again. Requests for data removal can be made by contacting the developer directly (see Section 9 for contact information).
- **Fixed Message Records** are deleted automatically after 90 days, or immediately when the fixed message is deleted.
- **Log Files** are deleted automatically after 2 weeks.
- **Request Cache** entries are deleted automatically after 10 minutes.
- **Error Reports** are retained according to Sentry's data retention policy.

## 7. **Security Measures**

- The server and database hosting the collected data are password protected to prevent unauthorized access.
- While measures are in place to protect the data, it is important to note that the data itself is not encrypted.

## 8. **User Rights**

Guild owners, their authorized representatives, and users can request access to, modification, or deletion of their data. To make such a request, please contact the developer using the contact information provided below.

Users can opt out of having their messages processed by Embed Fixer at any time with the `/ignore-me` command. A single link can also be skipped by adding `$` at the beginning of the link or wrapping it with `<>`.

## 9. **Contact Information**

If you have any questions, concerns, or requests regarding this Privacy Policy or the data collected by Embed Fixer, you can contact the developer:

- **Email:** <seria.ati@gmail.com>
- **Discord:** @seria_ati

Please note that while contact options are provided, there is no guarantee that every issue or request will be addressed.

## 10. **Changes to the Privacy Policy**

Changes to this Privacy Policy may be made at any time. However, users will not be notified of changes to the policy. It is recommended that users review the Privacy Policy periodically for any updates.
