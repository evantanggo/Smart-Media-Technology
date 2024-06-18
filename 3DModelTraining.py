import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from Models import ArmModel3D
import time
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from torch.utils.tensorboard import SummaryWriter
import glob

# Which arm should be trained?
ARM = 'right'  # 'left' or 'right'

# Number of landmarks to be used
num_landmarks = len(ArmModel3D.landmarkMask(ARM))

#### HYPERPARAMETERS ###
num_epochs = 100
learning_rate = 0.001
batch_size = 32

# Create writer for logging
writer = SummaryWriter(log_dir=f'runs/arms_3D_{ARM}_{time.asctime()}')

# Custom Dataset class for PyTorch
class PoseGestureDataset(Dataset):
    def __init__(self, data):
        self.X = []
        for row in data.itertuples(index=False):
            landmarks = []
            for i in range(2, num_landmarks + 2): # landmark data starts at 2, 0 is 'az' & 1 is 'el'
                x, y, z = map(float, row[i].split(','))
                landmarks.extend([x, y, z])
            self.X.append(landmarks)
        self.X = torch.tensor(self.X, dtype=torch.float32)
        self.az = torch.tensor(data['az'].values, dtype=torch.float32).unsqueeze(1)
        self.el = torch.tensor(data['el'].values, dtype=torch.float32).unsqueeze(1)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], torch.tensor([self.az[idx], self.el[idx]])

# Path to the directory containing the CSV files
data_directory = f'TrainData/3D_data_{ARM}/'

# Get a list of all CSV files in the directory
csv_files = glob.glob(data_directory + f'3D_data_{ARM}_*.csv')

# Read and concatenate all CSV files into a single DataFrame
data_frames = [pd.read_csv(file) for file in csv_files]
data = pd.concat(data_frames, ignore_index=True)

# Split the data into training and testing sets
train_data, test_data = train_test_split(data, test_size=0.2, random_state=42)

# Create DataLoader for PyTorch
train_dataset = PoseGestureDataset(train_data)
test_dataset = PoseGestureDataset(test_data)
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

#single_sample = next(iter(train_loader))
#print(single_sample)
#quit()
# Initialize the model, loss function and optimizer
model = ArmModel3D.PoseGestureModel()
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

# Training loop
epoch_loss_train, epoch_loss_test = [], []  # store epoch loss
epoch_acc_train, epoch_acc_test = [], [] # store epoch accuracy


for epoch in range(num_epochs):
    # reset list for target / prediction histograms every epoch
    epoch_targets_train = torch.tensor([])
    epoch_targets_test = torch.tensor([])
    epoch_pred_test = torch.tensor([])

    #TRAIN
    model.train()
    for inputs, targets in train_loader: ## stuff needs to be done here to be able to fit two labels
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

    #epoch_loss_train.append(loss.item())
    writer.add_scalar('Loss/Train', loss.item(), epoch)

    #TEST
    model.eval()
    with torch.no_grad():
        for inputs, targets in test_loader:
            outputs = model(inputs)
            loss = criterion(outputs, targets)

            epoch_pred_test = torch.cat((epoch_pred_test, outputs), 0)
            epoch_targets_test = torch.cat((epoch_targets_test, targets), 0)

        #epoch_loss_test.append(loss.item())
        writer.add_scalar('Loss/Test', loss.item(), epoch)

    # Logs every 10 epochs
    if (epoch + 1) % 10 == 0:
        print(f'Epoch [{epoch + 1}/{num_epochs}], Loss: {loss.item():.4f}')

        # log a histogram of all targets/predictions
        writer.add_histogram('Targets/Test', epoch_targets_test, epoch)
        writer.add_histogram('Predictions/Test', epoch_pred_test, epoch)

# Save the trained model
save_path = f'Models/'
torch.save(model.state_dict(), save_path + f'3D_model_{ARM}.pth')
print("Model training completed and saved.")

"""landmarks, labels = next(iter(train_loader))
writer.add_graph(model, landmarks)

writer.add_hparams({"training files": str(csv_files),
                    "num samples": train_dataset.__len__(),
                    "epochs": num_epochs,
                    "batch size": batch_size,
                    "learning rate": learning_rate},
                   {"loss": loss.item()})
writer.flush()
writer.close()
"""
"""
Run this from terminal to start Tensorboard:

tensorboard --logdir=runs

Note: Safari won't open the page, you need chrome/firefox...!
"""