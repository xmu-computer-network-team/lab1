import numpy as np
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
from encoder.frame_builder import FrameBuilder
import matplotlib.pyplot as pyplot

if __name__ == "__main__":
    fb = FrameBuilder()
    our_dir = "test/template_test_attachments"
    os.makedirs(our_dir, exist_ok=True)
    out_path = os.path.join(our_dir,"template.png")
    pyplot.imsave(out_path, fb.template, cmap="gray", vmin=0, vmax=255)
    print("saved",out_path)