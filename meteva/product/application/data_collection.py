import shutil
import datetime
import meteva
import os
import numpy as np
#from meteva.base.io import DataBlock_pb2
#from meteva.base.io.GDS_data_service import GDSDataService
from multiprocessing import Process,cpu_count

para_example= {
    "cup_count":1,
    "ip_port_file":r"H:\test_data\input\input\meb\ip_port.txt",
    "local_binary_dir": r"O:\data\mdfs",
    "local_sta_dir": r"O:\data\sta",
    "local_grid_dir":r"O:\data\grid",
    "max_save_day": 14,
    "sta_origin_dirs": [
        ["mdfs:///SURFACE/QC_BY_FSOL/RAIN01_ALL_STATION/", [[0, 2359]]],
        ["mdfs:///SURFACE/QC_BY_FSOL/WIND_AVERAGE_2MIN_ALL_STATION/", [[0, 2359]]],
        ["mdfs:///SURFACE/QC_BY_FSOL/TMP_ALL_STATION/", [[0, 2359]]],
    ],
    "grid_origin_dirs": {
        "NWFD_SCMOC": [
            ["NWFD_SCMOC/RAIN03", [[1100, 1200],[2100,2300]]],
            ["NWFD_SCMOC/TMP/2M_ABOVE_GROUND", [[1100, 1200],[2100,2359]]],
            ["NWFD_SCMOC/WIND/10M_ABOVE_GROUND", [[1100, 1200],[2100,2359]]],
        ],
        "EWMWF": [
            ["ECMWF_HR/TMP_2M/", [[1100, 1200],[2200,2359]]],
            ["ECMWF_HR/APCP/", [[1100, 1200],[2200,2359]]],
            ["mdfs:///ECMWF_HR/WIND_10M/", [[1100, 1200],[2200,2359]]],
        ],
        "GRAPES_GFS": [
            ["mdfs:///GRAPES_GFS/WIND/10M_ABOVE_GROUND/", [[1100, 1200],[2200,2359]]],
            ["GRAPES_GFS/TMP/2M_ABOVE_GROUND", [[1100, 1200],[2200,2359]]],
            ["GRAPES_GFS/APCP", [[1100, 1200],[2200,2359]]],
        ],
    }
}





def download_one_cup(k,ip,port,local_binary_dir,local_sta_dir,local_grid_dir,file_sta_list,file_grid_list):
    service = meteva.base.io.GDSDataService(ip, port)
    for filepath in file_sta_list:
        dir,file = os.path.split(filepath)
        save_path = local_binary_dir + "/" + dir + "/" + file
        dati_str = meteva.product.application.get_dati_str_of_path(save_path)
        try:
            status, response = service.getData(dir, file)
            ByteArrayResult = meteva.base.io.DataBlock_pb2.ByteArrayResult()
            if status == 200:
                ByteArrayResult.ParseFromString(response)
                if ByteArrayResult is not None:
                    byteArray = ByteArrayResult.byteArray
                    save_path_sta = local_sta_dir + "/" + dir + "/" + dati_str + "/" + file
                    meteva.base.tool.path_tools.creat_path(save_path_sta)
                    br = open(save_path_sta, 'wb')
                    br.write(byteArray)
                    br.close()
                    print(save_path_sta)
                    print(k)
        except Exception as e:
            print(e)

    for filepath in file_grid_list:
        dir,file = os.path.split(filepath)
        save_path = local_binary_dir + "/" + dir + "/" + file
        dati_str = meteva.product.application.get_dati_str_of_path(save_path)
        try:
            status, response = service.getData(dir, file)
            ByteArrayResult = meteva.base.io.DataBlock_pb2.ByteArrayResult()
            if status == 200:
                ByteArrayResult.ParseFromString(response)
                if ByteArrayResult is not None:
                    byteArray = ByteArrayResult.byteArray
                    meteva.base.tool.path_tools.creat_path(save_path)
                    br = open(save_path, 'wb')
                    br.write(byteArray)
                    br.close()
                    if dir.upper().find("WIND") >= 0:
                        if (dir.upper().find("GUST")) >= 0:
                            grd = meteva.base.io.byteArray_to_griddata(byteArray)
                        else:
                            grd = meteva.base.io.byteArray_to_gridwind(byteArray)
                    else:
                        grd = meteva.base.io.byteArray_to_griddata(byteArray)
                    save_path_nc = local_grid_dir + "/" + dir + "/" + dati_str + "/" + file + ".nc"
                    meteva.base.write_griddata_to_nc(grd, save_path_nc, creat_dir=True,show=True)
                    print(k)
        except Exception as e:
            print(e)

