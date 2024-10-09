# app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from pronunciation_assessment import pronunciation_assessment_configured_with_whisper
from utils.helpers import allowed_file, setup_logging
from config import Config
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import logging
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from models.api_key import db, APIKey
from flasgger import Swagger, swag_from

# Thiết lập logging
setup_logging()
logger = logging.getLogger(__name__)  # Lấy logger với tên hiện tại

# Thêm dòng log thử nghiệm để xác nhận logging hoạt động
logger.info("Flask application đã khởi động và logging đã được thiết lập.")

# Khởi tạo Flask app
app = Flask(__name__)
CORS(app)

# Cấu hình ứng dụng
app.config.from_object(Config)

# Khởi tạo SQLAlchemy
db.init_app(app)

# Khởi tạo JWT Manager
jwt = JWTManager(app)

# Cấu hình Swagger với Security Definitions
swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "API Đánh Giá Phát Âm",
        "description": "API cho việc đánh giá phát âm sử dụng Whisper model.",
        "version": "1.0.0"
    },
    "securityDefinitions": {
        "apiKey": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Nhập API key của bạn mà không cần tiền tố. Ví dụ: \"12345\""
        }
    },
    "security": [
        {
            "apiKey": []
        }
    ]
}
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,  # Chỉ định các rule để bao gồm trong Swagger
            "model_filter": lambda tag: True,  # Chỉ định các model để bao gồm trong Swagger
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/"
}

swagger = Swagger(app, template=swagger_template, config=swagger_config)
@app.before_request
def add_bearer_to_auth_header():
    auth_header = request.headers.get("Authorization")
    if auth_header and not auth_header.startswith("Bearer "):
        request.headers.environ["HTTP_AUTHORIZATION"] = f"Bearer {auth_header}"

# Tạo thư mục uploads nếu chưa tồn tại
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Tải mô hình và processor khi khởi động Flask
logger.info("Loading Whisper model...")
try:
    processor = WhisperProcessor.from_pretrained(app.config['MODEL_DIR'])
    model = WhisperForConditionalGeneration.from_pretrained(app.config['MODEL_DIR'])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    logger.info("Whisper model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading Whisper model: {e}")
    raise e

# Tạo cơ sở dữ liệu nếu chưa tồn tại
with app.app_context():
    db.create_all()

# Decorator kiểm tra JWT và role
def jwt_required_with_roles(required_roles=None):
    """
    Decorator yêu cầu JWT và kiểm tra roles nếu được chỉ định.
    """
    def decorator(func):
        @wraps(func)
        @jwt_required()
        def wrapper(*args, **kwargs):
            if required_roles:
                claims = get_jwt()
                user_role = claims.get('role', None)
                if user_role not in required_roles:
                    logger.warning(f"Forbidden access attempt by role: {user_role}")
                    return jsonify({'error': 'Forbidden: Insufficient permissions.'}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Thêm handler cho lỗi 405 và 404
@app.errorhandler(405)
def method_not_allowed(e):
    logger.warning(f"Method Not Allowed: {request.method} on {request.path}")
    return jsonify({'error': 'Method Not Allowed. Please use POST method.'}), 405

@app.errorhandler(404)
def not_found(e):
    logger.warning(f"Not Found: {request.path}")
    return jsonify({'error': 'Not Found.'}), 404

# Endpoint để đăng nhập và nhận JWT
@app.route('/login', methods=['POST'])
@swag_from({
    'tags': ['Authentication'],
    'security': [],  # Không yêu cầu xác thực cho endpoint này
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'username': {
                        'type': 'string',
                        'example': 'admin'
                    },
                    'password': {
                        'type': 'string',
                        'example': 'password'
                    }
                },
                'required': ['username', 'password']
            },
            'description': 'Thông tin đăng nhập'
        }
    ],
    'responses': {
        200: {
            'description': 'Token truy cập thành công',
            'schema': {
                'type': 'object',
                'properties': {
                    'access_token': {
                        'type': 'string'
                    }
                }
            }
        },
        401: {
            'description': 'Sai tên đăng nhập hoặc mật khẩu'
        }
    }
})
def login():
    """
    Đăng nhập và nhận JWT token.
    ---
    """
    data = request.get_json()
    username = data.get('username', None)
    password = data.get('password', None)

    # Đơn giản hóa xác thực
    if username != 'admin' or password != 'password':
        return jsonify({'msg': 'Bad username or password'}), 401

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200

