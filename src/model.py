import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F

class MemLayer(nn.Module):
    def __init__(self, args, device, prior_centroids=None):
        super(MemLayer, self).__init__()
        self.args = args
        self.total_centroids = self.args.num_centroids
        self.device = device
        
        if prior_centroids is None:
            self.centroids = \
                nn.Parameter(2 * torch.rand(
                    self.args.cluster_heads,
                    self.total_centroids * (self.args.hidden_dim)) - 1)
        else:
            self.centroids = nn.Parameter(prior_centroids)
        self.centroids.requires_grad = True

        self.wm1 = nn.Linear(args.input_dim, args.hidden_dim)
        self.wm2 = nn.Linear(args.hidden_dim, args.hidden_dim)
        self.leakyrelu = nn.LeakyReLU(0.2)
        self.wm21 = nn.Linear(args.hidden_dim, args.hidden_dim)
        
        self.headConv = nn.Parameter(torch.zeros(size=(self.args.cluster_heads, 1)))
        nn.init.xavier_uniform_(self.headConv.data, gain=1.414)

        self.hard_loss = torch.Tensor([0])

    def forward(self, x_node, adj, epoch):
        x_node = self.leakyrelu(F.dropout(self.wm1(x_node), p=self.args.dropout, training=self.training))
        x_node = self.leakyrelu(F.dropout(self.wm2(x_node), p=self.args.dropout, training=self.training))
        h_prime = torch.squeeze(x_node)
        
        new_feat = self.cluster_block(h_prime, adj)
        new_feat = self.leakyrelu(F.dropout(self.wm21(new_feat), p=self.args.dropout, training=self.training))

        self.centroids.requires_grad = False
        if (epoch + 1) % self.args.backward_period:
            self.centroids.requires_grad = True
        
        return h_prime, new_feat
    
    def cluster_block(self, x, adj):
        """ This function calculates the assignment matrix for keys (batch_centroids) and queries (points) """
        node_num = x.shape[0]
        cumsum = np.cumsum(self.args.num_centroids)
        cumsum = np.insert(cumsum, 0, 0)
        # [nheads, ncenters, nfeat]
        batch_centroids = self.centroids
        batch_centroids = batch_centroids.view(self.args.cluster_heads, -1, self.args.hidden_dim)
        # [nheads, ncenters, node_num, nfeat]
        batch_centroids = torch.unsqueeze(batch_centroids, 2).repeat(1, 1, node_num, 1)
        # batch_centroids = batch_centroids.to(self.device)
        
        # size: [nheads, node_num, nfeat]
        points = torch.unsqueeze(x, 0).repeat(batch_centroids.shape[0], 1, 1)
        # size: [nHeads, ncenters, node_num, nfeat]
        points = torch.unsqueeze(points, 1).repeat(1, batch_centroids.shape[1], 1, 1)

        dist = torch.sum(torch.abs(points - batch_centroids) ** 2, 3)
        nu = 1  # this is a hyperparameter, same as the one in the taxonomy paper
        q = torch.pow((1 + dist / nu), -(nu + 1) / 2)
        
        #TODO: use adj to reform
        new_feat = torch.zeros([len(adj), q.shape[1], x.shape[1]]).to(self.device)
        for i in range(len(adj)):
            edge_list = adj[i]
            tmpq = q[:, :, edge_list]
            denominator = torch.unsqueeze(torch.sum(tmpq, 2), 2)
            tmpq = tmpq / denominator
            tmpq = tmpq.permute(2, 1, 0)
            tmpq = torch.matmul(tmpq, self.headConv)
            
            tmpq = torch.squeeze(tmpq.permute(2, 1, 0), 0)
            tmpq = torch.softmax(tmpq, 1) 
            # hidden label
            _, hidden = torch.max(tmpq, 0)

            new_feat[i] = torch.matmul(tmpq, x[edge_list])

            # Hard loss after convolution
            p = torch.pow(tmpq, 2) / torch.unsqueeze(torch.sum(tmpq, 1), 1)
            denominator = torch.sum(p, 1)
            denominator = torch.unsqueeze(denominator, 1)
            p = p / denominator

            hard_loss2 = p * torch.log(p / tmpq)
            self.hard_loss = 100 * torch.sum(hard_loss2)

        return new_feat


class Decoder(nn.Module):
    def __init__(self, args):
        super(Decoder, self).__init__()
        self.decoder_layer1 = nn.Linear(args.hidden_dim, args.hidden_dim)
        self.decoder_layer2 = nn.Linear(args.hidden_dim, args.output_dim)
        self.leakyrelu = nn.LeakyReLU(0.2)
        self.args = args

    def forward(self, x):
        h_prime = self.leakyrelu(F.dropout(self.decoder_layer1(torch.mean(x, 1)), p=self.args.dropout, training=self.training))
        h_prime = F.dropout(self.decoder_layer2(h_prime), p=self.args.dropout, training=self.training)
        return h_prime

# MemAN
class MemAPT(nn.Module):
    def __init__(self, args, device, prior_centroids=None):
        super(MemAPT, self).__init__()
        self.memlayer = MemLayer(args, device, prior_centroids)
        self.decoder = Decoder(args)

    def forward(self, x_node, adj, epoch):
        h, z = self.memlayer(x_node, adj, epoch)
        return h, self.decoder(z)