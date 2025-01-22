import sys
sys.path.append('..')
from src.tools import *
from src.config import NODE_TYPE
import subprocess
from multiprocessing import Pool

############################################################
# Please configure your own path
# file_list is for used files
# file_path is for download root
# save_dir is for generated data

file_list = [
 'ta1-cadets-e3-official.json',
 'ta1-cadets-e3-official.json.1',
 'ta1-cadets-e3-official.json.2',
 'ta1-cadets-e3-official-1.json',
 'ta1-cadets-e3-official-1.json.1',
 'ta1-cadets-e3-official-1.json.2',
 'ta1-cadets-e3-official-1.json.3',
 'ta1-cadets-e3-official-1.json.4',
 'ta1-cadets-e3-official-2.json',
 'ta1-cadets-e3-official-2.json.1'
 ]

file_path="/root/cadets3/"

save_dir="./data/cadets3"
os.system(f'mkdir -p {save_dir}')
############################################################

pattern_time = re.compile(r'timestampNanos\":(.*?),')

edgeTypes = {
 'EVENT_CREATE_OBJECT': 0,
 'EVENT_OPEN': 1,
 'EVENT_CLOSE': 2,
 'EVENT_READ': 3,
 'EVENT_WRITE': 4,
 'EVENT_CLONE': 5,
 'EVENT_FORK': 6,
 'EVENT_CONNECT': 7,
 'EVENT_ACCEPT': 8,
 'EVENT_EXECUTE': 9,
 'EVENT_RECVFROM': 10,
 'EVENT_RECVMSG': 11,
 'EVENT_SENDTO': 12,
 'EVENT_SENDMSG': 13,
 'EVENT_RENAME': 14,
 'EVENT_LOADLIBRARY': 15,
 'EVENT_UPDATE': 16,
 'EVENT_UNLINK': 17,
 'EVENT_LINK': 18}

def check_uuid(uuid, entity_map):
    for node_type in [NODE_TYPE.FILE, NODE_TYPE.PROCESS, NODE_TYPE.NET]:
        if uuid in entity_map[node_type]:
            return node_type, entity_map[node_type][uuid]
    return -1, None

############################################################
# build entity map, simlar to Kairos[S&P'24]
entity_map = {NODE_TYPE.PROCESS:{}, NODE_TYPE.FILE:{}, NODE_TYPE.NET:{}}

# file entities
file_node = set()
for file in file_list:
    with open(file_path+file, 'r') as f:
        for line in f:
            if "com.bbn.tc.schema.avro.cdm18.FileObject" in line:
                Object_uuid = re.findall('FileObject":{"uuid":"(.*?)",', line)
                try:
                    file_node.add(Object_uuid[0])
                except:
                    print(line)

for file in file_list:
    with open(file_path+file, 'r') as f:
        for line in f:
            if '{"datum":{"com.bbn.tc.schema.avro.cdm18.Event"' in line:
                dst_uuid = re.findall('"predicateObject":{"com.bbn.tc.schema.avro.cdm18.UUID":"(.*?)"}',
                                                    line)
                if len(dst_uuid) > 0:
                    if dst_uuid[0] in file_node:
                        if '"predicateObjectPath":null,' not in line and '<unknown>' not in line:
                            path_name = re.findall('"predicateObjectPath":{"string":"(.*?)"', line)
                            entity_map[NODE_TYPE.FILE][dst_uuid[0]] = path_name[0]

# process entities
process_node = {}
for file in file_list:
    with open(file_path+file, 'r') as f:
        for line in f:
            if "com.bbn.tc.schema.avro.cdm18.Subject" in line:
                proc = re.findall('Subject":{"uuid":"(.*?)",(.*?),"cid":(.*?),"', line)
                try:
                    uuid, cid = proc[0][0], proc[0][-1]
                    process_node[uuid] = cid
                except:
                    print(line)

for file in file_list:
    with open(file_path+file, 'r') as f:
        for line in f:
            if "Event" in line:
                proc_uuid = re.findall(
                    '"subject":{"com.bbn.tc.schema.avro.cdm18.UUID":"(.*?)"}(.*?)"exec":"(.*?)"', line)
                try:
                    if proc_uuid[0][0] in process_node:
                        entity_map[NODE_TYPE.PROCESS][proc_uuid[0][0]] = f'{process_node[proc_uuid[0][0]]}\t{proc_uuid[0][-1]}'
                    else:
                        continue
                except:
                    try:
                        if proc_uuid[0][0] in process_node:
                            entity_map[NODE_TYPE.PROCESS][proc_uuid[0][0]] = f'{process_node[proc_uuid[0][0]]}'
                        else:
                            continue
                    except:
                        pass

