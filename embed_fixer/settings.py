from __future__ import annotations

from enum import StrEnum


class Setting(StrEnum):
    LANG = "lang"
    DISABLE_FIXES = "disable_fixes"
    EXTRACT_MEDIA_CHANNELS = "extract_media_channels"
    DISABLE_FIX_CHANNELS = "disable_fix_channels"
    ENABLE_FIX_CHANNELS = "enable_fix_channels"
    TOGGLE_WEBHOOK_REPLY = "toggle_webhook_reply"
    DISABLE_IMAGE_SPOILERS = "disable_image_spoilers"
    TOGGLE_DELETE_REACTION = "toggle_delete_reaction"
    SHOW_POST_CONTENT_CHANNELS = "show_post_content_channels"
    DELETE_MSG_EMOJI = "delete_msg_emoji"
    CHOOSE_FIX_SERVICE = "choose_fix_service"
    BOT_VISIBILITY = "bot_visibility"
