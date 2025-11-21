#!/usr/bin/env python3
"""
resnet50 inference script for cpu/gpu profiling
jlr & uwindsor hackathon
"""

import torch
import torchvision.models as models
import torchvision.transforms as transforms
import time
import sys
from PIL import Image
import numpy as np

def create_dummy_image(size=(224, 224)):
    """create dummy rgb image"""
    return Image.fromarray(np.random.randint(0, 255, (*size, 3), dtype=np.uint8))

def load_resnet50(device='cpu'):
    """load pretrained resnet50"""
    print(f"loading resnet50 on {device}...")
    model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
    model = model.to(device)
    model.eval()
    print("model loaded")
    return model

def preprocess_image(image):
    """preprocess image for resnet50"""
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])
    return transform(image).unsqueeze(0)

def run_inference(model, input_tensor, device='cpu', num_iterations=10):
    """run repeated inference"""
    input_tensor = input_tensor.to(device)

    print("warming up...")
    with torch.no_grad():
        for _ in range(3):
            _ = model(input_tensor)

    print(f"running {num_iterations} iterations...")
    times = []

    with torch.no_grad():
        for i in range(num_iterations):
            start = time.time()
            output = model(input_tensor)
            if device == 'cuda':
                torch.cuda.synchronize()
            end = time.time()
            times.append(end - start)
            print(f"  iteration {i+1}/{num_iterations}: {(end-start)*1000:.2f} ms")

    return times, output

def main():
    device = 'cuda' if len(sys.argv) > 1 and sys.argv[1] == 'gpu' and torch.cuda.is_available() else 'cpu'
    num_iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print("-"*60)
    print("resnet50 inference profiling")
    print("-"*60)
    print(f"device: {device}")
    print(f"iterations: {num_iterations}")
    print(f"pytorch version: {torch.__version__}")
    if device == 'cuda':
        print(f"cuda available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"gpu: {torch.cuda.get_device_name(0)}")
    print("-"*60)

    model = load_resnet50(device)

    image = create_dummy_image()
    input_tensor = preprocess_image(image)

    times, output = run_inference(model, input_tensor, device, num_iterations)

    print("\n" + "-"*60)
    print("performance results")
    print("-"*60)
    print(f"average time: {np.mean(times)*1000:.2f} ms")
    print(f"median time: {np.median(times)*1000:.2f} ms")
    print(f"min time: {np.min(times)*1000:.2f} ms")
    print(f"max time: {np.max(times)*1000:.2f} ms")
    print(f"std deviation: {np.std(times)*1000:.2f} ms")
    print("-"*60)

    _, predicted_idx = torch.max(output, 1)
    print(f"predicted class index: {predicted_idx.item()}")

    return times

if __name__ == "__main__":
    main()