# netflow entities
for file in file_list:
    with open(file_path+file, 'r') as f:
        for line in f:
            if "NetFlowObject" in line:
                try:
                    res = re.findall(
                        'NetFlowObject":{"uuid":"(.*?)"(.*?)"localAddress":"(.*?)","localPort":(.*?),"remoteAddress":"(.*?)","remotePort":(.*?),',
                        line)[0]

                    nodeid = res[0]
                    srcaddr = res[2]
                    srcport = res[3]
                    dstaddr = res[4]
                    dstport = res[5]
                    entity_map[NODE_TYPE.NET][nodeid] = f'{srcaddr}:{dstaddr}'
                except:
                    pass
for nt,name in zip([NODE_TYPE.FILE, NODE_TYPE.PROCESS, NODE_TYPE.NET], ['file', 'process', 'net']):
    print(f'{len(entity_map[nt])} {name}s', end='\t')
print()
############################################################

############################################################
# data generation

# benign data
END_TIME = datetime_to_ns_time_US('2018-04-06 00:00:00')
benign_data = []
for file in file_list:
    with open(file_path+file, 'r') as f:
        for line in f:
            if '{"datum":{"com.bbn.tc.schema.avro.cdm18.Event' in line:
                timestamp = int(pattern_time.findall(line)[0])
                if timestamp > END_TIME:
                    break
            benign_data.append(line)

c = 0
with open(f'{save_dir}/benign.json', 'w') as wf:
    for line in benign_data:
        if '{"datum":{"com.bbn.tc.schema.avro.cdm18.Event"' in line and "EVENT_FLOWS_TO" not in line:
            time_rec = re.findall('"timestampNanos":(.*?),', line)[0]
            
            proc_uuid = re.findall('"subject":{"com.bbn.tc.schema.avro.cdm18.UUID":"(.*?)"}', line)
            dst_uuid = re.findall('"predicateObject":{"com.bbn.tc.schema.avro.cdm18.UUID":"(.*?)"}', line)
            if len(proc_uuid) == 0 or len(dst_uuid) == 0:
                continue
            if proc_uuid[0] not in entity_map[NODE_TYPE.PROCESS]:
                continue
            dst_type, name = check_uuid(dst_uuid[0], entity_map)
            if dst_type == -1:
                continue
            event_type = re.findall('"type":"(.*?)"', line)[0]

            if event_type not in edgeTypes:
                continue
            
            proc = entity_map[NODE_TYPE.PROCESS][proc_uuid[0]].split()
            proc_pid, proc_name = proc[0], ''
            if len(proc)>1:
                proc_name = proc[1]

            if dst_type == NODE_TYPE.PROCESS:
                #'MSec', 'PID', 'PName','EventName', 'ChildID', 'ChildPName', 'CommandLine'
                pp = name.split()
                cpid, cpname = pp[0], ''
                if len(pp)>1:
                    cpname = pp[1]
                event_dict = {'MSec':time_rec, 'PID':proc_pid, 'PName':proc_name, 'EventName': event_type, 
                            'ChildID':cpid, 'ChildPName':cpname, 'CommandLine': proc_name}
                wf.write(json.dumps(event_dict)+'\n')

            if dst_type == NODE_TYPE.FILE:
                #'MSec', 'PID','PName','EventName','FileName'
                event_dict = {'MSec':time_rec, 'PID':proc_pid, 'PName':proc_name, 'EventName': event_type, 
                            'FileName':name}
                wf.write(json.dumps(event_dict)+'\n')
                
            if dst_type == NODE_TYPE.NET:
                # 'MSec', 'PID','PName','EventName','saddr', 'daddr'
                event_dict = {'MSec':time_rec, 'PID':proc_pid, 'PName':proc_name, 'EventName': event_type, 
                            'saddr':name.split(':')[0], 'daddr':name.split(':')[1]}
                wf.write(json.dumps(event_dict)+'\n')
                
# attack data
START_TIME = datetime_to_ns_time_US('2018-04-06 00:00:00')
pattern_time = re.compile(r'timestampNanos\":(.*?),')
day_file = {}
for day in [4,5,6,7,8,9,10,11,12,13]:
    day_file[day] = set()
    
