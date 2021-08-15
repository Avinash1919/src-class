from typing import Optional
import torch
import torch.nn  as nn
from torch.nn.modules.sparse import Embedding
from torch.utils.data import Dataset,DataLoader
import torch.optim as optim
from pathlib import Path
import os

DATASETDIR="data_language_clean"
BATCH_SIZE=128
CLASS_NUM=0
FILE_NUM=0  # 0 means unlimited, otherwise limit to the specifical number.
DTYPE=torch.FloatTensor
VOCAB=set()
EPOCH_NUM=100
MAX_TOKEN=200


def strip_chinese(strs):
    for _char in strs:
        if '\u4e00' <= _char <= '\u9fa5':
            return ""
    return strs

class BuildSrcData(Dataset):
   
    def __init__(self,DataDir,VOCAB):
        self.allcat={}
        self.x_data=[]
        self.y_data=[]
        for id,dir in enumerate(Path(DataDir).iterdir()):
            self.allcat[str(dir).split(os.sep)[-1]]=id
        
        for dir in self.allcat:
            for file in (Path(DataDir)/dir).iterdir():
                with open(file,"r",encoding="utf-8") as f:
                    lines= f.readlines()
                    lines=list(map(lambda x:x.replace("\n",""),lines))
                    lines=list(map(strip_chinese,lines))
                    VOCAB.update(lines)
                    nLines=len(lines)
                    if  nLines <MAX_TOKEN :
                        lines.extend([""]*(MAX_TOKEN-nLines))
                    else:
                        lines=lines[:MAX_TOKEN]

                    self.x_data.append(lines)
                    label=self.allcat[dir]
                    self.y_data.append(label)
                    
        
        


    def __len__(self):
        return len(self.y_data)

    def __getitem__(self, index):
        return self.x_data[index],self.y_data[index]

    def getnumclass(self):
        return len(self.allcat)
        


#https://wmathor.com/index.php/archives/1445/
class TextCNN(nn.Module):
    def __init__(self,vocab_size,embedding_size,num_classes):
        super(TextCNN,self).__init__()
        self.W = nn.Embedding(vocab_size,embedding_size,padding_idx=0)
        output_channel =3
        self.conv = nn.Sequential(
            nn.Conv2d(1,output_channel,(2,embedding_size)),
            nn.ReLU(),
            nn.MaxPool2d((2,1)),
        )

        self.fc=nn.Linear(output_channel,num_classes)
    
    def forward(self,X):
        batch_size=X.shape[0]
        embedding_X=self.W(X) # [batch_size, sequence_length, embedding_size]
        embedding_X=embedding_X.unsequeenze(1)  # add channel(=1) [batch, channel(=1), sequence_length, embedding_size]
        conved = self.conv(embedding_X)  # [batch_size, output_channel*1*1]
        flatten = conved.view(batch_size,-1)
        output=self.fc(flatten)
        return output


def do_train(ds_src,WORDLIST):
    VOCAB_SIZE=len(WORDLIST) # 
    CLASS_NUM =  ds_src.getnumclass()
    device = torch.device("cuda" if torch.cuda.is_available() else 'cpu')
    model = TextCNN(VOCAB_SIZE,128,CLASS_NUM).to(device)
    criterion = nn.CrossEntropyLoss().to(device)
    optimizer =optim.Adam(model.parameters(),lr=1e-3)
    loader=DataLoader(dataset=ds_src,batch_size=BATCH_SIZE,shuffle=True,num_workers=0)
    for epoch in range(EPOCH_NUM):
        new_batch_x=[]
        for batch_x,batch_y in loader:
            line=[]
            for item in batch_x:
                line=[ WORDLIST[key] for key in item]
            new_batch_x.append(line)
                   
            batch_x,batch_y = torch.tensor(new_batch_x).to(device), torch.tensor(batch_y).to(device)
            pred=model(batch_x)
            loss = criterion(pred,batch_y)
            if (epoch + 1) % 1000 == 0:
                print('Epoch:', '%04d' % (epoch + 1), 'loss =', '{:.6f}'.format(loss))

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()





if __name__ == "__main__":
    ds_src=BuildSrcData(DATASETDIR,VOCAB)
  
    WORDLIST={key:i for i,key in enumerate(VOCAB)}
    
    do_train(ds_src,WORDLIST)