# Endpoint để tạo API Key mới (chỉ dành cho admin)
@app.route('/admin/create-api-key', methods=['POST'])
@jwt_required_with_roles(required_roles=["ROLE_DEV"])
@swag_from({
    'tags': ['Admin'],
    'security': [{'apiKey': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'owner': {
                        'type': 'string',
                        'example': 'Tên chủ sở hữu API Key'
                    }
                },
                'required': ['owner']
            },
            'description': 'Tên chủ sở hữu API Key'
        }
    ],
    'responses': {
        201: {
            'description': 'API Key mới được tạo',
            'schema': {
                'type': 'object',
                'properties': {
                    'api_key': {
                        'type': 'string'
                    }
                }
            }
        },
        400: {
            'description': 'Thiếu tên chủ sở hữu API Key'
        },
        403: {
            'description': 'Forbidden: Insufficient permissions.'
        }
    }
})
def create_api_key():
    """
    Endpoint để tạo API Key mới.
    ---
    """
    data = request.get_json()
    owner = data.get('owner', None)
    if not owner:
        logger.warning("Owner name not provided for API key creation.")
        return jsonify({'error': 'Owner name is required.'}), 400

    new_key = APIKey(owner=owner)
    db.session.add(new_key)
    db.session.commit()

    logger.info(f"API key created for owner: {owner}")
    return jsonify({'api_key': new_key.key}), 201

# Endpoint để xoá API Key (chỉ dành cho admin)
@app.route('/admin/delete-api-key', methods=['POST'])
@jwt_required_with_roles(required_roles=["ROLE_DEV"])
@swag_from({
    'tags': ['Admin'],
    'security': [{'apiKey': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'api_key': {
                        'type': 'string',
                        'example': 'API_KEY_CẦN_XÓA'
                    }
                },
                'required': ['api_key']
            },
            'description': 'API Key cần xoá hoặc vô hiệu hóa'
        }
    ],
    'responses': {
        200: {
            'description': 'API Key đã được vô hiệu hóa',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string'
                    }
                }
            }
        },
        400: {
            'description': 'Thiếu API Key'
        },
        404: {
            'description': 'API Key không tìm thấy hoặc đã bị vô hiệu hóa'
        },
        403: {
            'description': 'Forbidden: Insufficient permissions.'
        }
    }
})
def delete_api_key():
    """
    Endpoint để xoá hoặc vô hiệu hóa API Key.
    ---
    """
    data = request.get_json()
    api_key = data.get('api_key', None)
    if not api_key:
        logger.warning("API key not provided for deletion.")
        return jsonify({'error': 'API key is required.'}), 400

    key = APIKey.query.filter_by(key=api_key, active=True).first()
    if not key:
        logger.warning(f"API key not found or already inactive: {api_key}")
        return jsonify({'error': 'API key không tìm thấy hoặc đã bị vô hiệu hóa.'}), 404

    key.active = False
    db.session.commit()

    logger.info(f"API key deactivated: {api_key}")
    return jsonify({'message': 'API key đã được vô hiệu hóa.'}), 200

# Endpoint kiểm tra logging
@app.route('/test-logging', methods=['POST'])
@jwt_required_with_roles()
@swag_from({
    'tags': ['Testing'],
    'security': [{'apiKey': []}],
    'responses': {
        200: {
            'description': 'Logging hoạt động đúng',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string'
                    }
                }
            }
        },
        403: {
            'description': 'Forbidden: Insufficient permissions.'
        }
    }
})
def test_logging():
    """
    Endpoint kiểm tra logging.
    ---
    """
    logger.info("Test logging endpoint called.")
    print("Test logging endpoint called.")
    return jsonify({'message': 'Logging is working!'}), 200

