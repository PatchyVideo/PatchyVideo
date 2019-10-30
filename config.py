
class BaseConfig:
    REDIS_URL = "redis://redis:6379/"

"""
Playlists
"""
class PlaylistConfig:
    MAX_TITLE_LENGTH = 128
    MAX_DESC_LENGTH = 2048
    MAX_COVER_URL_LENGTH = 512
    MAX_VIDEO_PER_PLAYLIST = 10000
    MAX_COMMON_TAGS = 150
