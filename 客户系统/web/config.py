import os


class Config:
    BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASEDIR, "instance", "system.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get(
        'UPLOAD_FOLDER',
        os.path.abspath(os.path.join(BASEDIR, '上传的文件'))
    )
    SECRET_KEY = '123456'
    STANDARD_FILES_FOLDER = os.path.join(UPLOAD_FOLDER, 'standard_files')
    VERSION = 'V5.0.1'