def download_mp(ip,port,local_binary_dir,local_sta_dir,local_grid_dir,download_sta_list,download_grid_list,multi_pro_num):
    max_pro_num = cpu_count() - 2
    if multi_pro_num > max_pro_num:
        multi_pro_num = max_pro_num

    file_sta_dict_list = {}
    file_grid_dict_list = {}
    for i in range(multi_pro_num):
        file_sta_dict_list[i] = []
        file_grid_dict_list[i] = []

    for i in range(len(download_sta_list)):
        k = i % multi_pro_num
        file_sta_dict_list[k].append(download_sta_list[i])
    for i in range(len(download_grid_list)):
        k = i % multi_pro_num
        file_grid_dict_list[k].append(download_grid_list[i])

    PP = []
    for k in range(multi_pro_num):
        tmpp = Process(target=download_one_cup, args=(k,ip,port,local_binary_dir,local_sta_dir,local_grid_dir,file_sta_dict_list[k],file_grid_dict_list[k]))
        PP.append(tmpp)
    print('Waiting for all subprocesses done...')
    for pc in PP:
        pc.start()

    for pp in PP:
        pp.join()
    print('All subprocesses done.')


def in_op_time(hm,op_list_list):
    in_op = False
    for down_set in op_list_list:
        if hm >= down_set[0] and hm <= down_set[1]:
            in_op = True
    return in_op

def download_from_gds(para):
    #遍历下载
    now = datetime.datetime.now()
    print("于"+str(now)+"开始下载")
    weekago = now - datetime.timedelta(days=7)
    hm = now.hour * 100 + now.minute
    ip,port = meteva.base.io.read_gds_ip_port(para["ip_port_file"])
    service = meteva.base.io.GDSDataService(ip, port)
    if (service is None):
        print("service is None")
        return
    download_sta_list = []
    for down_set in para["sta_origin_dirs"]:
        if in_op_time(hm,down_set[1]):
            dir_list = []
            meteva.base.tool.path_tools.get_gds_all_dir(ip,port,down_set[0],dir_list)
            for dir in dir_list:
                file_list = meteva.base.tool.path_tools.get_gds_file_list_in_one_dir(ip,port,dir)
                file_list.sort(reverse = True)
                for file in file_list:
                    dati = meteva.product.application.get_dati_of_path(file)
                    if dati < weekago:break
                    dati_str = meteva.product.application.get_dati_str_of_path(file)
                    save_path_sta = para["local_sta_dir"] + "/" + dir + "/" + dati_str + "/" + file
                    if not os.path.exists(save_path_sta):
                        download_sta_list.append(dir + "/" +file)

    download_grid_list = []
    for key in para["grid_origin_dirs"].keys():
        down_set_group  = para["grid_origin_dirs"][key]
        for down_set in down_set_group:
            if in_op_time(hm, down_set[1]):
                dir_list = []
                meteva.base.tool.path_tools.get_gds_all_dir(ip,port,down_set[0],dir_list)
                for dir in dir_list:
                    file_list = meteva.base.tool.path_tools.get_gds_file_list_in_one_dir(ip,port,dir)
                    file_list.sort(reverse=True)
                    for file in file_list:
                        dati = meteva.product.application.get_dati_of_path(file)
                        if dati < weekago: break
                        save_path = para["local_binary_dir"] + "/" +dir+"/" +file
                        if not os.path.exists(save_path):
                            download_grid_list.append(dir + "/" + file)
                        else:
                            try:
                                dati_str = meteva.product.application.get_dati_str_of_path(save_path)
                                save_path_nc = para["local_grid_dir"] + "/" + dir + "/" + dati_str + "/" + file+".nc"
                                if not os.path.exists(save_path_nc):
                                    if dir.upper().find("WIND")>=0:
                                        if (dir.upper().find("GUST"))>=0:
                                            grd = meteva.base.read_griddata_from_gds_file(save_path)
                                        else:
                                            grd = meteva.base.read_gridwind_from_gds_file(save_path)
                                    else:
                                        grd = meteva.base.read_griddata_from_gds_file(save_path)
                                    if grd is not None:
                                        meteva.base.write_griddata_to_nc(grd, save_path_nc, creat_dir=True)
                                    else:
                                        print(save_path + "文件格式错误")
                            except Exception as e:
                                print(e)

    download_mp(ip, port, para["local_binary_dir"], para["local_sta_dir"], para["local_grid_dir"], download_sta_list, download_grid_list,
                para["cup_count"])