for file, i in zip(file_list, range(len(file_list))):
    if not os.path.exists(f'{file_path}{file}'):
         continue
    result = subprocess.run(['head', f'{file_path}{file}', '-n', '10'], capture_output=True, text=True)
    output = result.stdout
    lines = output.split('\n')
    for line in lines:
        if 'com.bbn.tc.schema.avro.cdm18.Event' in line:
                timestamp = pattern_time.findall(line)[0]
                start = ns_time_to_datetime_US(timestamp)[:-10]
                break

    result = subprocess.run(['tail', f'{file_path}{file}', '-n', '10'], capture_output=True, text=True)
    output = result.stdout
    lines = output.split('\n')
    for li in range(len(lines)):
        line = lines[len(lines)-li-1]
        if 'com.bbn.tc.schema.avro.cdm18.Event' in line:
                timestamp = pattern_time.findall(line)[0]
                end = ns_time_to_datetime_US(timestamp)[:-10]
                break
    day_start = int(start[8:11])
    day_end = int(end[8:11])
    for day in range(day_start, day_end+1):
         if day in day_file:
            day_file[day].add(i)
print(day_file)

def generate_day_file(day):
    name = f'{day}.json'
    print(f'{day} {name}\n')
    target_fid = day_file[day]
    target_files = [file_list[i] for i in sorted(list(target_fid))]
    with open(f'{save_dir}/{name}', 'w') as wf:
        start_time = datetime_to_ns_time_US(f'2018-04-{day} 00:00:00')
        end_time = datetime_to_ns_time_US(f'2018-04-{day+1} 00:00:00')
        for file in target_files:
            with open(file_path+file, 'r') as f:
                for line in f:
                    if '{"datum":{"com.bbn.tc.schema.avro.cdm18.Event"' in line and "EVENT_FLOWS_TO" not in line:
                        time_rec = re.findall('"timestampNanos":(.*?),', line)[0]
                        if int(time_rec)>end_time:
                            break
                        if int(time_rec)<start_time:
                            continue

                        proc_uuid = re.findall('"subject":{"com.bbn.tc.schema.avro.cdm18.UUID":"(.*?)"}', line)
                        dst_uuid = re.findall('"predicateObject":{"com.bbn.tc.schema.avro.cdm18.UUID":"(.*?)"}', line)
                        if len(proc_uuid) == 0 or len(dst_uuid) == 0:
                            continue
                        if proc_uuid[0] not in entity_map[NODE_TYPE.PROCESS]:
                            continue
                        dst_type, name = check_uuid(dst_uuid[0], entity_map)
                        if dst_type == -1:
                            continue
                        
                        event_type = re.findall('"type":"(.*?)"', line)[0]

                        if event_type not in edgeTypes:
                            continue
                        
                        proc = entity_map[NODE_TYPE.PROCESS][proc_uuid[0]]
                        proc_pid, proc_name= proc.split('\t')

                        if proc_name.rfind('/')!=-1:
                            proc_name = proc_name[proc_name.rfind('/')+1:]

                        if dst_type == NODE_TYPE.PROCESS:
                            cpid, cpname = name.split('\t')
                            if cpname.rfind('/')!=-1:
                                cpname = cpname[cpname.rfind('/')+1:]
                            
                            event_dict = {'MSec':time_rec, 'PID':proc_pid, 'PName':proc_name, 'EventName': event_type, 
                                        'ChildID':cpid, 'ChildPName':cpname}
                            wf.write(json.dumps(event_dict)+'\n')

                        if dst_type == NODE_TYPE.FILE:
                            event_dict = {'MSec':time_rec, 'PID':proc_pid, 'PName':proc_name, 'EventName': event_type, 
                                        'FileName':name}
                            wf.write(json.dumps(event_dict)+'\n')
                            
                        if dst_type == NODE_TYPE.NET:
                            event_dict = {'MSec':time_rec, 'PID':proc_pid, 'PName':proc_name, 'EventName': event_type, 
                                        'saddr':name.split(':')[0], 'daddr':name.split(':')[1]}
                            wf.write(json.dumps(event_dict)+'\n')

thread_num = 8
with Pool(thread_num) as p:
    results = p.map(generate_day_file, [6,7,8,9,10,11,12,13])

############################################################

# timestamp information check for each test file
for day in range(6,14):
    result = subprocess.run(['head', f'{save_dir}/{day}.json', '-n', '1'], capture_output=True, text=True)
    output = result.stdout
    print(ns_time_to_datetime_US(get_orgs(output)['MSec'])[:-10])
    result = subprocess.run(['tail', f'{save_dir}/{day}.json', '-n', '1'], capture_output=True, text=True)
    output = result.stdout
    print(ns_time_to_datetime_US(get_orgs(output)['MSec'])[:-10])
    print()