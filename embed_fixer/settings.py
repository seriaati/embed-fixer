from __future__ import annotations

from enum import StrEnum


class Setting(StrEnum):
    DISABLE_FIXES = "disable_fixes"
    LANG = "lang"
    EXTRACT_MEDIA_CHANNELS = "extract_media_channels"
    DISABLE_FIX_CHANNELS = "disable_fix_channels"
    TOGGLE_WEBHOOK_REPLY = "toggle_webhook_reply"
    DISABLE_IMAGE_SPOILERS = "disable_image_spoilers"
    TOGGLE_DELETE_REACTION = "toggle_delete_reaction"
    SHOW_POST_CONTENT_CHANNELS = "show_post_content_channels"
    USE_VXREDDIT = "use_vxreddit"
    DELETE_MSG_EMOJI = "delete_msg_emoji"
