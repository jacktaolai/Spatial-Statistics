import shapefile
from matplotlib import pyplot as plt
import numpy as np
from tqdm import tqdm  # 导入进度条库
import random
import math
from shapely.geometry import Polygon #计算多边形面积


# 获取文件点的坐标
def getPointsCoordinates(path,is_plot=True):
    """
    Args:
        path:shp文件路径
        is_plot:是否开启绘图，默认True
    """
    # 使用Reader读取shapefile文件
    point_file=shapefile.Reader(path)
    #print(point_file)
    # 使用shapes得到文件夹里的所有Shape类（返回列表）包括点线面
    shp=point_file.shapes()
    # 可使用Shape类提供了获取点坐标的方法获取点坐标
    #print(shp[0].points) # 查看点的结构
    # 获取点坐标的列表方便绘图
    point_list=[]
    for point in shp:
        point_list.append((point.points)[0])
    print(point_list)
    if is_plot:
        # 使用matplot绘图
        x,y=zip(*point_list)
        fig, ax = plt.subplots()  # 生成一张图和一张子图
        # plt.plot(x,y,'k-') # x横坐标 y纵坐标 ‘k-’线性为黑色
        plt.scatter(x, y, color='#6666ff', label='fungis')  # x横坐标 y纵坐标 ‘k-’线性为黑色
        ax.axis('equal')
        plt.show()
    return point_list
def getPolygonCoordinates(path,is_plot=False):
    """
    Args:
        path:面的shp文件的地址
        is_plot:是否绘图展示
    Returns:
        返回点的列表
    """
    # 使用Reader读取shapefile文件
    point_file=shapefile.Reader(path)
    #print(point_file)
    # 使用shapes得到文件夹里的所有Shape类（返回列表）包括点线面
    shp=point_file.shapes()
    # 可使用Shape类提供了获取点坐标的方法获取点坐标
    #print(shp[0].points) # 查看点的结构
    # 获取点坐标的列表方便绘图
    point_list=shp[0].points

    if is_plot:
        # 使用matplot绘图
        x,y=zip(*point_list)
        fig, ax = plt.subplots()  # 生成一张图和一张子图
        # plt.plot(x,y,'k-') # x横坐标 y纵坐标 ‘k-’线性为黑色
        plt.plot(x, y, color='#6666ff', label='fungis')  # x横坐标 y纵坐标 ‘k-’线性为黑色
        ax.axis('equal')
        plt.show()
    return point_list

# 获取两点之间距离
def getDistance(a,b):
    """
    Args:
        a,b:点坐标[x1,y1],[x2,y2]
    Returns:
        两点之间距离
    """
    x1,y1=a
    x2,y2=b
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
# 计算RipleysK
def calRipleyK(point_list,start,end,step_size,study_area_size,is_plot=False):
    """
    Args:
        point_list:所有点的列表[(x1,y1),(x2,y2)...]
        star:开始的缓冲区距离,建议为0
        end:结束的缓冲区距离
        step_size:每一步距离的步长
        study_area_size:研究区域的面积
        is_plot:是否绘图，默认False
    Returns:
        返回[r_list,k_list],分别为缓冲区距离，每个缓冲区的K函数值
    """
    # 存储距离方便后面判断在不在缓冲区内
    distance_table=[]
    for i in point_list:
        distance_table.append([])
        for j in point_list:
            distance_table[-1].append(getDistance(i,j))
    point_num=len(point_list) # 点数

    r_list=np.arange(start, end, step_size).tolist() # 缓冲区半径的列表
    count_list=[] # 缓冲区内的点个数的列表
    for r in tqdm(r_list, desc="处理半径r"):# 对每个缓冲区求一次k
        count=0 #在缓冲区内的个数
        for i in range(point_num):
            for j in range(point_num):
                if(i!=j):
                    if(distance_table[i][j]<=r):
                        count+=1
        count_list.append(count)
    k_list=[] # 存储k函数值
    for count in count_list:
        k_list.append(study_area_size*count/(point_num*(point_num-1)))
    
    result=[r_list,k_list]
    # 绘图
    if is_plot:
        pi_r_squared = [math.pi * r ** 2 for r in r_list] #理论期望值
        plt.figure(figsize=(8, 5))
        plt.plot(r_list, k_list, 'b-', label='k vs r')
        #plt.scatter(r_list, k_list, color='red', label='Data Points (k)')
        plt.plot(r_list, pi_r_squared, 'g--', label='πr²')
        #plt.scatter(r_list, pi_r_squared, color='purple', label='Data Points (πr²)')
        plt.title("Ripleys'K Function")
        plt.xlabel("r/m")
        plt.ylabel("K(r)")
        plt.grid(True)
        plt.legend()
        plt.show()
        # 实验
        # l_values = np.sqrt(np.array(k_list) / np.pi) 
        # plt.plot(r_list, l_values, label="L(r)")
        # plt.plot(r_list, r_list, label="E(r)")
        # plt.axhline(0, color='red', linestyle='--', label="完全随机")
        # plt.title("Ripley's L Function")
        # plt.show()

    
    
def calStudyAreaSize(study_area_shp_path,point_list):
    """
    计算研究区的面积
    Args:
        study_area_shp_path:研究区域的shp文件,若无请填None！
        point_list:研究点的列表
    Returns:
        和Arcgis一样，若无研究区域，使用所有点的最大外接矩形，若有，使用研究区域的面积，请确保研究区域给的是投影坐标系!
    """
    if study_area_shp_path==None:
        # 初始化外接矩形的四个顶点
        min_x=float("inf")
        max_x=-float("inf")
        min_y=float("inf")
        max_y=-float("inf")
        for point in point_list:
            if point[0]>max_x:  max_x=point[0]
            if point[0]<min_x:  min_x=point[0]
            if point[1]>max_y:  max_y=point[1]
            if point[1]<min_y:  min_y=point[1]
        return (max_x-max_y)*(max_y-min_x)
    else:
        study_area_shp=getPolygonCoordinates(study_area_shp_path,True)
        #tuple_coords = [tuple(coord) for coord in study_area_shp]# 将点变为[[x,y]...]->[(x,y)...]形式
        return Polygon(study_area_shp).area # 使用shaply自带的计算面积方法

            

import pandas as pd 

if __name__=="__main__":
    point_list=getPointsCoordinates(r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\实习二\data\武汉银行gsc2000 164.shp")

    A=calStudyAreaSize(r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\实习二\data\武汉市cgcs2000 114E.shp",point_list)
    result=calRipleyK(point_list,0,34000,1,A,True)
    # 转换为 DataFrame 并保存
    df = pd.DataFrame({
        "r_buffer": result[0],  # 缓冲区距离 r
        "K_value": result[1]    # K函数值
    })
    df.to_csv("ripley_k_results.csv", index=False)  # 不保存行索引
