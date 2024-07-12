import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import tqdm
from torch.utils.data import ConcatDataset, random_split
import numpy as np
import argparse
import wandb
from torch.utils.data import Subset, DataLoader
from torch.utils.data import Dataset
import math

class ConvNet(nn.Module):
    def __init__(self, args):
        super(ConvNet, self).__init__()
        self.n = args.depth
        
        self.conv1 = nn.Conv2d(3, 96, kernel_size=(3, 3))
        self.bn1 = nn.BatchNorm2d(96)
        self.relu1 = nn.ReLU()
        
        conv_layers = []
        channels = 96
        for i in range(1, self.n + 1):
            channels = 96 * 2 ** (i - 1)
            conv_layers.append(nn.Conv2d(channels, channels, kernel_size=(3, 3)))
            conv_layers.append(nn.BatchNorm2d(channels))
            conv_layers.append(nn.ReLU())
            conv_layers.append(nn.Conv2d(channels, channels * 2, kernel_size=(3, 3), stride=2))
            conv_layers.append(nn.BatchNorm2d(channels * 2))
            conv_layers.append(nn.ReLU())
        self.conv_layers = nn.Sequential(*conv_layers)
        self.conv2 = nn.Conv2d(96 * 2 ** self.n, 96 * 2 ** self.n, kernel_size=(3,3))
        self.bn2 = nn.BatchNorm2d(96 * 2 ** self.n)
        self.relu2 = nn.ReLU()
        
        self.final_conv1 = nn.Conv2d(96 * 2 ** self.n, 96 * 2 ** self.n, kernel_size=(1, 1))
        self.final_bn1 = nn.BatchNorm2d(96 * 2 ** self.n)
        self.relu_final1 = nn.ReLU()
        self.final_conv2 = nn.Conv2d(96 * 2 ** self.n, 10, kernel_size=(1, 1))
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        
    def forward(self, x):
        x = self.relu1(self.conv1(x))
        x = self.conv_layers(x)
        x = self.relu_final1(self.final_conv1(x))
        x = self.final_conv2(x)
        x = self.avgpool(x)
        x = x.reshape(x.size(0), -1)
        return x

    
def train(args):
    wandb.init(project="cifar10-cnn")
    wandb.config.update(args, allow_val_change=True)
    
    mean = (0.4914, 0.4822, 0.4465)
    std = (0.2023, 0.1994, 0.2010)
    trans = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])

    trainset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=trans)
    testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=trans)

    train_loader = torch.utils.data.DataLoader(trainset, batch_size=128, shuffle=True)
    test_loader = torch.utils.data.DataLoader(testset, batch_size=128, shuffle=False)

    device = torch.device(f'cuda:{args.gpu}' if torch.cuda.is_available() else 'cpu')
    model = ConvNet(args).to(device)
    print(model)
    # Define the loss function and optimizer
    criterion = nn.CrossEntropyLoss().to(device)
    
    data_length = len(trainset)
    num_chunks = args.num_chunks
    num_iters_per_chunk = data_length // num_chunks
    
    chunks = random_split(trainset, [len(trainset) // num_chunks] * num_chunks)
    buffer = []

    # Training loop
    for chunk_idx in tqdm.tqdm(range(num_chunks)):
        num_epochs = args.num_epochs[chunk_idx]
        optimizer = torch.optim.SGD(model.parameters(), momentum=0.9, lr=0.05, weight_decay=0.001)
        scheduler = torch.optim.lr_scheduler.MultiStepLR(optimizer, milestones=range(1, num_epochs+1), gamma=0.97)
        buffer.append(chunks[chunk_idx])
        chunk_loader = DataLoader(ConcatDataset(buffer),
                                  batch_size=128,
                                  shuffle=True)

        for epoch in range(num_epochs):
            running_loss = 0.0
            correct_train = 0
            total_train = 0

            model.train()
            for inputs, labels in chunk_loader:
                # Forward pass
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)

                # Backward pass and optimization
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                running_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total_train += labels.size(0)
                correct_train += (predicted == labels).sum().item()
            scheduler.step()
            # Evaluate the model on the validation set
            model.eval()
            correct_val = 0
            total_val = 0
            with torch.no_grad():
                for inputs, labels in test_loader:
                    inputs, labels = inputs.to(device), labels.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    total_val += labels.size(0)
                    correct_val += (predicted == labels).sum().item()

            val_accuracy = correct_val / total_val

            # Print the average loss and accuracies for each epoch and log to wandb
            print(f"Chunk [{chunk_idx+1}/{num_chunks}], Epoch [{epoch+1}/{num_epochs}], Loss: {running_loss/len(chunk_loader):.4f}, "
                  f"Train Accuracy: {correct_train/total_train:.4f}, "
                  f"Test Accuracy: {val_accuracy:.4f}")
            wandb.log({"epoch": epoch + (chunk_idx * num_epochs), "loss": running_loss/len(chunk_loader),
                       "train_accuracy": correct_train/total_train, "test_accuracy": val_accuracy})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=2, help="Depth of the network (number of conv layers between 1 and 3)")
    parser.add_argument("--num_chunks", type=int, default=2, help="Number of chunks to split the training data into")
    parser.add_argument("--num_epochs", type=int, nargs='+', default=[100, 100])
    parser.add_argument("--gpu", type=int, default=0, help="GPU index to use (0, 1, ...)")

    args = parser.parse_args()
    args.num_epochs = list(map(lambda x: int(x), args.num_epochs))
    train(args)