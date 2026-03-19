import unittest
import cv2
import os
import numpy as np

# 将上级目录添加到可被直接引用的包路径
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decoder.locator import FrameLocator
from common.config import GRID_ROWS, GRID_COLS, BLOCK_SIZE

class LocatorTest(unittest.TestCase):
    def setUp(self):
        # 准备测试用的附件目录
        self.attachments_dir = os.path.join(os.path.dirname(__file__), 'locator_test_attachments')
        if not os.path.exists(self.attachments_dir):
            os.makedirs(self.attachments_dir)
            
    def test_locate_and_rectify(self):
        """测试定位和图片矫正逻辑"""
        # 待读取的测试畸变图像，这需要你在里面放一张手机拍摄的带二维码定位块的图像
        # 假设我们将传入文件名为 'distorted_frame.jpg'
        test_img_path = os.path.join(self.attachments_dir, 'distorted_frame.jpg')
        
        # 考虑到可能附件目录当前是空的，避免强行报错停在那
        if not os.path.exists(test_img_path):
            print(f"\n[跳过] 请在 {self.attachments_dir} 下放置命名为 'distorted_frame.jpg' 的测试图。")
            return
            
        # 读取彩色原图 (BGR)
        raw_frame = cv2.imread(test_img_path)
        self.assertIsNotNone(raw_frame, "测试图片读取失败，请检查文件是否损坏")
        
        # 实例化解码定位器
        locator = FrameLocator()
        
        # 运行被测方法
        corrected_frame = locator.locate_and_rectify(raw_frame)
        
        # 断言返回值：定位成功不应当返回 None
        self.assertIsNotNone(corrected_frame, "找不到足够的 Finder Pattern")
        
        # 断言形状：应该是一张灰度图 (二维数组)，且符合约定的统一输出尺寸
        expected_height = GRID_ROWS * BLOCK_SIZE
        expected_width = GRID_COLS * BLOCK_SIZE
        self.assertEqual(len(corrected_frame.shape), 2, "期望矫正后的图像是 2D 二维灰度图")
        self.assertEqual(corrected_frame.shape, (expected_height, expected_width), "矫正后的图像尺寸不符合预设的物理配置")
        
        # （可选）将输出结果保存下来以供查验
        output_path = os.path.join(self.attachments_dir, 'rectified_output.jpg')
        cv2.imwrite(output_path, corrected_frame)
        print(f"\n[成功] 矫正图已输出到: {output_path}")

if __name__ == '__main__':
    unittest.main()
