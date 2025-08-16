# 使用Python 3.7官方镜像，兼容TensorFlow 1.15
FROM python:3.7-slim

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/app:$PYTHONPATH

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制requirements文件
COPY requirements.txt .

# 升级pip
RUN pip install --upgrade pip

# 先安装基础数值计算库
RUN pip install --no-cache-dir numpy==1.19.5

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装neuralgym
RUN pip install git+https://github.com/JiahuiYu/neuralgym

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /app/uploads /app/outputs

# 设置权限
RUN chmod +x *.py

# 暴露端口（如果需要web服务）
EXPOSE 8080

# 默认命令 - 保持容器运行
CMD ["tail", "-f", "/dev/null"]