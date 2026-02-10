from src.config import *
from src.storage import *
from src.log_parser import *
from src.model import MemAPT

host_id = sys.argv[1]
data_config = json.load(open('config/data.json', 'r'))['optc']
data_path = data_config['data_path']
interval = data_config['interval']
EVENT_TYPE = EVENT_TYPE_CONFIG(data_config['event_config_path'])
time_type = int
time_key = 'MSec'

# model config
args = ARGS(data_config['infeat'])
device = torch.device(int(sys.argv[2]))

model = MemAPT(args, device)
model.load_state_dict(torch.load(f'trained_model/{host_id}.pt', map_location=device))
model = model.to(device)
criterion = torch.nn.MSELoss(reduction='none')
model.eval()

storage = Storage(data_config, test=True)
label = load_label('optc')
storage.label = label[int(host_id)]
eventf = open(f'{data_path}/{host_id}.json', 'r')
log_line = eventf.readline()
org_log = get_orgs(log_line)
time_window_start = time_type(org_log[time_key])
time_window_end = time_window_start + interval
time_window_index = 0
eventf.close()


eventf = open(f'{data_path}/{host_id}.json', 'r')
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
    add_event_optc(storage, org_log, EVENT_TYPE)

data = storage.generate_time_window_graph()
storage.local_pattern_extraction(data, model, criterion, device)
storage.clear_time_window()
eventf.close()

storage.cross_pattern_detection()
storage.alert_generation(root=f'result/optc/{host_id}')