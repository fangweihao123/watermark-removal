#!/bin/bash
set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting Watermark Removal API with Flask${NC}"

# 创建必要的目录
mkdir -p /app/uploads /app/outputs /app/logs

# 检查模型文件
if [ ! -f "/app/model/checkpoint" ]; then
    echo -e "${YELLOW}⚠️  Warning: Model checkpoint not found at /app/model/checkpoint${NC}"
    echo -e "${YELLOW}   Please ensure model files are properly mounted or copied${NC}"
fi

# 检查配置文件
if [ ! -f "/app/inpaint.yml" ]; then
    echo -e "${YELLOW}⚠️  Warning: inpaint.yml not found${NC}"
fi

# 显示配置信息
echo -e "${BLUE}📋 Configuration:${NC}"
echo "  - Flask App: ${FLASK_APP:-app.py}"
echo "  - Environment: ${FLASK_ENV:-development}"
echo "  - Host: ${FLASK_HOST:-0.0.0.0}"
echo "  - Port: ${FLASK_PORT:-8080}"
echo "  - Upload Folder: ${UPLOAD_FOLDER:-/app/uploads}"
echo "  - Output Folder: ${OUTPUT_FOLDER:-/app/outputs}"

# 设置默认值
export FLASK_HOST=${FLASK_HOST:-0.0.0.0}
export FLASK_PORT=${FLASK_PORT:-8080}
export UPLOAD_FOLDER=${UPLOAD_FOLDER:-/app/uploads}
export OUTPUT_FOLDER=${OUTPUT_FOLDER:-/app/outputs}

echo -e "${GREEN}🌟 Starting Flask development server...${NC}"

# 启动Flask应用
python -c "
import os
from app import app

if __name__ == '__main__':
    app.run(
        host=os.environ.get('FLASK_HOST', '0.0.0.0'),
        port=int(os.environ.get('FLASK_PORT', 8080)),
        debug=False,
        threaded=True,
        use_reloader=False
    )
"