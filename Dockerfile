# 使用Ubuntu 18.04作为基础镜像，因为TensorFlow 1.15需要较旧的环境
FROM ubuntu:18.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/app:$PYTHONPATH

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
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
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip3 install --no-cache-dir -r requirements.txt

# 安装neuralgym
RUN pip3 install git+https://github.com/JiahuiYu/neuralgym

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /app/uploads /app/outputs

# 设置权限
RUN chmod +x *.py

# 暴露端口（如果需要web服务）
EXPOSE 8080

# 默认命令
CMD ["python3", "main.py", "--help"]