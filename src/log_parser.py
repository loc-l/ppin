def add_event_darpa(self, row, EVENT_TYPE):
        event_type = EVENT_TYPE.get_type(row['EventName'])
        if event_type is None:
            print(row)
            return
        if 'FileName' in row:
            dst_nid = self.add_file_node(row['FileName'])
        elif 'ChildID' in row:
            cpid, cpname = row['ChildID'], row['ChildPName']
            dst_nid = self.add_process_node(f'{cpid}\t{cpname}', cpname)
        elif 'daddr' in row:
            dst_nid = self.add_net_node(row['daddr'])
        else:
            return
        
        pid, pname = row['PID'], row['PName']
        process_nid = self.add_process_node(f'{pid}\t{pname}', pname)
        if process_nid not in self.temporal_time_window_edge:
            self.temporal_time_window_edge[process_nid] = {} # adj list
        if dst_nid not in self.temporal_time_window_edge[process_nid]:
            self.temporal_time_window_edge[process_nid][dst_nid] = set([event_type])
            return
        self.temporal_time_window_edge[process_nid][dst_nid].add(event_type)

