import os
import sys
import unittest
import numpy as np
import cv2

# Add workspace to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.person_detector import PersonDetector

class TestPersonDetector(unittest.TestCase):
    def setUp(self):
        self.detector = PersonDetector()
        self.test_dir = os.path.join(os.path.dirname(__file__), "tmp_test_images")
        os.makedirs(self.test_dir, exist_ok=True)

    def test_missing_image_handled_gracefully(self):
        """Missing or unreadable file must not crash."""
        detected, conf, boxes = self.detector.detect("non_existent_file.jpg")
        self.assertFalse(detected)
        self.assertEqual(conf, 0.0)
        self.assertEqual(len(boxes), 0)

    def test_blank_image_no_human(self):
        """Blank image should have 0 detections."""
        blank_path = os.path.join(self.test_dir, "blank.jpg")
        blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.imwrite(blank_path, blank_img)

        detected, conf, boxes = self.detector.detect(blank_path)
        self.assertFalse(detected)
        self.assertEqual(conf, 0.0)
        self.assertEqual(len(boxes), 0)

    def test_annotate_and_save(self):
        """Annotating an image should create the target file with valid dimensions."""
        src_path = os.path.join(self.test_dir, "test_input.jpg")
        dst_path = os.path.join(self.test_dir, "test_output.jpg")
        img = np.full((480, 640, 3), 128, dtype=np.uint8)
        cv2.imwrite(src_path, img)

        # Mock a box to test annotation rendering
        mock_boxes = [(100, 100, 200, 350)]
        self.detector.annotate_and_save(src_path, dst_path, mock_boxes, 0.88)

        self.assertTrue(os.path.exists(dst_path))
        annotated = cv2.imread(dst_path)
        self.assertIsNotNone(annotated)
        self.assertEqual(annotated.shape, (480, 640, 3))

if __name__ == "__main__":
    unittest.main()
