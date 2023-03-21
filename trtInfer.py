from __future__ import print_function

import numpy as np
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
from PIL import Image

import time
import os

import argparse
import cv2
from pathlib import Path
import re

import sys, time
import cv2 as cv
import torch

class TensorRTInfer:
    """
    Implements inference for the EfficientNet TensorRT engine.
    """

    def __init__(self, engine_path):
        """
        :param engine_path: The path to the serialized engine to load from disk.
        """
        # Load TRT engine
        self.logger = trt.Logger(trt.Logger.ERROR)
        with open(engine_path, "rb") as f, trt.Runtime(self.logger) as runtime:
            assert runtime
            self.engine = runtime.deserialize_cuda_engine(f.read())
        assert self.engine
        self.context = self.engine.create_execution_context()
        assert self.context
        # Setup I/O bindings
        self.stream = cuda.Stream()
        self.inputs = []
        self.outputs = []
        self.allocations = []
        for i in range(self.engine.num_bindings):
            is_input = False
            if self.engine.binding_is_input(i):
                is_input = True
            name = self.engine.get_binding_name(i)
            dtype = self.engine.get_binding_dtype(i)
            shape = self.engine.get_binding_shape(i)
            if is_input:
                self.batch_size = shape[0]
            # size = np.dtype(trt.nptype(dtype)).itemsize
            # for s in shape:
            #     size *= s

            mem_size = abs(trt.volume(self.engine.get_binding_shape(self.engine[i]))) * self.engine.max_batch_size
            binding_type = trt.nptype(self.engine.get_binding_dtype(i))
            host_mem = cuda.pagelocked_empty(mem_size, binding_type)
            device_mem = cuda.mem_alloc(host_mem.nbytes)

            # allocation = cuda.mem_alloc(size)
            binding = {
                "index": i,
                "name": name,
                "dtype": np.dtype(trt.nptype(dtype)),
                "shape": list(shape),
                # "allocation": allocation,
                "host_mem": host_mem,
                "device_mem": device_mem
            }

            self.allocations.append(int(device_mem))
            if self.engine.binding_is_input(i):
                self.inputs.append(binding)
            else:
                self.outputs.append(binding)
        print(self.inputs)
        print(self.outputs)
        assert self.batch_size > 0
        assert len(self.inputs) > 0
        assert len(self.outputs) > 0
        assert len(self.allocations) > 0
    
    def infer(self, batch_data, top=1):

        self.inputs[0]["host_mem"] = batch_data

        # Transfer input data to the GPU.
        [cuda.memcpy_htod_async(inp["device_mem"], np.ascontiguousarray(inp["host_mem"]), self.stream) for inp in self.inputs]
        # Run inferenmemcpy_htod_asyncce.
        self.context.execute_async_v2(bindings=self.allocations, stream_handle=self.stream.handle)
        # Transfer predictions back from the GPU.
        [cuda.memcpy_dtoh_async(out["host_mem"], out["device_mem"], self.stream) for out in self.outputs]
        # Synchronize the stream
        self.stream.synchronize()

        trt_outputs = self.outputs[0]["host_mem"]

        # top_classes = np.flip(np.argsort(trt_outputs))[0:top]
        # top_scores =  np.flip(np.sort(trt_outputs))[0:top]

        return trt_outputs

def preprocess_image(image_path, the_dtype):
    mean = [123.675, 116.28, 103.53]
    std = [58.395, 57.12, 57.375]
    img = cv.imread(image_path)
    img = cv.resize(img, (512,512))
    img = (img - mean) / std
    img = np.transpose(img, (2,0,1))
    img = torch.tensor(img)
    np_image = np.float32(img.numpy()) # Batch
    return np_image



if __name__ == "__main__":
    engine_path = "tensorrt/simipu.trt"

    trt_infer = TensorRTInfer(engine_path)
    trt_dtype = trt_infer.inputs[0]["dtype"]

    image_file = "/home/insign2/work/Monocular-Depth-Estimation-Toolbox/dataset/endoscopy/train_fake/train/rgb/0002_1_0000_image_.jpg"
    batcher_data = preprocess_image(image_file, trt_dtype)
    
    for i in range(50):
        s = time.time()
        out_trt = trt_infer.infer(batcher_data, top=1)
        e = time.time()
        print((e-s)*1000, "ms")
    
    print(out_trt.shape)
    out_trt = out_trt.reshape(1, 1, 512, 512)
    out_trt = np.squeeze(np.transpose(out_trt, (0, 2, 3, 1)))
    out_trt  = out_trt / out_trt.max() * 255 
    out_trt = cv2.cvtColor(out_trt, cv2.COLOR_RGB2BGR)
    cv2.imwrite('./tensorrt/depthformer_trt.png', out_trt)