# Endpoint liệt kê tất cả các routes
@app.route('/routes', methods=['GET'])
@swag_from({
    'tags': ['Utility'],
    'responses': {
        200: {
            'description': 'Danh sách tất cả các routes',
            'schema': {
                'type': 'object',
                'example': {
                    "/login": "POST",
                    "/admin/create-api-key": "POST",
                    # Các routes khác...
                }
            }
        }
    }
})
def list_routes():
    """
    Endpoint liệt kê tất cả các routes.
    ---
    """
    import urllib
    output = {}
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods))
        url = urllib.parse.unquote(str(rule))
        output[url] = methods
    return jsonify(output), 200

# Endpoint đánh giá phát âm với JWT
@app.route('/api/pronunciation-assessment', methods=['POST'])
@jwt_required_with_roles()
@swag_from({
    'tags': ['Pronunciation Assessment'],
    'security': [{'apiKey': []}],
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'file',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'Tệp âm thanh cần đánh giá'
        },
        {
            'name': 'language',
            'in': 'formData',
            'type': 'string',
            'required': False,
            'default': 'en-US',
            'description': 'Ngôn ngữ của tệp âm thanh'
        },
        {
            'name': 'reference_text',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Văn bản tham khảo'
        }
    ],
    'responses': {
        200: {
            'description': 'Đánh giá phát âm thành công',
            'schema': {
                'type': 'object',
                'properties': {
                    'score': {
                        'type': 'number',
                        'format': 'float'
                    },
                    'details': {
                        'type': 'string'
                    }
                    # Các trường khác tùy theo kết quả đánh giá
                }
            }
        },
        422: {
            'description': 'Lỗi yêu cầu, không có tệp hoặc tham số yêu cầu'
        },
        500: {
            'description': 'Lỗi trong quá trình đánh giá'
        },
        403: {
            'description': 'Forbidden: Insufficient permissions.'
        }
    }
})
def pronunciation_assessment():
    """
    Endpoint để đánh giá phát âm.
    ---
    """
    logger.info("Đã nhận yêu cầu đánh giá phát âm.")

    if 'file' not in request.files:
        logger.warning("Không tìm thấy phần file trong yêu cầu.")
        return jsonify({'msg': 'No file part in the request'}), 422

    file = request.files['file']

    if file.filename == '':
        logger.warning("Không có tệp được chọn.")
        return jsonify({'msg': 'No selected file'}), 422

    if not allowed_file(file.filename):
        logger.warning(f"Loại tệp không được phép: {file.filename}")
        return jsonify({'msg': f'File type not allowed. Allowed types: {app.config["ALLOWED_EXTENSIONS"]}'}), 422

    # Lưu tệp âm thanh
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    logger.info(f"Tệp đã được lưu: {file_path}")

    # Lấy các tham số khác
    language = request.form.get('language', 'en-US')
    reference_text = request.form.get('reference_text', None)

    if not reference_text:
        logger.warning("reference_text là bắt buộc.")
        return jsonify({'msg': 'reference_text is required'}), 422

    # Thực hiện đánh giá phát âm
    try:
        results = pronunciation_assessment_configured_with_whisper(
            filename=file_path,
            language=language,
            reference_text=reference_text,
            processor=processor,
            model=model,
            device=device
        )
        logger.info(f"Đánh giá phát âm hoàn thành cho tệp: {filename}")
    except Exception as e:
        logger.error(f"Lỗi trong quá trình đánh giá: {e}")
        return jsonify({'msg': str(e)}), 500
    finally:
        # Xóa tệp sau khi xử lý (tuỳ chọn)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Tệp đã bị xóa: {file_path}")

    return jsonify(results), 200

# Endpoint chính
@app.route('/')
def index():
    return "API Flask cho Đánh Giá Phát Âm đang chạy."

if __name__ == '__main__':
    # Chạy Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
