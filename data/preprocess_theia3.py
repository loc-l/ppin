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

filelist = [
 'ta1-theia-e3-official-1r.json',
 'ta1-theia-e3-official-1r.json.1',
 'ta1-theia-e3-official-1r.json.2',
 'ta1-theia-e3-official-1r.json.3',
 'ta1-theia-e3-official-1r.json.4',
 'ta1-theia-e3-official-1r.json.5',
 'ta1-theia-e3-official-1r.json.6',
 'ta1-theia-e3-official-1r.json.7',
 'ta1-theia-e3-official-1r.json.8',
 'ta1-theia-e3-official-1r.json.9',
 'ta1-theia-e3-official-3.json',
 'ta1-theia-e3-official-5m.json',
 'ta1-theia-e3-official-6r.json',
 'ta1-theia-e3-official-6r.json.1',
 'ta1-theia-e3-official-6r.json.2',
 'ta1-theia-e3-official-6r.json.3',
 'ta1-theia-e3-official-6r.json.4',
 'ta1-theia-e3-official-6r.json.5',
 'ta1-theia-e3-official-6r.json.6',
 'ta1-theia-e3-official-6r.json.7',
 'ta1-theia-e3-official-6r.json.8',
 'ta1-theia-e3-official-6r.json.9',
 'ta1-theia-e3-official-6r.json.10',
 'ta1-theia-e3-official-6r.json.11',
 'ta1-theia-e3-official-6r.json.12',
 ]

file_path="/root/theia3/"

save_dir = "./data/theia3"
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

def check_uuid(uuid):
    for node_type in [NODE_TYPE.FILE, NODE_TYPE.PROCESS, NODE_TYPE.NET]:
        if uuid in entity_map[node_type]:
            return node_type, entity_map[node_type][uuid]
    return -1, None

############################################################
# build entity map, simlar to Kairos[S&P'24]
thread_num = 21

def build_entity_map(file):
    entity_map = {NODE_TYPE.PROCESS:{}, NODE_TYPE.FILE:{}, NODE_TYPE.NET:{}}
    print(f'process {file}')
    with open(file_path+file, 'r') as f:
        for line in f:
            if "com.bbn.tc.schema.avro.cdm18.NetFlowObject" in line:
                try:
                    res = re.findall(
                        'NetFlowObject":{"uuid":"(.*?)"(.*?)"localAddress":"(.*?)","localPort":(.*?),"remoteAddress":"(.*?)","remotePort":(.*?),',
                        line)[0]

                    node_uuid = res[0]
                    srcaddr = res[2]
                    srcport = res[3]
                    dstaddr = res[4]
                    dstport = res[5]
                    entity_map[NODE_TYPE.NET][node_uuid] = f'{srcaddr}:{dstaddr}:{dstport}'
                except:
                    pass
                continue

            if "com.bbn.tc.schema.avro.cdm18.FileObject" in line:
                try:
                    res=re.findall('FileObject":{"uuid":"(.*?)"(.*?)"filename":"(.*?)"',line)[0]
                    node_uuid=res[0]
                    filename=res[2]
                    entity_map[NODE_TYPE.FILE][node_uuid] = filename
                except:
                    pass
                continue

            if "com.bbn.tc.schema.avro.cdm18.Subject" in line:
                proc = re.findall('Subject":{"uuid":"(.*?)",(.*?),"cid":(.*?),"(.*?)"cmdLine":{"string":"(.*?)"}', line)[0]
                try:
                    path_str=re.findall('"path":"(.*?)"',line)[0] 
                    path=path_str
                except:
                    path="null"
                    # print(line)
                    if proc[4]=='':
                        continue
                uuid, cid, cmd = proc[0], proc[2], proc[4]
                entity_map[NODE_TYPE.PROCESS][uuid] = [cid, cmd, path]
                continue
    return entity_map

with Pool(thread_num) as p:
    # 提交任务并获取结果
    results = p.map(build_entity_map, filelist)

entity_map = {NODE_TYPE.PROCESS:{}, NODE_TYPE.FILE:{}, NODE_TYPE.NET:{}}

for i in range(len(results)):
    for nt in results[i].keys():
        entity_map[nt].update(results[i][nt])

for nt in entity_map.keys():
    print(len(entity_map[nt]))

############################################################
############################################################
# data generation

filetime = []
pattern_time = re.compile(r'timestampNanos\":(.*?),')
day_file = {}
for day in [3,4,5,9,10,11,12,13]:
    day_file[day] = set()
    
for file, i in zip(filelist, range(len(filelist))):
    if not os.path.exists(f'{file_path}{file}'):
         continue
    # print(f'{file_path}{file}')
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
        day_file[day].add(i)
print(day_file)

def generate_day_file(day):
    name = f'{day}.json'
    print(f'{day} {name}\n')
    target_fid = day_file[day]
    target_files = [filelist[i] for i in sorted(list(target_fid))]
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
                        dst_type, name = check_uuid(dst_uuid[0])
                        if dst_type == -1:
                            continue
                        
                        event_type = re.findall('"type":"(.*?)"', line)[0]

                        if event_type not in edgeTypes:
                            continue
                        
                        proc_pid, proc_cmd, proc_name = entity_map[NODE_TYPE.PROCESS][proc_uuid[0]]
                        if proc_name.rfind('/')!=-1:
                            proc_name = proc_name[proc_name.rfind('/')+1:]

                        if dst_type == NODE_TYPE.PROCESS:
                            cpid, _, cpname = name
                            if cpname.rfind('/')!=-1:
                                cpname = cpname[cpname.rfind('/')+1:]
                            
                            event_dict = {'MSec':time_rec, 'PID':proc_pid, 'PName':proc_name, 'EventName': event_type, 
                                        'ChildID':cpid, 'ChildPName':cpname, 'CommandLine': proc_cmd}
                            # print(json.dumps(event_dict))
                            wf.write(json.dumps(event_dict)+'\n')

                        if dst_type == NODE_TYPE.FILE:
                            event_dict = {'MSec':time_rec, 'PID':proc_pid, 'PName':proc_name, 'EventName': event_type, 
                                        'FileName':name}
                            # print(json.dumps(event_dict))
                            wf.write(json.dumps(event_dict)+'\n')
                            
                        if dst_type == NODE_TYPE.NET:
                            # 'MSec', 'PID','PName','EventName','saddr', 'daddr', 'dport'
                            event_dict = {'MSec':time_rec, 'PID':proc_pid, 'PName':proc_name, 'EventName': event_type, 
                                        'saddr':name.split(':')[0], 'daddr':name.split(':')[1], 'dport':name.split(':')[2]}
                            # print(json.dumps(event_dict))
                            wf.write(json.dumps(event_dict)+'\n')
                        
    # print()

thread_num = 7
with Pool(thread_num) as p:
    results = p.map(generate_day_file, [3,4,5,9,10,11,12])

os.system(f'mv {save_dir}/9.json {save_dir}/benign.json.9')
os.system(f'cat {save_dir}/3.json {save_dir}/4.json {save_dir}/5.json > {save_dir}/benign.json.345')

for day in range(10,13):
    result = subprocess.run(['head', f'{save_dir}/{day}.json', '-n', '1'], capture_output=True, text=True)
    output = result.stdout
    print(ns_time_to_datetime_US(get_orgs(output)['MSec'])[:-10])
    result = subprocess.run(['tail', f'{save_dir}/{day}.json', '-n', '1'], capture_output=True, text=True)
    output = result.stdout
    print(ns_time_to_datetime_US(get_orgs(output)['MSec'])[:-10])
    print()