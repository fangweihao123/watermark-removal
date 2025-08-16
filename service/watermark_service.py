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
    """水印去除服务类 - 线程安全的单例模式"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(WatermarkRemovalService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.model = None
            self.sess = None
            self.output_tensor = None
            self.input_placeholder = None
            self.graph = None
            self._lock = threading.Lock()
            self._load_model()
            self.initialized = True

    def _load_model(self):
        """加载模型 - 只加载一次"""
        try:
            logger.info("Loading watermark removal model...")

            # 设置TensorFlow配置
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

            FLAGS = ng.Config('inpaint.yml')
            self.model = InpaintCAModel()

            # 创建新的图
            self.graph = tf.Graph()

            with self.graph.as_default():
                # 创建输入占位符
                self.input_placeholder = tf.placeholder(
                    tf.float32,
                    shape=[None, None, None, 6],
                    name='input_image'
                )

                # 构建模型图
                self.output_tensor = self.model.build_server_graph(
                    FLAGS, self.input_placeholder
                )
                self.output_tensor = (self.output_tensor + 1.) * 127.5
                self.output_tensor = tf.reverse(self.output_tensor, [-1])
                self.output_tensor = tf.saturate_cast(self.output_tensor, tf.uint8)

                # 创建会话
                sess_config = tf.ConfigProto()
                sess_config.gpu_options.allow_growth = True
                self.sess = tf.Session(config=sess_config, graph=self.graph)

                # 加载预训练权重
                checkpoint_dir = 'model/'
                vars_list = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES)
                assign_ops = []

                for var in vars_list:
                    vname = var.name
                    from_name = vname
                    try:
                        var_value = tf.contrib.framework.load_variable(
                            checkpoint_dir, from_name
                        )
                        assign_ops.append(tf.assign(var, var_value))
                    except Exception as e:
                        logger.warning(f"Could not load variable {vname}: {e}")

                self.sess.run(assign_ops)
                logger.info("Model loaded successfully!")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise e

    def process_image(self, input_path, output_path, watermark_type='istock'):
        """
        处理图像去水印
        
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

                # 打开并预处理图像
                image = Image.open(input_path)
                input_image = preprocess_image(image, watermark_type)

                if input_image.shape == (0,):
                    logger.error("Image preprocessing failed - unsupported size")
                    return False

                # 使用已加载的模型进行推理
                with self.graph.as_default():
                    result = self.sess.run(
                        self.output_tensor,
                        feed_dict={self.input_placeholder: input_image}
                    )

                # 保存结果
                cv2.imwrite(output_path, cv2.cvtColor(
                    result[0][:, :, ::-1], cv2.COLOR_BGR2RGB
                ))

                logger.info(f"Image processed successfully: {output_path}")
                return True

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return False

    def __del__(self):
        """清理资源"""
        if hasattr(self, 'sess') and self.sess:
            self.sess.close()