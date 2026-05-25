import os


class Config:
    BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    DESKTOP_MODE = os.environ.get('DESKTOP_MODE', 'false').lower() == 'true'

    UPLOAD_FOLDER = os.environ.get(
        'UPLOAD_FOLDER',
        os.path.abspath(os.path.join(BASEDIR, '上传的文件'))
    )
    STANDARD_FILES_FOLDER = os.path.join(UPLOAD_FOLDER, 'standard_files')

    if DESKTOP_MODE:
        DESKTOP_DATA_DIR = os.path.join(BASEDIR, 'desktop', 'desktop_data')
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(DESKTOP_DATA_DIR, "desktop_system.db")}'
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASEDIR, "instance", "system.db")}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = '123456'
    VERSION = 'V5.0.1'