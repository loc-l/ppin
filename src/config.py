class EVENT_TYPE_CONFIG:
    rawname2typeid = {}
    typeid2name = {}
    REVERSE_EVENT = []
    DIRECTED_EVENT = []

    def __init__(self, path):
        with open(path, 'r') as f:
            et_id = 0
            while(1):
                line = f.readline()
                if line=='\n':
                    break
                line = line.strip()
                et_key, raw_name, print_name = line.split('\t')
                self.__setattr__(et_key, et_id, raw_name, print_name) 
                et_id+=1
            line = f.readline().strip()
            for et in line.split(','):
                et = et.rstrip().strip()
                self.REVERSE_EVENT.append(self.get_type(et))
            line = f.readline().strip()
            for et in line.split(','):
                et = et.rstrip().strip()
                self.DIRECTED_EVENT.append(self.get_type(et))

    def __setattr__(self, __name , __value, __value1, __value2) -> None:
        self.rawname2typeid[__value1] = __value
        self.typeid2name[__value] = __value2
        return super().__setattr__(__name, __value)
    
    def get_type(self, et):
        if et in self.rawname2typeid:
            return self.rawname2typeid[et]
    
    def get_name(self, et):
        if et in self.typeid2name:
            return self.typeid2name[et]
    

class ARGS:
    def __init__(self, input_dim=None):
        self.device = 1
        self.lr = 0.002
        self.dropout = 0.1
        self.weight_decay = 0.0
        self.input_dim = input_dim
        self.hidden_dim = 16
        self.output_dim = 16
        self.num_centroids = 10
        self.cluster_heads = 3
        self.backward_period = 5
    
    def print(self):
        for key, value in self.__dict__.items():
            print(key, value)


class NODE_TYPE:
    PROCESS = 0
    FILE = 1
    NET = 2  
