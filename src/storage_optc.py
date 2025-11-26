# this is for optc
from .tools import *
from .smirnov_grubbs import max_test_indices

from sklearn.feature_extraction import FeatureHasher
from torch_geometric.data import TemporalData


class Pattern:
    def __init__(self):
        self.net_element_set = {} # ip element
        self.file_element_set = {} # file element
        self.file_hit_table = {} # file entity hit table
        self.hit = 1 # pattern hit times
        self.subject = {}  # subject candidate cache
        self.hit_window_set = set() # hit time window set
        self.PS = 0. # pattern-level rareness score


class Storage:
    def __init__(self, data_config, test=True):
        self.EVENT_TYPE = EVENT_TYPE_CONFIG(data_config['event_config_path'])
        self.data_config = data_config
        # md5 -> name, gnid
        self.entity_map = {NODE_TYPE.PROCESS:{}, NODE_TYPE.FILE:{}, NODE_TYPE.NET:{}}
        self.GNID = 0
        self.infeat = data_config['infeat']

        # gnid -> feat
        self.gnid2md5 = []
        self.FH_string = FeatureHasher(n_features=self.infeat, input_type="string")
        self.default_process_feat = self.FH_string.transform(['process']).toarray().reshape([-1])

        # time window storage
        # GNID -> NID
        self.temporal_time_window_entity_map = {NODE_TYPE.PROCESS:{}, NODE_TYPE.FILE:{}, NODE_TYPE.NET:{}}
        self.NID = 0
        
        self.temporal_time_window_node_feat = []
        self.temporal_time_window_node_gnid = []
        self.temporal_time_window_node_type = []
        self.temporal_time_window_train_process = []
        self.temporal_time_window_edge = {}
        self.time_window_index = -1

        # tokenization config
        self.token_list = get_token_list(data_config['name'])
        self.token_pattern = []
        for expression in self.token_list:
            self.token_pattern.append(re.compile(expression))
            
        if test:
            # load whitelist
            self.file_whitelist = torch.load(f"{data_config['data_path']}/file_whitelist.pt")
            self.net_whitelist = torch.load(f"{data_config['data_path']}/net_whitelist.pt")
            # cache definition
            self.pattern_cache = [] # pattern candidate cache
            self.edge_cache = {} # pruned sample cache
            
            self.label = None


    def load(self, root):
        if os.path.exists(f'{root}/storage_entity_map.pt'):
            self.entity_map = torch.load(f'{root}/storage_entity_map.pt')
            self.gnid2md5 = torch.load(f'{root}/storage_gnid2md5_map.pt')
            return True
        else:
            print('Not find!')
            return False


    def save(self, root):
        if not os.path.exists(f'{root}/storage_entity_map.pt'):
            torch.save(self.entity_map, f'{root}/storage_entity_map.pt')
            torch.save(self.gnid2md5, f'{root}/storage_gnid2md5_map.pt')


    def add_process_node(self, pid, name):
        node_type = NODE_TYPE.PROCESS
        process_node_md5 = get_md5(str(pid) + str(name))
        if process_node_md5 not in self.entity_map[node_type]:
            self.entity_map[node_type][process_node_md5] = {'name': name, 'pid':pid, 'id': self.GNID}
            process_gnid = self.GNID
            self.gnid2md5.append(process_node_md5)
            self.GNID+=1
        else:
            process_gnid = self.entity_map[node_type][process_node_md5]['id'] 

        if process_gnid not in self.temporal_time_window_entity_map[node_type]:
            self.temporal_time_window_entity_map[node_type][process_gnid] = self.NID
            process_nid = self.NID
            self.NID+=1
            if name=='':
                self.temporal_time_window_node_feat.append(self.default_process_feat.copy())
            else:
                self.temporal_time_window_node_feat.append(self.FH_string.transform(['process/'+name]).toarray().reshape([-1]).astype(np.float32))
            self.temporal_time_window_node_gnid.append(process_gnid)
            self.temporal_time_window_node_type.append(NODE_TYPE.PROCESS)
            if name!='':
                self.temporal_time_window_train_process.append(process_nid)
        else:
            process_nid = self.temporal_time_window_entity_map[node_type][process_gnid]

        return process_nid
    
    
    def add_file_node(self, name):
        node_type = NODE_TYPE.FILE
        file_node_md5 = get_md5(name)
        if not (file_node_md5 in self.entity_map[node_type]):
            self.entity_map[node_type][file_node_md5] = {'name': name, 'id': self.GNID}
            file_gnid = self.GNID
            self.gnid2md5.append(file_node_md5)
            self.GNID+=1
        else:
            file_gnid = self.entity_map[node_type][file_node_md5]['id']
        
        if file_gnid not in self.temporal_time_window_entity_map[node_type]:
            self.temporal_time_window_entity_map[node_type][file_gnid] = self.NID
            file_nid = self.NID
            self.NID+=1
            
            file_feat = self.FH_string.transform(['file/'+name]).toarray().reshape([-1]).astype(np.float32)
            self.temporal_time_window_node_feat.append(file_feat)
            self.temporal_time_window_node_gnid.append(file_gnid)
            self.temporal_time_window_node_type.append(NODE_TYPE.FILE)
        else:
            file_nid = self.temporal_time_window_entity_map[node_type][file_gnid]
        
        return file_nid
    

    def add_net_node(self, name):
        node_type = NODE_TYPE.NET
        net_node_md5 = get_md5(name) 
        if not (net_node_md5 in self.entity_map[node_type]):
            self.entity_map[node_type][net_node_md5] = {'name': name, 'id': self.GNID}
            net_gnid = self.GNID
            self.gnid2md5.append(net_node_md5)
            self.GNID+=1
        else:
            net_gnid = self.entity_map[node_type][net_node_md5]['id'] 

        if net_gnid not in self.temporal_time_window_entity_map[node_type]:
            self.temporal_time_window_entity_map[node_type][net_gnid] = self.NID
            net_nid = self.NID
            self.NID+=1
            net_feat  = self.FH_string.transform(['net/'+name]).toarray().reshape([-1]).astype(np.float32)
            self.temporal_time_window_node_feat.append(net_feat)
            self.temporal_time_window_node_gnid.append(net_gnid)
            self.temporal_time_window_node_type.append(NODE_TYPE.NET)
        else:
            net_nid = self.temporal_time_window_entity_map[node_type][net_gnid]
        return net_nid
    
    
    def clear_time_window(self):
        self.NID = 0
        self.temporal_time_window_entity_map.clear()
        self.temporal_time_window_entity_map = {NODE_TYPE.PROCESS:{}, NODE_TYPE.FILE:{}, NODE_TYPE.NET:{}}
        self.temporal_time_window_edge.clear()
        self.temporal_time_window_node_feat.clear()
        self.temporal_time_window_node_type.clear()
        self.temporal_time_window_train_process.clear()
        self.temporal_time_window_node_gnid.clear()

    
    def generate_time_window_graph(self):
        data = TemporalData()
        data.edge = self.temporal_time_window_edge
        data.x = torch.tensor(np.array(self.temporal_time_window_node_feat))
        data.node_type = torch.tensor(self.temporal_time_window_node_type)
        data.gnid = torch.tensor(self.temporal_time_window_node_gnid)

        return data
    

    def get_entity(self, nid, data):
        return data.node_type[nid], self.entity_map[data.node_type[nid].item()][self.gnid2md5[data.gnid[nid]]]
    

    def get_entity(self, gnid):
        md5 = self.gnid2md5[gnid]
        for nt in [NODE_TYPE.FILE, NODE_TYPE.NET, NODE_TYPE.PROCESS]:
            try:
                node = self.entity_map[nt][md5]
                return nt, node
            except:
                pass


    def get_entity_name(self, gnid):
        md5 = self.gnid2md5[gnid]
        for nt in [NODE_TYPE.FILE, NODE_TYPE.NET, NODE_TYPE.PROCESS]:
            try:
                node = self.entity_map[nt][md5]
                if nt==NODE_TYPE.PROCESS:
                    return nt, node['pid']
                return nt, node['name']
            except:
                pass


    def tokenization(self, name):
        for i in range(len(self.token_pattern)):
            p = self.token_pattern[i]
            if len(p.findall(name))>0:
                return self.token_list[i]
        return None


    def get_anomaly_edges(self):
        srcs = []
        dsts = []
        ets = []

        for src in self.anomalous_table:
            for nt in [NODE_TYPE.FILE, NODE_TYPE.NET, NODE_TYPE.PROCESS]:
                for dst in self.edge_cache[src][nt]:
                    if nt==NODE_TYPE.PROCESS:
                        if dst not in self.anomalous_table: 
                            continue
                    for et in self.edge_cache[src][nt][dst]:
                        if et in self.EVENT_TYPE.REVERSE_EVENT:
                            srcs.append(dst)
                            dsts.append(src)
                            ets.append(et)
                        if et in self.EVENT_TYPE.DIRECTED_EVENT:
                            srcs.append(src)
                            dsts.append(dst)
                            ets.append(et)
        return srcs, dsts, ets


    def local_pattern_extraction(self, data, model, criterion, device):
        self.time_window_index+=1
        # compute anomaly score RE
        nghs = [list(data.edge[nid].keys()) for nid in data.edge]
        subject_index = list(data.edge.keys())
        x = data.x.float().to(device)
        h, y = model(x, [torch.tensor(ngh_).to(device) for ngh_ in nghs], 0)
        
        loss = criterion(h[subject_index], y)
        anomaly_score = torch.sum(loss, dim=1).cpu()

        _, index4as = anomaly_score.sort(descending=True)
        
        for i in index4as:
            nid = subject_index[i]
            gnid = data.gnid[nid].item()
            
            tmp_pattern, tmpadj, childs = self.extract_pattern(data, nid)
            if len(tmp_pattern.file_hit_table)==0 and len(tmp_pattern.net_element_set)==0 and len(childs)==0: # filter null pattern
                continue

            # update edge cache
            if gnid not in self.edge_cache:
                self.edge_cache[gnid] = {NODE_TYPE.FILE:{}, NODE_TYPE.NET:{}, NODE_TYPE.PROCESS:{}}
            for nodes, nt in zip([tmp_pattern.file_hit_table, tmp_pattern.net_element_set, childs], [NODE_TYPE.FILE, NODE_TYPE.NET, NODE_TYPE.PROCESS]): 
                for ngh_gnid in nodes:
                    if len(self.edge_cache[gnid][nt])>15:
                        break
                    if ngh_gnid not in self.edge_cache[gnid][nt]:
                        self.edge_cache[gnid][nt][ngh_gnid] = set()
                    self.edge_cache[gnid][nt][ngh_gnid] |= tmpadj[ngh_gnid] # Edges types

            # merge similar patterns & update cache
            hit = False
            for pattern, pattern_id in zip(self.pattern_cache, range(len(self.pattern_cache))):
                if (len(tmp_pattern.net_element_set)>0 and len(pattern.net_element_set)>0) or (len(tmp_pattern.file_hit_table)>0 and len(pattern.file_hit_table)>0):
                    n_overlap = set(list(tmp_pattern.net_element_set.keys())) & set(list(pattern.net_element_set.keys()))
                    f_overlap = set(list(tmp_pattern.file_element_set.keys())) & set(list(pattern.file_element_set.keys()))
                    if len(n_overlap)==len(tmp_pattern.net_element_set) and len(f_overlap)==len(tmp_pattern.file_element_set): #sub pattern
                        hit = True
                        self.pattern_cache[pattern_id].hit += 1
                        if gnid in self.pattern_cache[pattern_id].subject:
                            self.pattern_cache[pattern_id].subject[gnid] = max(self.pattern_cache[pattern_id].subject[gnid], anomaly_score[i].item())
                        else:
                            self.pattern_cache[pattern_id].subject[gnid] = anomaly_score[i].item()
                        self.pattern_cache[pattern_id].hit_window_set.add(self.time_window_index)

                        for node in tmp_pattern.net_element_set:
                            self.pattern_cache[pattern_id].net_element_set[node]+=1
                    
                        for node in tmp_pattern.file_hit_table:
                            if node in self.pattern_cache[pattern_id].file_hit_table:
                                self.pattern_cache[pattern_id].file_hit_table[node]+=1
                            else:
                                self.pattern_cache[pattern_id].file_hit_table[node]=1

                        for token in tmp_pattern.file_element_set:
                            if token not in self.pattern_cache[pattern_id].file_element_set:
                                self.pattern_cache[pattern_id].file_element_set[token] = tmp_pattern.file_element_set[token]
                            else:
                                self.pattern_cache[pattern_id].file_element_set[token] |= tmp_pattern.file_element_set[token]

                        break
                    
                    if len(n_overlap | f_overlap)/(len(tmp_pattern.net_element_set)+len(tmp_pattern.file_element_set))>=0.8 or len(n_overlap | f_overlap)/(len(pattern.net_element_set)+len(pattern.file_element_set))>=0.8:
                        hit = True
                        for node in tmp_pattern.net_element_set:
                            if node in self.pattern_cache[pattern_id].net_element_set:
                                self.pattern_cache[pattern_id].net_element_set[node]+=1
                            else:
                                self.pattern_cache[pattern_id].net_element_set[node]=1

                        for node in tmp_pattern.file_hit_table:
                            if node in self.pattern_cache[pattern_id].file_hit_table:
                                self.pattern_cache[pattern_id].file_hit_table[node]+=1
                            else:
                                self.pattern_cache[pattern_id].file_hit_table[node]=1
                        
                        for token in tmp_pattern.file_element_set:
                            if token not in self.pattern_cache[pattern_id].file_element_set:
                                self.pattern_cache[pattern_id].file_element_set[token] = tmp_pattern.file_element_set[token]
                            else:
                                self.pattern_cache[pattern_id].file_element_set[token] |= tmp_pattern.file_element_set[token]

                        self.pattern_cache[pattern_id].hit += 1
                        if gnid in self.pattern_cache[pattern_id].subject:
                            self.pattern_cache[pattern_id].subject[gnid] = max(self.pattern_cache[pattern_id].subject[gnid], anomaly_score[i].item())
                        else:
                            self.pattern_cache[pattern_id].subject[gnid] = anomaly_score[i].item()
                        self.pattern_cache[pattern_id].hit_window_set.add(self.time_window_index)
                        break
            
            if not hit and (len(tmp_pattern.file_hit_table)>0 or len(tmp_pattern.net_element_set)>0):
                tmp_pattern.subject[gnid] = anomaly_score[i].item()
                tmp_pattern.hit_window_set.add(self.time_window_index)
                self.pattern_cache.append(tmp_pattern)


    def extract_pattern(self, data, nid):
        pattern = Pattern()
        nghs = {}
        childs = {}
        for ngh in data.edge[nid]:
            ets = data.edge[nid][ngh]
            gnid = data.gnid[ngh].item()
            nt, ngh_name = self.get_entity_name(data.gnid[ngh])
            if nt==NODE_TYPE.PROCESS:
                childs[gnid]=1
            elif nt==NODE_TYPE.NET:
                if ngh_name not in self.net_whitelist:
                    pattern.net_element_set[gnid]=1
            elif nt==NODE_TYPE.FILE:
                newname = self.tokenization(ngh_name)
                if newname is None:
                    if ngh_name not in self.file_whitelist:
                        pattern.file_hit_table[gnid]=1
                        pattern.file_element_set[ngh_name]=set([gnid])
                else:#token
                    if newname not in self.file_whitelist:
                        pattern.file_hit_table[gnid]=1
                        if newname not in pattern.file_element_set:
                            pattern.file_element_set[newname] = set()
                        pattern.file_element_set[newname].add(gnid)

            nghs[gnid] = ets
        
        return pattern, nghs, childs
        

    def pattern_rareness(self, beta):
        total_time_window_number = self.time_window_index
        candidate_table = {}
        all_pattern_count = 0
        max_pattern_count = 0
        for pattern, pattern_id in zip(self.pattern_cache, range(len(self.pattern_cache))):
            all_pattern_count+=pattern.hit
            if pattern.hit > max_pattern_count:
                max_pattern_count = pattern.hit

        for pattern, pattern_id in zip(self.pattern_cache, range(len(self.pattern_cache))):
            # Pattern-level rareness (PS) 
            self.pattern_cache[pattern_id].PS = min(math.log((total_time_window_number+1)/len(pattern.hit_window_set)), math.log((max_pattern_count+1)/pattern.hit))
            # Instance-level rareness (IS)
            for gnid in pattern.subject:
                gnid_score = []
                for dt in self.edge_cache[gnid]:
                    if dt==NODE_TYPE.NET:
                        for dst in self.edge_cache[gnid][dt]:
                            if dst in pattern.net_element_set:
                                gnid_score.append((pattern.hit+1)/pattern.net_element_set[dst])
                    
                    if dt==NODE_TYPE.FILE:
                        for dt in self.edge_cache[gnid][dt]:
                            for key in pattern.file_element_set:
                                if dt in pattern.file_element_set[key]:
                                    element_hit = 0
                                    for token2gnid in pattern.file_element_set[key]:
                                        element_hit+=pattern.file_hit_table[token2gnid]
                                    gnid_score.append((pattern.hit+1)/element_hit)
                                    break
                IS = torch.mean(torch.tensor(gnid_score)).item()
                if gnid not in candidate_table:
                    candidate_table[gnid] = {} # (gnid,pattern) pair
                if len(gnid_score)==0:
                    continue
                # AS_{p\perp \kappa}=PS_{\kappa}*RE_{p}^2*IS_{p\perp \kappa}
                # score for `process hit pattern
                candidate_table[gnid][pattern_id] = self.pattern_cache[pattern_id].PS * (pattern.subject[gnid]) * (pattern.subject[gnid]) * IS

        # AS_{p}
        AS_p = {}
        for p in candidate_table:
            AS_p[p] = torch.mean(torch.tensor(list(candidate_table[p].values())))
        anomalous_processes = torch.tensor(list(candidate_table.keys()))[torch.topk(torch.tensor(list(AS_p.values())),math.ceil(len(candidate_table)*beta))[1]].tolist()
        self.anomalous_table = {}
        for p in anomalous_processes:
            # (gnid,pattern) pair
            self.anomalous_table[p] = candidate_table[p] 


    def cross_pattern_detection(self, beta):
        self.pattern_rareness(beta)

        # this part realizes the dual of the original paper
        # and generates pattern combinations with AS_c
        srcs, dsts, ets = self.get_anomaly_edges()
        edges = torch.tensor([srcs, dsts])
        sc_graph = to_scipy_sparse_matrix(edges)
        _, component_ids = sp.csgraph.connected_components(
                    sc_graph, connection='weak')
        _, count = np.unique(component_ids, return_counts=True) # node number of each connected components
        cs = torch.where(torch.tensor(count)>1)[0].tolist() # remove isolate nodes

        # pattern combination score AS_{c}
        AS_c = []
        for idx in range(len(cs)):
            graph_score = []
            patterns = {}
            for i in np.argwhere(component_ids==cs[idx]): # combination idx
                gnid = i[0]
                if gnid in self.anomalous_table:
                    for pi in self.anomalous_table[gnid]:
                        if pi in patterns:
                            score = self.anomalous_table[gnid][pi]
                        else:
                            score = self.anomalous_table[gnid][pi]
                            patterns[pi] = score
                            graph_score.append(score)
            AS_c.append(torch.mean(torch.tensor(graph_score)))
        if len(AS_c)<3: return

        # outlier detection
        gids = max_test_indices(AS_c, alpha=1e-1)
        self.gids = gids
        self.cs = cs
        self.srcs = srcs
        self.dsts = dsts
        self.ets = ets
        self.component = component_ids
        

    def alert_generation(self, root='./', time_window_index=None):
        try:
            graphs = {}
            for i in self.gids:
                cid = self.cs[i]
                graphs[cid] = Digraph(name=f"{cid}", format='pdf')
                graphs[cid].graph_attr['rankdir'] = 'LR'
        except:
            return
        nodes = set()
        edges = set()

        if len(graphs)<1:
            return
        
        detected_proc = set()
        detected_net = set()
        detected_file = set()
        for src,dst,et in zip(self.srcs, self.dsts, self.ets):
            cid = self.component[src]
            if cid not in graphs:
                continue
            
            src_type, src_name = self.get_entity_name(src)
            dst_type, dst_name = self.get_entity_name(dst)

            if dst_type==NODE_TYPE.PROCESS:
                if dst not in self.anomalous_table: 
                    continue
            
            is_attack_event = 0.1
            for (nt, nn, nid) in zip([src_type, dst_type], [src_name, dst_name], [src, dst]):
                color = 'black'
                if nt==NODE_TYPE.PROCESS:
                    node_shape = 'box'
                    detected_proc.add(nn)
                    if self.label!=None:
                        if nn in self.label[NODE_TYPE.PROCESS]:
                            color='red'
                            is_attack_event+=0.5
                elif nt==NODE_TYPE.FILE:
                    node_shape = 'oval'
                    detected_file.add(nn)
                    if self.label != None:
                        if nn in self.label[NODE_TYPE.FILE]:
                            color='red'
                            is_attack_event+=0.5
                elif nt==NODE_TYPE.NET:
                    node_shape = 'diamond'
                    detected_net.add(nn)
                    if self.label != None:
                        if nn in self.label[NODE_TYPE.NET]:
                            color='red'
                            is_attack_event+=0.5
                if nid not in nodes:
                    nodes.add(nid)
                    graphs[cid].node(name=str(nid), color=color, label=nn, shape=node_shape)
            if f'{src}-{et}-{dst}' not in edges:
                ecolor='black'
                if int(is_attack_event):
                    ecolor='red'
                edges.add(f'{src}-{et}-{dst}')
                graphs[cid].edge(str(src), str(dst), label=self.EVENT_TYPE.get_name(et), color=ecolor)
        
        # render visualizatin for structural alerts where red denote attack nodes/edges (tp)
        os.system(f'mkdir -p {root}')
        for cid in graphs:
            graphs[cid].render(directory=f'{root}', )
        
        # entity-level alert in the form of `.txt`
        with open(f'{root}/log.txt', 'a') as wf:
            if time_window_index is not None:
                wf.write(f'\n{time_window_index}\n')
            for i in detected_proc:
                wf.write(f'{i},')
            wf.write('\n')
            for i in detected_file:
                wf.write(f'{i},')
            wf.write('\n')
            for i in detected_net:
                wf.write(f'{i},')
            wf.write('\n')


    def print_window_info(self, data):
        print(f"Time Window {self.time_window_index} finished! {torch.sum(data.node_type==NODE_TYPE.PROCESS).item()} processes! {torch.sum(data.node_type==NODE_TYPE.FILE).item()} files! {torch.sum(data.node_type==NODE_TYPE.NET).item()} nets!")        




