# -*- coding: utf-8 -*-
"""
# @file name  : 2_train_lenet.py
# @author     : Jimeng Shi
# @date       : 2020-01-18 23:05:00
# @brief      : train classification model of RMB
"""
import os
import numpy as np
from matplotlib import pyplot as plt

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
import torch.optim as optim

from common import utils
from models_diy import LeNet5_01
from rmb_dataset import RMBDataset


utils.set_seed()
rmb_label = {"1": 0, "100": 1}

MAX_EPOCH = 10
BATCH_SIZE = 16
LR = 0.01
log_interval = 10
val_interval = 1

# ============================ step 1/5 数据 ============================
split_dir = os.path.join("/tmp", "rmb_split")
train_dir = os.path.join(split_dir, "train")
valid_dir = os.path.join(split_dir, "valid")
test_dir = os.path.join(split_dir, "test")

norm_mean = [0.485, 0.456, 0.406]
norm_std = [0.229, 0.224, 0.225]

train_transform = transforms.Compose(
    [
        transforms.Resize((32, 32)),
        transforms.RandomCrop(32, padding=4),
        transforms.ToTensor(),
        transforms.Normalize(norm_mean, norm_std),
    ]
)

valid_transform = transforms.Compose(
    [
        transforms.Resize((32, 32)),
        transforms.ToTensor(),
        transforms.Normalize(norm_mean, norm_std),
    ]
)

train_data = RMBDataset(data_dir=train_dir, transform=train_transform)
valid_data = RMBDataset(data_dir=valid_dir, transform=valid_transform)

train_loader = DataLoader(dataset=train_data, batch_size=BATCH_SIZE, shuffle=True)
valid_loader = DataLoader(dataset=valid_data, batch_size=BATCH_SIZE)

# ============================ step 2/5 模型 ============================
net = LeNet5_01(classes=2)
net.initialize_weights()

# ============================ step 3/5 损失函数 ============================
criterion = nn.CrossEntropyLoss()  # 选择损失函数

# ============================ step 4/5 优化器 ============================
optimizer = optim.SGD(net.parameters(), lr=LR, momentum=0.9)
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)

# ============================ step 5/5 训练 ============================
train_curve = list()
valid_curve = list()

for epoch in range(MAX_EPOCH):
    print("Epoch[{:0>3}/{:0>3}]".format(epoch, MAX_EPOCH))

    loss_mean = 0.0
    correct = 0.0
    total = 0.0

    net.train()
    for i, data in enumerate(train_loader):
        # forward
        inputs, labels = data
        outputs = net(inputs)

        # backward
        optimizer.zero_grad()
        loss = criterion(outputs, labels)
        loss.backward()

        # update weights
        optimizer.step()

        # 统计分类情况
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).squeeze().sum().numpy()

        # 打印训练信息
        loss_mean += loss.item()
        train_curve.append(loss.item())
        if (i + 1) % log_interval == 0:
            loss_mean = loss_mean / log_interval
            print(
                "Training: Iteration[{:0>3}/{:0>3}] Loss: {:.4f} Acc:{:.2%}".format(
                    i + 1, len(train_loader), loss_mean, correct / total
                )
            )
            loss_mean = 0.0

    scheduler.step()  # 更新学习率

    # validate the model
    if (epoch + 1) % val_interval == 0:
        correct_val = 0.0
        total_val = 0.0
        loss_val = 0.0
        net.eval()
        with torch.no_grad():
            for j, data in enumerate(valid_loader):
                inputs, labels = data
                outputs = net(inputs)
                loss = criterion(outputs, labels)

                _, predicted = torch.max(outputs.data, 1)
                total_val += labels.size(0)
                correct_val += (predicted == labels).squeeze().sum().numpy()

                loss_val += loss.item()

            valid_curve.append(loss_val / valid_loader.__len__())
            print(
                "Valid:    Iteration[{:0>3}/{:0>3}] Loss: {:.4f} Acc:{:.2%}".format(
                    j + 1, len(valid_loader), loss_val, correct_val / total_val
                )
            )

train_x = range(len(train_curve))
train_y = train_curve

train_iters = len(train_loader)
valid_x = (
    np.arange(1, len(valid_curve) + 1) * train_iters * val_interval
)  # 由于valid中记录的是epochloss，需要对记录点进行转换到iterations
valid_y = valid_curve

plt.plot(train_x, train_y, label="Train")
plt.plot(valid_x, valid_y, label="Valid")

plt.legend(loc="upper right")
plt.ylabel("loss value")
plt.xlabel("Iteration")
plt.show()

# ============================ inference ============================

print("\nInference:\n")

test_data = RMBDataset(data_dir=test_dir, transform=valid_transform)
test_loader = DataLoader(dataset=test_data, batch_size=1)

for i, data in enumerate(test_loader):
    # forward
    inputs, labels = data
    outputs = net(inputs)
    _, predicted = torch.max(outputs.data, 1)

    rmb = 1 if predicted.numpy()[0] == 0 else 100
    print("模型获得{}元".format(rmb))
