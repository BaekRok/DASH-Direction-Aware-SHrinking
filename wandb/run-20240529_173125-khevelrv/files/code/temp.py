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

# Define the CNN model
class ConvNet(nn.Module):
    def __init__(self, args):
        super(ConvNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 128, kernel_size=(3,3))
        self.relu1 = nn.ReLU()
        
        self.conv2 = nn.Conv2d(128, 256, kernel_size=(3,3))
        self.relu2 = nn.ReLU()
        
        self.conv3 = nn.Conv2d(256, 512, kernel_size=(3,3))
        self.relu3 = nn.ReLU()

        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(346112, 512)
        self.relu4 = nn.ReLU()
        self.fc2 = nn.Linear(512, 10)
        
        if args.depth == 1:
            self.conv2 = nn.Identity()
            self.conv3 = nn.Identity()
            self.fc1 = nn.Linear(115200, 512)
        if args.depth == 2:
            self.conv3 = nn.Identity()
            self.fc1 = nn.Linear(200704, 512)
    def forward(self, x):
        x = self.relu1(self.conv1(x))
        x = self.relu2(self.conv2(x))
        x = self.relu3(self.conv3(x))
        x = self.flatten(x)
        x = self.relu4(self.fc1(x))
        x = self.fc2(x)
        return x

def train(args):
    wandb.init(project="cifar10-cnn")

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

    model = ConvNet(args).to('cuda')

    # Define the loss function and optimizer
    criterion = nn.CrossEntropyLoss().to('cuda')
    optimizer = torch.optim.SGD(model.parameters(), momentum=0.9, lr=0.01)

    data_length = len(trainset)
    num_chunks = args.num_chunks
    num_iters_per_chunk = data_length // num_chunks

    chunks = random_split(trainset, [len(trainset) // num_chunks] * num_chunks)
    buffer = []

    # Training loop
    for chunk_idx in tqdm.tqdm(range(num_chunks)):
        buffer.append(chunks[chunk_idx])
        chunk_loader = DataLoader(ConcatDataset(buffer),
                                  batch_size=128,
                                  shuffle=True)

        for epoch in range(num_epochs[chunk_idx]):
            running_loss = 0.0
            correct_train = 0
            total_train = 0

            model.train()
            for inputs, labels in chunk_loader:
                # Forward pass
                outputs = model(inputs.to('cuda'))
                loss = criterion(outputs, labels.to('cuda'))

                # Backward pass and optimization
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                running_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total_train += labels.size(0)
                correct_train += (predicted == labels.to('cuda')).sum().item()

            # Evaluate the model on the validation set
            model.eval()
            correct_val = 0
            total_val = 0
            with torch.no_grad():
                for inputs, labels in test_loader:
                    outputs = model(inputs.to('cuda'))
                    _, predicted = torch.max(outputs.data, 1)
                    total_val += labels.to('cuda').size(0)
                    correct_val += (predicted == labels.to('cuda')).sum().item()

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
    parser.add_argument("--num_epochs", type=list, default=[100, 100])

    args = parser.parse_args()
    train(args)