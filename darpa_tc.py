from src.config import *
from src.storage import *
from src.log_parser import *
from src.model import MemAPT

# data config
data_name = sys.argv[1]
data_config = json.load(open('config/data.json', 'r'))[data_name]
data_path = data_config['data_path']
interval = data_config['interval']
EVENT_TYPE = EVENT_TYPE_CONFIG(data_config['event_config_path'])
time_type = int
time_key = 'MSec'

# model config
args = ARGS(data_config['infeat'])
device = torch.device(int(sys.argv[2]))

model = MemAPT(args, device)
model.load_state_dict(torch.load(data_config['model'], map_location=device))
model = model.to(device)
criterion = torch.nn.MSELoss(reduction='none')
model.eval()


# detection day by day
for day in data_config['detect_days']:
    storage = Storage(data_config, day=day, test=True)
    label = load_label(data_name)
    if day in label:
        storage.label = label[day]
    eventf = open(f'{data_path}/{day}.json', 'r')
    log_line = eventf.readline()
    org_log = get_orgs(log_line)
    time_window_start = time_type(org_log[time_key])
    time_window_end = time_window_start + interval
    time_window_index = 0
    eventf.close()


    eventf = open(f'{data_path}/{day}.json', 'r')
    while(1):
        log_line = eventf.readline()
        if not log_line:
            break

        org_log = get_orgs(log_line)
        timestamp = time_type(org_log[time_key])
        
        if timestamp > time_window_end:
            data = storage.generate_time_window_graph()
            storage.local_pattern_extraction(data, model, criterion, device)
            storage.clear_time_window()
            
            time_window_index+=1
            time_window_start = time_window_end
            time_window_end = time_window_start + interval
        add_event_darpa(storage, org_log, EVENT_TYPE)

    data = storage.generate_time_window_graph()
    storage.local_pattern_extraction(data, model, criterion, device)
    storage.clear_time_window()
    eventf.close()

    storage.cross_pattern_detection()
    storage.alert_generation(root=f'result/{data_name}/{day}/')