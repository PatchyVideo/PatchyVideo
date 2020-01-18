
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

"""
Tags
"""
class TagsConfig:
    MAX_LANGUAGE_LENGTH = 6
    MAX_TAG_LENGTH = 48
    MAX_CATEGORY_LENGTH = 16

"""
Videos
"""
class VideoConfig:
    MAX_TAGS_PER_VIDEO = 200
    MAX_URL_LENGTH = 1000
    MAX_BATCH_POST_COUNT = 1000
    MAX_COPIES = 20
    MAX_TITLE_LENGTH = 100
    MAX_DESC_LENGTH = 5000

"""
Querys
"""
class QueryConfig:
    MAX_QUERY_LENGTH = 1000

"""
User
"""
class UserConfig:
    MAX_USERNAME_LENGTH = 32
    MIN_USERNAME_LENGTH = 3
    MAX_PASSWORD_LENGTH = 64
    MIN_PASSWORD_LENGTH = 6
    MAX_DESC_LENGTH = 10000
    MAX_EMAIL_LENGTH = 150
    SESSION_EXPIRE_TIME = 30 * 60
    LOGIN_EXPIRE_TIME = 24 * 60 * 60

"""
Display
"""
class DisplayConfig:
    MAX_ITEM_PER_PAGE = 500

"""
Upload
"""
class UploadConfig:
    MAX_UPLOAD_SIZE = 1024 * 1024 * 10 # 10MB
