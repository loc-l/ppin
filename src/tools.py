from hashlib import md5
import string, json, re, os, random, copy, math, sys
import torch
import numpy as np
from graphviz import Digraph
from collections import defaultdict
import numpy as np
import scipy.sparse as sp
from torch_geometric.utils import to_scipy_sparse_matrix
from .config import *

from datetime import datetime
import time
import pytz
from time import mktime
from datetime import datetime
import time

from config import *


def ns_time_to_datetime(ns):
    """
    :param ns: int nano timestamp
    :return: datetime   format: 2013-10-10 23:40:00.000000000
    """
    dt = datetime.fromtimestamp(int(ns) // 1000000000)
    s = dt.strftime('%Y-%m-%d %H:%M:%S')
    s += '.' + str(int(int(ns) % 1000000000)).zfill(9)
    return s

def ns_time_to_datetime_US(ns):
    """
    :param ns: int nano timestamp
    :return: datetime   format: 2013-10-10 23:40:00.000000000
    """
    tz = pytz.timezone('US/Eastern')
    dt = pytz.datetime.datetime.fromtimestamp(int(ns) // 1000000000, tz)
    s = dt.strftime('%Y-%m-%d %H:%M:%S')
    s += '.' + str(int(int(ns) % 1000000000)).zfill(9)
    return s

def time_to_datetime_US(s):
    """
    :param ns: int nano timestamp
    :return: datetime   format: 2013-10-10 23:40:00
    """
    tz = pytz.timezone('US/Eastern')
    dt = pytz.datetime.datetime.fromtimestamp(int(s), tz)
    s = dt.strftime('%Y-%m-%d %H:%M:%S')

    return s

def datetime_to_ns_time(date):
    """
    :param date: str   format: %Y-%m-%d %H:%M:%S   e.g. 2013-10-10 23:40:00
    :return: nano timestamp
    """
    timeArray = time.strptime(date, "%Y-%m-%d %H:%M:%S")
    timeStamp = int(time.mktime(timeArray))
    timeStamp = timeStamp * 1000000000
    return timeStamp

def datetime_to_ns_time_US(date):
    """
    :param date: str   format: %Y-%m-%d %H:%M:%S   e.g. 2013-10-10 23:40:00
    :return: nano timestamp
    """
    tz = pytz.timezone('US/Eastern')
    timeArray = time.strptime(date, "%Y-%m-%d %H:%M:%S")
    dt = datetime.fromtimestamp(mktime(timeArray))
    timestamp = tz.localize(dt)
    timestamp = timestamp.timestamp()
    timeStamp = timestamp * 1000000000
    return int(timeStamp)

def datetime_to_timestamp_US(date):
    """
    :param date: str   format: %Y-%m-%d %H:%M:%S   e.g. 2013-10-10 23:40:00
    :return: nano timestamp
    """
    tz = pytz.timezone('US/Eastern')
    timeArray = time.strptime(date, "%Y-%m-%d %H:%M:%S")
    dt = datetime.fromtimestamp(mktime(timeArray))
    timestamp = tz.localize(dt)
    timestamp = timestamp.timestamp()
    timeStamp = timestamp
    return int(timeStamp)

def get_md5(s):
    """
    get md5 hash value of String s
    :param s:
    :return:
    """
    return str(md5(s.encode('utf8')).hexdigest())

def get_orgs(line):
    org_logs = json.loads(line)
    return org_logs   

def print_metrics(tn, tp, fn, fp, metric):
    metric_values = {
        'tn' : tn,
        'tp' : tp,
        'fn' : fn,
        'fp' : fp,
        'tpr' : tp/(tp+fn),
        'fpr' : fp/(fp+tn),
        'tnr' : tn/(fp+tn),
        'fnr' : fn/(tp+fn),
        'acc' : (tp+tn)/(tn+tp+fn+fp),
        'precision' : tp/(tp+fp),
        'recall' : tp/(tp+fn)
        }

    for m in metric:
        if m in ['tn','tp','fn','fp',]:
            print(f'{m}: {metric_values[m]}')
        else:
            print(f'{m}: {metric_values[m]:.4f}')
            
def load_label(data_name):
    attack_scene = {}
    with open(f'./label/{data_name}.txt', 'r') as f:
        while(1):
            line = f.readline()
            if not line:
                break

            if line[:6]=='ATTACK':
                t = line[6:].strip().split('/')
                # print(f'2018-{t[0]}-{t[1]}')
                attack_map = {NODE_TYPE.PROCESS:set(), NODE_TYPE.NET:set(), NODE_TYPE.FILE:set(),
                                'DAY':t[1]}
                
                while(1):
                    line = f.readline()
                    if line=='\n':
                        break
                    attack_map[NODE_TYPE.NET].add(line.strip())
                        
                while(1):
                    line = f.readline()
                    if line=='\n':
                        break
                    attack_map[NODE_TYPE.FILE].add(line.strip())

                while(1):
                    line = f.readline()
                    if line=='\n' or not line:
                        break
                    proc = line.strip()
                    attack_map[NODE_TYPE.PROCESS].add(proc)
                attack_scene[int(t[1])]=attack_map

    return attack_scene

def get_token_list(name):
    token_list = []
    for line in open(f'token/{name}.txt'):
        token_list.append(line.strip()) 
    return token_list
  
def setup_seed(seed):
     torch.manual_seed(seed)
     torch.cuda.manual_seed_all(seed)
     np.random.seed(seed)
     random.seed(seed)

