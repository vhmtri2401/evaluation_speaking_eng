# utils/helpers.py

import os
from flask import jsonify
from config import Config
from werkzeug.utils import secure_filename
import logging

def allowed_file(filename):
    """Kiểm tra định dạng tệp có được phép không."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# utils/helpers.py

import logging
import os

def setup_logging():
    log_directory = 'logs'
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    
    log_file = os.path.join(log_directory, 'app.log')
    
    # Tạo logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Đặt mức độ log tối thiểu
    
    # Xóa các handler cũ nếu có (để tránh trùng lặp log)
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Tạo formatter
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
    
    # Tạo FileHandler để ghi log vào tệp
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Đặt mức độ log cho FileHandler
    file_handler.setFormatter(formatter)
    
    # Tạo StreamHandler để hiển thị log trên console
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)  # Đặt mức độ log cho StreamHandler
    stream_handler.setFormatter(formatter)
    
    # Thêm các handler vào logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

