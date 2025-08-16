import os

class Config:
    """应用配置"""

    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # 文件上传配置
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/tmp/uploads'
    OUTPUT_FOLDER = os.environ.get('OUTPUT_FOLDER') or '/tmp/outputs'

    # 模型配置
    MODEL_PATH = os.environ.get('MODEL_PATH') or 'model/'

    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
