from src.config import *
from src.tools import *
from src.storage import *
from src.log_parser import *

def generate_whitelist(data_config):
    data_path = data_config['data_path']
    dataset = torch.load(f'{data_path}/train_data.pt')
    storage = Storage(data_config, test=False)
    storage.load(f'{data_path}')

    # P1: most windows
    file_window_hit = {}
    net_window_hit = {}
    token2gnid = defaultdict(set)
    history_window_hit_records = torch.tensor([[0]*len(storage.gnid2md5)]*len(dataset))
    for data, did in zip(dataset, range(len(dataset))):
        history_window_hit_records[did][data.gnid.cpu()]+=1
        c=0
        for nid in data.edge:
            gnid = data.gnid[nid].item()
            try:
                name = storage.entity_map[NODE_TYPE.PROCESS][storage.gnid2md5[gnid]]['name']
                c+=1
            except:
                print(gnid, c)
                print(data.edge[nid])
                break
            for ngh_nid in torch.tensor(list(data.edge[nid].keys())):
                ngh_gnid = data.gnid[ngh_nid].item()
                nt,ngh_name = storage.get_entity_name(ngh_gnid)
                if nt==NODE_TYPE.FILE:
                    if ngh_gnid not in file_window_hit:
                        file_window_hit[ngh_gnid]=set()
                    file_window_hit[ngh_gnid].add(gnid)
                if nt==NODE_TYPE.NET:
                    if ngh_gnid not in net_window_hit:
                        net_window_hit[ngh_gnid]=set()
                    net_window_hit[ngh_gnid].add(gnid)

    for md5 in storage.entity_map[NODE_TYPE.FILE]:
        node = storage.entity_map[NODE_TYPE.FILE][md5]
        name = node['name']
        gnid = node['id']
        token = storage.tokenization(name)
        if token is not None:
            token2gnid[token].add(gnid)

    for token in token2gnid:
        common_elements = list(token2gnid[token])
        for idx in range(1, len(common_elements)):
            history_window_hit_records[:, common_elements[0]] |= history_window_hit_records[:, common_elements[idx]]
            file_window_hit[common_elements[0]] |= file_window_hit[common_elements[idx]]
            
    file_whitelist = set()
    net_whitelist = set()

    history_window_hit_number = torch.sum(history_window_hit_records, dim=0)
    common_elements = torch.where(history_window_hit_number>(len(dataset)*0.5))[0]
    for gnid in common_elements:
        nt, name = storage.get_entity_name(gnid)
        if nt==NODE_TYPE.FILE:
            token = storage.tokenization(name)
            if token is not None:
                if gnid == list(token2gnid[token])[0]:
                    name = token
                else:
                    continue
            file_whitelist.add(name)
        if nt==NODE_TYPE.NET:
            net_whitelist.add(name)

    token_hit = torch.tensor([len(token2gnid[token]) for token in token2gnid])
    for i in torch.where(token_hit>5)[0].tolist():
        key =list(token2gnid.keys())[i]
        file_whitelist.add(key)

    # P2: most processes access
    alpha=0.0001
    totall_process_number=len(storage.entity_map[NODE_TYPE.PROCESS])
    index = torch.where(torch.tensor([len(file_window_hit[gnid]) for gnid in file_window_hit])>totall_process_number*alpha)[0]

    for i in index:
        nt, name = storage.get_entity_name(list(file_window_hit.keys())[i])
        if nt==NODE_TYPE.FILE:
            token = storage.tokenization(name)
            if token is not None:
                if gnid == list(token2gnid[token])[0]:
                    name = token
                else:
                    continue
            if name not in file_whitelist:
                file_whitelist.add(name)
        
    # some other common dir paths and local netflow
    file_whitelist.add('/.')
    file_whitelist.add('/var/log/')
    file_whitelist.add('/tmp/.')
    file_whitelist.add('/root/Desktop')
    file_whitelist.add('/root')
    net_whitelist.add('127.0.0.1')

    torch.save(file_whitelist, f"{data_config['data_path']}/file_whitelist.pt")
    torch.save(net_whitelist, f"{data_config['data_path']}/net_whitelist.pt")


def generate_train_data(data_config, time_type=int, time_key='MSec'):
    interval = data_config['interval']
    data_path = data_config['data_path']
    EVENT_TYPE = EVENT_TYPE_CONFIG(data_config['event_config_path'])

    dataset = []
    time_window_index = 0
    storage = Storage(data_config, test=False)

    for stream_file in data_config["train_data"]:
        print('Processing', stream_file)
        assert(os.path.exists(stream_file))
        eventf = open(stream_file, 'r')
        log_line = eventf.readline()
        org_log = get_orgs(log_line)
        eventf.close()

        time_window_start = time_type(org_log[time_key])
        time_window_end = time_window_start + interval
        
        for log_line in open(stream_file):
            org_log = get_orgs(log_line)
            timestamp = time_type(org_log[time_key])
            
            if timestamp > time_window_end:
                data = storage.generate_time_window_graph()
                print(f"Time Window {time_window_index} finished! {torch.sum(data.node_type==NODE_TYPE.PROCESS).item()} processes! {torch.sum(data.node_type==NODE_TYPE.FILE).item()} files! {torch.sum(data.node_type==NODE_TYPE.NET).item()} nets!") 
                dataset.append(copy.deepcopy(data))
                storage.clear_time_window()
                time_window_index+=1
                time_window_start = time_window_end
                time_window_end = time_window_start + interval
            add_event_darpa(storage, org_log, EVENT_TYPE)
            
        data = storage.generate_time_window_graph()
        print(f"Time Window {time_window_index} finished! {torch.sum(data.node_type==NODE_TYPE.PROCESS).item()} processes! {torch.sum(data.node_type==NODE_TYPE.FILE).item()} files! {torch.sum(data.node_type==NODE_TYPE.NET).item()} nets!") 
        dataset.append(copy.deepcopy(data))
        storage.clear_time_window()
        time_window_index+=1

    torch.save(dataset, f'{data_path}/train_data.pt')
    storage.save(f'{data_path}/')
    return dataset


def main(data_name):
    data_config = json.load(open('config/data.json', 'r'))[data_name]
    generate_train_data(data_config)
    generate_whitelist(data_config)

    
if __name__ == "__main__":
    main(sys.argv[1])