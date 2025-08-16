from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import uuid
import os
import logging
from datetime import datetime
import traceback
from service.watermark_service import WatermarkRemovalService
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

service = WatermarkRemovalService()

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "service": "watermark-removal",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route('/api/v1/remove-watermark', methods=['POST'])
def remove_watermark():
    """去水印API端点"""
    try:
        # 检查是否有文件上传
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400

        # 获取水印类型参数
        watermark_type = request.form.get('watermark_type', 'istock')

        # 生成唯一的文件名
        task_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        input_filename = f"{task_id}_input.{file_extension}"
        output_filename = f"{task_id}_output.png"

        # 保存上传的文件
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        file.save(input_path)
        logger.info(f"File saved: {input_path}")

        # 处理图像
        success = service.process_image(
            input_path, output_path, watermark_type
        )

        if success:
            return jsonify({
                "success": True,
                "task_id": task_id,
                "message": "Watermark removed successfully",
                "download_url": f"/api/v1/download/{task_id}"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to process image"
            }), 500

    except RequestEntityTooLarge:
        return jsonify({"error": "File too large"}), 413
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500
    finally:
        # 清理输入文件
        if 'input_path' in locals() and os.path.exists(input_path):
            try:
                os.remove(input_path)
            except:
                pass

@app.route('/api/v1/download/<task_id>', methods=['GET'])
def download_result(task_id):
    """下载处理结果"""
    try:
        output_filename = f"{task_id}_output.png"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        if not os.path.exists(output_path):
            return jsonify({"error": "File not found"}), 404

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"watermark_removed_{task_id}.png",
            mimetype='image/png'
        )
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({"error": "Failed to download file"}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large"}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

    app.run(host='0.0.0.0', port=8080, debug=False)