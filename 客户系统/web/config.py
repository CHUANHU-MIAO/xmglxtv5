import os


class Config:
    BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    UPLOAD_FOLDER = os.environ.get(
        'UPLOAD_FOLDER',
        os.path.abspath(os.path.join(BASEDIR, '上传的文件'))
    )
    STANDARD_FILES_FOLDER = os.path.join(UPLOAD_FOLDER, 'standard_files')

    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASEDIR, "instance", "system.db")}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = '123456'
    VERSION = 'V5.0.1'