# config.py

# import os

# class Config:
#     # Thư mục lưu trữ tệp tải lên
#     UPLOAD_FOLDER = 'uploads'
    
#     # Đường dẫn tới mô hình Whisper
#     MODEL_DIR = os.getenv('MODEL_DIR', 'models\whisper-model\whisper-tiny')
    
#     # Các loại tệp được phép tải lên
#     ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a'}
    
#     # Giới hạn kích thước tệp tải lên (ví dụ: 100MB)
#     MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    
#     # Cấu hình logging
#     LOG_FILE = f'logs/app.log'
#     API_KEY = os.getenv('API_KEY', 'your-default-api-key')
#     SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///api_keys.db')
#     SQLALCHEMY_TRACK_MODIFICATIONS = False
#     # Cấu hình JWT
#     JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key')  # Thay 'your-jwt-secret-key' bằng một chuỗi bí mật an toàn
#     JWT_ACCESS_TOKEN_EXPIRES = 3600  # Token hết hạn sau 1 giờ
# config.py

import os

class Config:
    # Thư mục lưu trữ tệp tải lên
    UPLOAD_FOLDER = 'uploads'
    
    # Đường dẫn tới mô hình Whisper
    MODEL_DIR = os.getenv('MODEL_DIR', 'models\whisper-model\whisper-tiny')
    
    # Các loại tệp được phép tải lên
    ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a'}
    
    # Giới hạn kích thước tệp tải lên (ví dụ: 100MB)
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    
    # Cấu hình logging
    LOG_FILE = 'logs/app.log'
    
    # Cấu hình cơ sở dữ liệu
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///api_keys.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Cấu hình JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key')  # Thay 'your-jwt-secret-key' bằng khóa bí mật thực tế
    #JWT_ACCESS_TOKEN_EXPIRES = 3600  # Token hết hạn sau 1 giờ
