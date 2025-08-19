import os
import cv2
import numpy as np
import tensorflow as tf
import neuralgym as ng
from PIL import Image
import logging
import threading
import time
import tempfile
import shutil
import json
import moviepy.editor as mp

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
        self.sess = None
        self.output_tensor = None
        self.input_placeholder = None
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

    def process_video(self, input_path, output_path, 
        watermark_type='istock', task_id=None):
        """
        处理视频去水印
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            watermark_type: 水印类型
            task_id: 任务ID，用于进度跟踪
        
        Returns:
            bool: 处理是否成功
        """
        try:
            with self._lock:
                logger.info(f"Processing video: {input_path}")

                # 加载视频
                video = mp.VideoFileClip(input_path)
                
                # 调试信息：打印视频属性
                logger.info(f"Video duration: {video.duration}")
                logger.info(f"Video fps: {video.fps}")
                logger.info(f"Video size: {video.size}")

                # 尝试获取duration和fps，如果为None则使用备用方法
                duration = video.duration
                fps = video.fps
                
                # 如果moviepy无法获取fps，尝试使用opencv获取
                if fps is None:
                    try:
                        import cv2
                        cap = cv2.VideoCapture(input_path)
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        cap.release()
                        logger.info(f"Using OpenCV fps: {fps}")
                    except Exception as e:
                        logger.warning(f"Failed to get fps from OpenCV: {e}")
                        fps = 25.0  # 默认帧率
                        logger.info(f"Using default fps: {fps}")
                
                # 如果moviepy无法获取duration，尝试计算
                if duration is None:
                    try:
                        import cv2
                        cap = cv2.VideoCapture(input_path)
                        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                        fps_cv = cap.get(cv2.CAP_PROP_FPS)
                        cap.release()
                        if fps_cv > 0:
                            duration = frame_count / fps_cv
                            logger.info(f"Calculated duration: {duration}")
                    except Exception as e:
                        logger.warning(f"Failed to calculate duration: {e}")

                # 最终检查
                if duration is None or duration <= 0:
                    logger.error("Could not determine video duration")
                    return False
                    
                if fps is None or fps <= 0:
                    logger.error("Could not determine video fps")
                    return False

                # 检查视频长度限制（60秒）
                if duration > 60:
                    logger.error("Video duration exceeds 60 seconds limit")
                    return False

                # 创建临时目录处理帧
                temp_dir = tempfile.mkdtemp()

                # 初始化TensorFlow会话（只初始化一次）
                tf.reset_default_graph()
                sess_config = tf.ConfigProto()
                sess_config.gpu_options.allow_growth = True

                try:
                    with tf.Session(config=sess_config) as sess:
                        # 预加载模型（只加载一次）
                        dummy_input = tf.placeholder(tf.float32, shape=[1, None, None, 6])
                        output_tensor = self.model.build_server_graph(self.FLAGS, dummy_input)
                        output_tensor = (output_tensor + 1.) * 127.5
                        output_tensor = tf.reverse(output_tensor, [-1])
                        output_tensor = tf.saturate_cast(output_tensor, tf.uint8)

                        # 加载预训练模型权重
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

                        sess.run(assign_ops)
                        logger.info('Model loaded once for video processing')

                        # 提取和处理帧
                        frames = []
                        total_frames = int(duration * fps)

                        for i, frame in enumerate(video.iter_frames()):
                            if task_id:
                                self._update_progress(task_id, i / total_frames * 0.8)  # 80%用于处理帧

                            # 保存帧为临时图片
                            frame_path = os.path.join(temp_dir, f"frame_{i:06d}.png")
                            cv2.imwrite(frame_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

                            # 处理帧去水印（复用已加载的模型）
                            processed_frame_path = os.path.join(temp_dir, f"processed_{i:06d}.png")
                            success = self._process_single_frame_with_session(
                                frame_path, processed_frame_path, watermark_type, sess, dummy_input, output_tensor)

                            if success:
                                frames.append(processed_frame_path)
                            else:
                                logger.warning(f"Failed to process frame {i}")
                                frames.append(frame_path)  # 使用原帧

                    # 重新组装视频
                    if task_id:
                        self._update_progress(task_id, 0.9)  # 90%开始组装

                    processed_frames = [mp.ImageClip(frame, duration=1/fps) for frame in frames]
                    final_video = mp.concatenate_videoclips(processed_frames, method="compose")

                    # 添加原始音频
                    if video.audio:
                        final_video = final_video.set_audio(video.audio)

                    # 输出视频
                    final_video.write_videofile(output_path, fps=fps, verbose=False, logger=None)

                    if task_id:
                        self._update_progress(task_id, 1.0)  # 100%完成

                    logger.info(f"Video processed successfully: {output_path}")
                    return True

                finally:
                    # 清理临时文件
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    video.close()

        except Exception as e:
            logger.error(f"Error processing video: {e}")
            if task_id:
                self._update_progress(task_id, -1)  # 标记失败
            return False

    def _process_single_frame(self, input_path, output_path, watermark_type):
        try:
            # 预处理图像
            image = Image.open(input_path)
            input_image = preprocess_image(image, watermark_type)

            if input_image.shape == (0,):
                return False

            # 重置默认图并创建新会话 (和process_image方法相同的逻辑)
            tf.reset_default_graph()
            
            # 创建会话配置
            sess_config = tf.ConfigProto()
            sess_config.gpu_options.allow_growth = True
            
            # 在会话中执行推理
            with tf.Session(config=sess_config) as sess:
                # 将输入图像转换为TensorFlow常量
                input_image_tensor = tf.constant(input_image, dtype=tf.float32)
                
                # 构建服务器图
                output = self.model.build_server_graph(self.FLAGS, input_image_tensor)
                
                # 后处理输出
                output = (output + 1.) * 127.5
                output = tf.reverse(output, [-1])
                output = tf.saturate_cast(output, tf.uint8)
                
                # 加载预训练模型
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
                
                # 运行变量赋值
                sess.run(assign_ops)
                
                # 执行推理
                result = sess.run(output)
                
                # 保存结果
                cv2.imwrite(output_path, cv2.cvtColor(
                    result[0][:, :, ::-1], cv2.COLOR_BGR2RGB
                ))

            return True
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return False

    def _process_single_frame_with_session(self, input_path, output_path, watermark_type, sess, input_placeholder, output_tensor):
        """
        使用已有的TensorFlow会话处理单帧（避免重复加载模型）
        """
        try:
            # 预处理图像
            image = Image.open(input_path)
            input_image = preprocess_image(image, watermark_type)

            if input_image.shape == (0,):
                return False

            # 使用已有的会话执行推理
            result = sess.run(output_tensor, feed_dict={input_placeholder: input_image})

            # 保存结果
            cv2.imwrite(output_path, cv2.cvtColor(
                result[0][:, :, ::-1], cv2.COLOR_BGR2RGB
            ))

            return True
        except Exception as e:
            logger.error(f"Error processing frame with session: {e}")
            return False

    def _update_progress(self, task_id, progress):
        progress_file = f"progress_{task_id}.json"
        progress_data = {
            "task_id": task_id,
            "progress": progress,
            "timestamp": time.time(),
            "status": "processing" if progress >= 0 else "failed"
        }

        try:
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f)
        except:
            pass

    def get_progress(self, task_id):
        """获取任务进度"""
        progress_file = f"progress_{task_id}.json"
        try:
            with open(progress_file, 'r') as f:
                return json.load(f)
        except:
            return {"task_id": task_id, "progress": 0, "status": "not_found"}