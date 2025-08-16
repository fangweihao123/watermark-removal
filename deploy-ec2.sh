#!/bin/bash

# AWS EC2 Docker 部署脚本 - 水印移除项目
# 使用方法: chmod +x deploy-ec2.sh && ./deploy-ec2.sh

set -e

echo "🚀 开始在 AWS EC2 上部署水印移除项目"

# 更新系统包
echo "📦 更新系统包..."
sudo apt-get update -y

# 安装必要的系统工具
echo "🔧 安装必要工具..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    unzip \
    wget

# 安装 Docker
echo "🐳 安装 Docker..."
if ! command -v docker &> /dev/null; then
    # 添加 Docker 官方 GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # 设置 Docker 仓库
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 安装 Docker Engine
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # 启动 Docker 服务
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # 将当前用户添加到 docker 组
    sudo usermod -aG docker $USER
    
    echo "✅ Docker 安装完成"
else
    echo "✅ Docker 已安装"
fi

# 安装 Docker Compose
echo "🔧 安装 Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose 安装完成"
else
    echo "✅ Docker Compose 已安装"
fi

# 克隆项目（如果不存在）
PROJECT_DIR="watermark-removal"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📥 克隆项目..."
    git clone https://github.com/zuruoke/watermark-removal.git
    cd $PROJECT_DIR
else
    echo "📁 进入项目目录..."
    cd $PROJECT_DIR
    git pull origin master
fi

# 创建必要的目录
echo "📁 创建必要目录..."
mkdir -p uploads outputs

# 下载预训练模型
echo "🤖 检查预训练模型..."
if [ ! -f "model/checkpoint" ]; then
    echo "⚠️  预训练模型未找到！"
    echo "请手动下载模型文件并放置在 model/ 目录下："
    echo "下载链接: https://drive.google.com/drive/folders/1xRV4EdjJuAfsX9pQme6XeoFznKXG0ptJ?usp=sharing"
    echo "模型文件包括: checkpoint, snap-0.data-00000-of-00001, snap-0.index, snap-0.meta"
    read -p "按回车键继续（确保已下载模型）..."
fi

# 构建 Docker 镜像
echo "🏗️  构建 Docker 镜像..."
docker build -t watermark-removal:latest .

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

echo ""
echo "🎉 部署完成！"
echo ""
echo "📋 使用说明:"
echo "1. 将待处理图片上传到 uploads/ 目录"
echo "2. 运行处理命令:"
echo "   docker exec watermark-removal-app python3 main.py --image /app/uploads/your_image.jpg --output /app/outputs/result.png --checkpoint_dir /app/model/ --watermark_type istock"
echo "3. 处理结果将保存在 outputs/ 目录"
echo ""
echo "🔧 管理命令:"
echo "- 查看日志: docker-compose logs -f"
echo "- 停止服务: docker-compose down"
echo "- 重启服务: docker-compose restart"
echo "- 进入容器: docker exec -it watermark-removal-app bash"
echo ""
echo "📖 更多信息请查看 EC2-DEPLOYMENT.md"