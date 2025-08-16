import os
import cv2
import numpy as np
import tensorflow as tf
import neuralgym as ng
from PIL import Image
import logging
import threading

from preprocess_image import preprocess_image
from inpaint_model import InpaintCAModel

logger = logging.getLogger(__name__)

class WatermarkRemovalService:
    """基于原始main.py逻辑的水印去除服务类"""

    def __init__(self):
        self.FLAGS = None
        self.model = None
        self.checkpoint_dir = 'model/'
        self._lock = threading.Lock()
        self._load_config()
        logger.info("WatermarkRemovalService initialized")

    def _load_config(self):
        """加载配置文件 - 基于原始main.py第26-30行"""
        try:
            # 设置TensorFlow日志级别
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
            
            # 加载配置，就像原始main.py第26行
            self.FLAGS = ng.Config('inpaint.yml')
            # 创建模型实例，就像原始main.py第30行
            self.model = InpaintCAModel()
            logger.info("Model configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise e

    def process_image(self, input_path, output_path, watermark_type='istock'):
        """
        处理图像去水印 - 完全基于原始main.py的逻辑
        
        Args:
            input_path: 输入图像路径
            output_path: 输出图像路径  
            watermark_type: 水印类型
            
        Returns:
            bool: 处理是否成功
        """
        try:
            with self._lock:  # 确保线程安全
                logger.info(f"Processing image: {input_path}")
                
                # 步骤1: 加载和预处理图像 (就像main.py第31-32行)
                image = Image.open(input_path)
                input_image = preprocess_image(image, watermark_type)
                
                # 步骤2: 检查预处理结果 (就像main.py第37行)
                if input_image.shape == (0,):
                    logger.error("Image preprocessing failed - unsupported size")
                    return False
                
                # 步骤3: 重置默认图 (就像main.py第33行)
                tf.reset_default_graph()
                
                # 步骤4: 创建会话配置 (就像main.py第35-36行)
                sess_config = tf.ConfigProto()
                sess_config.gpu_options.allow_growth = True
                
                # 步骤5: 在会话中执行所有操作 (就像main.py第38-58行)
                with tf.Session(config=sess_config) as sess:
                    # 将输入图像转换为TensorFlow常量 (第39行)
                    input_image_tensor = tf.constant(input_image, dtype=tf.float32)
                    
                    # 构建服务器图 (第40行)
                    output = self.model.build_server_graph(self.FLAGS, input_image_tensor)
                    
                    # 后处理输出 (第41-43行)
                    output = (output + 1.) * 127.5
                    output = tf.reverse(output, [-1])
                    output = tf.saturate_cast(output, tf.uint8)
                    
                    # 加载预训练模型 (第44-53行)
                    vars_list = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES)
                    assign_ops = []
                    for var in vars_list:
                        vname = var.name
                        from_name = vname
                        try:
                            var_value = tf.contrib.framework.load_variable(
                                self.checkpoint_dir, from_name
                            )
                            assign_ops.append(tf.assign(var, var_value))
                        except Exception as e:
                            logger.warning(f"Could not load variable {vname}: {e}")
                    
                    # 运行变量赋值 (第53行)
                    sess.run(assign_ops)
                    logger.info('Model loaded for this inference')
                    
                    # 执行推理 (第55行)
                    result = sess.run(output)
                    
                    # 保存结果 (第56-57行)
                    cv2.imwrite(output_path, cv2.cvtColor(
                        result[0][:, :, ::-1], cv2.COLOR_BGR2RGB
                    ))
                
                logger.info(f"Image processed successfully: {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False