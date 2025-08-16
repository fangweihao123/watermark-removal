# AWS EC2 Docker 部署指南 - 水印移除项目

## 🎯 概述

本指南将帮助您在 AWS EC2 实例上使用 Docker 部署水印移除项目。该方案解决了本地部署配置复杂的问题，提供了完整的自动化部署流程。

## 📋 前置要求

### AWS 资源要求
- **EC2 实例类型**: 推荐 `t3.large` 或更高配置
- **存储**: 至少 20GB EBS 存储
- **内存**: 至少 8GB RAM（推荐 16GB）
- **操作系统**: Ubuntu 20.04 LTS 或 18.04 LTS
- **安全组**: 开放端口 22 (SSH) 和 8080 (应用端口)

### 本地要求
- SSH 客户端
- AWS CLI (可选，用于 EC2 管理)

## 🚀 快速部署

### 步骤 1: 创建 EC2 实例

1. 登录 AWS 控制台
2. 启动新的 EC2 实例:
   - **AMI**: Ubuntu Server 20.04 LTS
   - **实例类型**: t3.large (2 vCPU, 8GB RAM)
   - **存储**: 30GB gp3
   - **安全组**: 允许 SSH (22) 和 HTTP (8080)

### 步骤 2: 连接到 EC2 实例

```bash
# 使用 SSH 连接到实例
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

### 步骤 3: 运行部署脚本

```bash
# 下载部署脚本
wget https://raw.githubusercontent.com/zuruoke/watermark-removal/master/deploy-ec2.sh

# 给脚本执行权限
chmod +x deploy-ec2.sh

# 运行部署脚本
./deploy-ec2.sh
```

### 步骤 4: 下载预训练模型

由于模型文件较大，需要手动下载：

1. 访问 [Google Drive 链接](https://drive.google.com/drive/folders/1xRV4EdjJuAfsX9pQme6XeoFznKXG0ptJ?usp=sharing)
2. 下载所有模型文件
3. 上传到 EC2 实例的 `watermark-removal/model/` 目录

```bash
# 在 EC2 上创建 model 目录
mkdir -p ~/watermark-removal/model/

# 使用 scp 上传模型文件
scp -i your-key.pem model/* ubuntu@your-ec2-ip:~/watermark-removal/model/
```

## 📖 详细部署步骤

### 1. 系统环境准备

部署脚本会自动执行以下操作：

- 更新系统包
- 安装 Docker 和 Docker Compose
- 配置用户权限
- 克隆项目代码

### 2. Docker 配置

#### Dockerfile 特性
- 基于 Ubuntu 18.04 (兼容 TensorFlow 1.15)
- 预装所有 Python 依赖
- 配置 neuralgym 库
- 创建工作目录和权限设置

#### Docker Compose 配置
- 自动端口映射 (8080)
- 数据卷挂载 (uploads, outputs, model)
- 环境变量配置
- 自动重启策略

### 3. 服务启动

部署脚本会自动：
1. 构建 Docker 镜像
2. 启动 Docker Compose 服务
3. 验证服务状态

## 🖼️ 使用方法

### 基础使用

1. **上传图片到 EC2**:
```bash
# 从本地上传图片
scp -i your-key.pem input.jpg ubuntu@your-ec2-ip:~/watermark-removal/uploads/
```

2. **处理图片**:
```bash
# 进入项目目录
cd ~/watermark-removal

# 使用 Docker 处理图片
docker exec watermark-removal-app python3 main.py \
  --image /app/uploads/input.jpg \
  --output /app/outputs/result.png \
  --checkpoint_dir /app/model/ \
  --watermark_type istock
```

3. **下载结果**:
```bash
# 下载处理结果到本地
scp -i your-key.pem ubuntu@your-ec2-ip:~/watermark-removal/outputs/result.png ./
```

### 批量处理

```bash
# 批量处理多张图片
docker exec watermark-removal-app python3 batch_test.py
```

### 支持的水印类型

- `istock` - iStock 水印
- 其他类型可根据需要配置

## 🔧 管理和维护

### 服务管理命令

```bash
# 查看服务状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新服务
git pull origin master
docker-compose build
docker-compose up -d
```

### 容器管理

```bash
# 进入容器
docker exec -it watermark-removal-app bash

# 查看容器资源使用
docker stats watermark-removal-app

# 清理未使用的镜像
docker system prune -a
```

## 🔍 故障排除

### 常见问题

1. **内存不足**
   - 确保 EC2 实例至少有 8GB RAM
   - 考虑使用交换文件或升级实例类型

2. **模型文件缺失**
   - 确认 model/ 目录下有所有必需文件
   - 检查文件权限和路径

3. **Docker 权限问题**
   - 重新登录 SSH 会话激活用户组权限
   - 或使用 `sudo` 运行 Docker 命令

4. **端口访问问题**
   - 检查 AWS 安全组设置
   - 确认防火墙配置

### 日志分析

```bash
# 查看应用日志
docker-compose logs watermark-removal

# 查看 Docker 系统日志
sudo journalctl -u docker

# 查看容器内部日志
docker exec watermark-removal-app tail -f /var/log/syslog
```

## 📊 性能优化

### EC2 实例建议

| 用途 | 实例类型 | vCPU | 内存 | 网络 |
|------|----------|------|------|------|
| 测试环境 | t3.medium | 2 | 4GB | 低-中等 |
| 生产环境 | t3.large | 2 | 8GB | 中等 |
| 高负载 | c5.xlarge | 4 | 8GB | 高 |
| GPU 加速 | p3.2xlarge | 8 | 61GB | 高+GPU |

### 存储优化

- 使用 gp3 EBS 卷提高 I/O 性能
- 考虑使用 EFS 进行共享存储
- 定期清理 outputs 目录

## 🔒 安全建议

1. **网络安全**
   - 仅开放必要端口
   - 使用 VPC 和私有子网
   - 配置 HTTPS (如需 web 接口)

2. **访问控制**
   - 使用 IAM 角色而非访问密钥
   - 定期轮换 SSH 密钥
   - 启用 CloudTrail 日志

3. **数据安全**
   - 加密 EBS 卷
   - 定期备份重要数据
   - 不在容器中存储敏感信息

## 💰 成本优化

1. **实例管理**
   - 使用 Spot 实例节省成本
   - 设置自动停止策略
   - 监控实际使用率

2. **存储优化**
   - 定期清理临时文件
   - 使用生命周期策略管理 S3 存储
   - 压缩大文件

## 📈 监控和告警

### CloudWatch 监控

```bash
# 安装 CloudWatch 代理
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
```

### 基础监控指标

- CPU 使用率
- 内存使用率
- 磁盘使用率
- 网络流量
- Docker 容器状态

## 🤝 支持和反馈

如果遇到部署问题：

1. 检查本文档的故障排除部分
2. 查看项目 [GitHub Issues](https://github.com/zuruoke/watermark-removal/issues)
3. 提交新的问题报告

## 📝 更新日志

- **v1.0.0** - 初始版本，支持基础 Docker 部署
- **v1.1.0** - 添加 docker-compose 支持
- **v1.2.0** - 优化 EC2 部署流程

---

**注意**: 此项目仅供学术研究使用，请遵守相关法律法规。