def remove(dir,save_day):
    file_list = meteva.base.tool.path_tools.get_path_list_in_dir(dir)
    now = datetime.datetime.now()
    for file in file_list:
        dati = meteva.product.application.get_dati_of_path(file)
        dday = (now - dati).total_seconds()/(3600*24)
        if dday > save_day:
            os.remove(file)
    print(dir +"目录下"+str(save_day)+"天之前的数据已删除")


para_list = [
    {
        "input":r"O:\data\grid\GRAPES_GFS\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output":r"L:\luoqi\GRAPES_GFS\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start":datetime.datetime(2020,3,1,8,0),
        "end":datetime.datetime(2020,6,1,8,0),
        "hour_range":[8,21,12],
        "dh_range":[3,241,3],
        "recover":False
    },

    {
        "input": r"O:\data\grid\ECMWF_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"L:\luoqi\ECMWF_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 3, 1, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [8, 21, 12],
        "dh_range": [3, 241, 3],
        "recover": False
    },

    {
        "input": r"O:\data\grid\NCEP_GFS_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"L:\luoqi\NCEP_GFS_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 3, 1, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [8, 21, 12],
        "dh_range": [3, 241, 3],
        "recover": False
    },

    {
        "input": r"O:\data\grid\SHANGHAI_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"L:\luoqi\SHANGHAI_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 3, 1, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [0, 24, 1],
        "dh_range": [0, 25, 1],
        "recover": False
    },

    {
        "input": r"O:\data\grid\GRAPES_MESO_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"L:\luoqi\GRAPES_MESO_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 3, 1, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [2, 24, 3],
        "dh_range": [0, 85, 1],
        "recover": False
    },

    {
        "input": r"O:\data\grid\GRAPES_3KM\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"L:\luoqi\GRAPES_3KM\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 3, 1, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [2, 24, 3],
        "dh_range": [0, 37, 1],
        "recover": False
    },

]


para_list1 = [
    {
        "input":r"O:\data\grid\NWFD_SCMOC\RAIN03\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output":r"\\10.28.27.93\SCMOC\RAIN03\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start":datetime.datetime(2020,5,20,8,0),
        "end":datetime.datetime(2020,6,1,8,0),
        "hour_range":[8,21,12],
        "dh_range":[3,241,3],
        "recover":False
    },
    {
        "input": r"O:\data\grid\NWFD_SCMOC\TMP\2M_ABOVE_GROUND\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"\\10.28.27.93\SCMOC\TMP\2M_ABOVE_GROUND\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 5, 20, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [8, 21, 12],
        "dh_range": [3, 241, 3],
        "recover": False
    },
    {
        "input": r"O:\data\grid\NWFD_SCMOC\WIND\10M_ABOVE_GROUND\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"\\10.28.27.93\SCMOC\WIND\10M_ABOVE_GROUND\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 5, 20, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [8, 21, 12],
        "dh_range": [3, 241, 3],
        "recover": False
    },
]


def copy_data_file(para_list):
    for para in para_list:
        time0 = para["start"]
        time1 = datetime.datetime(time0.year,time0.month,time0.day,0,0)
        hour_list =  np.arange(para["hour_range"][0],para["hour_range"][1],para["hour_range"][2]).tolist()
        dh_list = np.arange(para["dh_range"][0], para["dh_range"][1], para["dh_range"][2]).tolist()
        recover = para["recover"]
        while time1 <= para["end"]:
            for hour in hour_list:
                time2 = time1 +datetime.timedelta(hours=hour)
                for dh in dh_list:
                    path_out = meteva.base.get_path(para["output"],time2,dh)
                    if recover or not os.path.exists(path_out):
                        path_in = meteva.base.get_path(para["input"],time2,dh)
                        if os.path.exists(path_in):
                            meteva.base.creat_path(path_out)
                            shutil.copyfile(path_in,path_out)
            time1 = time1 + datetime.timedelta(hours=24)



if __name__ == '__main__':
    #download_from_gds(para_example)
    copy_data_file(para_list1)



