import shapefile
from matplotlib import pyplot as plt
import numpy as np
from tqdm import tqdm  # 导入进度条库
import random
import math
from shapely.geometry import Polygon #计算多边形面积
from shapely.geometry import Point # 随机采样点



# 获取文件点的坐标
def getPointsCoordinates(path,is_plot=True):
    """
    Args:
        path:shp文件路径
        is_plot=True:是否开启绘图，默认True
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
    # print(point_list)
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
        is_plot=False:是否绘图展示
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
        start:开始的缓冲区距离,建议为0
        end:结束的缓冲区距离
        step_size:每一步距离的步长
        study_area_size:研究区域的面积
        is_plot=False:是否绘图，默认False
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
        plt.scatter(r_list, k_list, color='red', label='Data Points (k)')
        plt.plot(r_list, pi_r_squared, 'g--', label='πr²')
        plt.scatter(r_list, pi_r_squared, color='purple', label='Data Points (πr²)')
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
    return result

    
# 获取研究区域的边界和面积    
def calStudyAreaSize(study_area_shp_path,point_list,is_show_study_area=False):
    """
    计算研究区的面积
    Args:
        study_area_shp_path:研究区域的shp文件,若无请填None！
        point_list:研究点的列表
        is_show_study_area=False:是否展示研究区域，仅在传入shp有效
    Returns:
        [study_area_size,study_area_point_list]:研究区域面积，研究区域的点列表
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
        study_area_size=(max_x-min_x)*(max_y-min_y)
        study_area_point_list=[[min_x,min_y],[min_x,max_y],[max_x,min_y],[max_x,max_y]]
        return [study_area_size,study_area_point_list]
    else:
        study_area_shp=getPolygonCoordinates(study_area_shp_path,is_show_study_area)
        #tuple_coords = [tuple(coord) for coord in study_area_shp]# 将点变为[[x,y]...]->[(x,y)...]形式
        return [Polygon(study_area_shp).area,study_area_shp] # 使用shaply自带的计算面积方法

#在研究区域内随机采样
def randomPointsInPolygon(polygon: list, num_points: int):
    """
    从研究区域内随机采样
    Args:
        polygon:列表类型，包含研究区域边界点坐标
        num_points:采样的店的个数
    Return:
        返回列表，包括所有采样的点的坐标
    """
    polygon=Polygon(polygon)
    min_x, min_y, max_x, max_y =  polygon.bounds
    points = []
    while len(points) < num_points:
        # 在边界框内生成随机点
        random_x = np.random.uniform(min_x, max_x)
        random_y = np.random.uniform(min_y, max_y)
        point = [random_x, random_y]
        # 检查点是否在多边形内
        if polygon.contains(Point(random_x,random_y)):
            points.append(point)
    return points

# K函数
def KFunction(point_list,start,end,step_size,study_area_shp_path=None,is_plot=True,output_path="rioleysk.csv",cal_confidence=False,ci_lower=2.5,ci_higher=97.5,num_simulated_points=99,n_simulations=99):
    """
    完全的K函数计算方法，可保存csv结果
    Args:
        point_list:研究点坐标，以列表形式传入
        point_list:所有点的列表[(x1,y1),(x2,y2)...]
        star:开始的缓冲区距离,建议为0
        end:结束的缓冲区距离
        step_size:每一步距离的步长
        study_area_shp:研究区域的shp文件路径，用于计算研究面积，默认为None，则用外接矩形计算，请确保shp文件只有一个图形，且使用投影坐标系
        is_plot:是否绘图，默认True
        out_put_path=None:csv结果的保存地址,默认rioleysk.csv,若为None不保存（强烈建议传入地址），csv结果包括r的取值，对应r的k函数取值，置信上下界（若开启）
        cal_confidence=False:是否计算置信区间，默认False，若开启可能会加长计算时间，若不开启，后面参数无效
        ci_lower=2.5:百分置信区间的低值，默认为2.5，使用numpy实现，传入数值应为小数的100倍，例如：2.5代表2.5%即0.025分位
        ci_higher=97.5:百分置信区间的高值，默认为9.75，使用numpy实现，传入数值应为小数的100倍，例如：9.75代表97.5%即0.975分位
        num_simulated_points=999:区域内模拟的点个数，默认99个
        n_simulations=99:模拟的次数，默认999次
    Returns:
        函数返回:列表里包括：[r_list,k_list,theoretical_K_value,bound_lower,bound_high]

    """
    
    study_area_size,study_area_point=calStudyAreaSize(study_area_shp_path,point_list)# 研究区域面积和研究区域的边界点
    # 计算实验点的k函数
    r_list,k_list=calRipleyK(point_list=point_list,start=start,end=end,study_area_size=study_area_size,step_size=step_size,is_plot=False)

    result=[] # 要返回的结果
    result.append(r_list)
    result.append(k_list)
    theoretical_k = np.pi * np.array(r_list)**2  # K(r) = πr²
    result.append(theoretical_k.tolist())
    if cal_confidence:# 如果要计算置信度
        simulated_k_list=[] #存储每一次模拟出来的k函数值
        for _ in tqdm(range(n_simulations),desc="模拟次数"):# 模拟次数
            # 生成模拟点
            sim_points=randomPointsInPolygon(study_area_point,num_simulated_points)
            sim_k=calRipleyK(point_list=sim_points,start=start,end=end,study_area_size=study_area_size,step_size=step_size,is_plot=False)[1] #娶该函数返回的k列表

            simulated_k_list.append(sim_k)

        # 取所有模拟结果的上下边界
        bound_lower = np.percentile(simulated_k_list, ci_lower, axis=0)
        bound_high= np.percentile(simulated_k_list, ci_higher, axis=0)
        result.append(bound_lower.tolist())
        result.append(bound_high.tolist())
    if is_plot:
        plt.figure(figsize=(10, 6))
        
        # 绘制观测K函数（实线）
        plt.plot(r_list, k_list, 
                color='black', 
                linewidth=2, 
                label='Observed K-function')
        if cal_confidence:
            # 绘制模拟的置信区间
            plt.fill_between(r_list, 
                            bound_lower, 
                            bound_high, 
                            color='lightblue', 
                            alpha=0.5, 
                            label=f'{ci_higher - ci_lower}% Confidence Envelope')
            
            # 绘制模拟的平均值线（虚线）
            median_k = np.average(simulated_k_list, axis=0)
            plt.plot(r_list, median_k, 
                    linestyle='--', 
                    color='red', 
                    linewidth=1, 
                    label='Average of Simulations')
        
        # 绘制理论随机分布πr²（绿色点线）
        plt.plot(r_list, theoretical_k,
                linestyle=':', 
                color='green',
                linewidth=1.5,
                label='Theoretical K value')
        
        # 图例和标签
        plt.xlabel('Distance (r)')
        plt.ylabel('K(r)')
        plt.title('K-function and Confidence Envelope')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()
    header=["r_list","k_list","theoretical_K_value","bound_lower","bound_high"]  # 表头
    data={} # csv的输出内容
    if output_path:
        for i in range(len(result)):
            data[header[i]]=result[i]
    df = pd.DataFrame(data)
    # 写入CSV
    df.to_csv(output_path, index=False)  # index=False 表示不写入行索引
    print(f"已保存计算结果到{output_path}")
    return result

def ArcgisLFunction(r_list,k_list,theoretical_K_value,bound_lower=None,bound_high=None,is_plot=True):
    """
    Arcgis里L(r)的计算方法
    Args:
        r_list:半径的列表,为KFunction返回result里的第0个结果
        k_list:计算的搭配的k值，为KFunction返回result里返回的第1个结果
        theoretical_K_value:理论k值即πr²，为KFunction返回result里返回的第2个结果
        bound_lower=None:置信度下界，为KFunction返回result里返回的第3个结果
        bound_high=None:置信度下界，为KFunction返回result里返回的第4个结果
        is_plot:是否绘图
    Returns:
        L(r):计算方式为sqrt(k/π)
    """
     # 计算L(r)值
    L_list=np.sqrt(np.array(k_list)/np.pi)
    theoretical_L=np.sqrt(np.array(theoretical_K_value)/np.pi)
    if is_plot:
        plt.figure(figsize=(10, 6))
        # 绘制观测L函数（黑色实线）
        plt.plot(r_list,L_list, 
                color='black', 
                linewidth=2, 
                label='Observed L-function')
        if (bound_lower!=None)and(bound_high!=None):
            # 转换置信区间到L尺度
            bund_lower_L=np.sqrt(np.array(bound_lower)/np.pi)
            bound_high_L=np.sqrt(np.array(bound_high)/np.pi)
            
            # 绘制置信区间（浅蓝色填充）
            plt.fill_between(r_list, 
                            bund_lower_L, 
                            bound_high_L, 
                            color='lightblue', 
                            alpha=0.5, 
                            label='Confidence Envelope')
        
        # 绘制理论随机分布
        plt.plot(r_list,theoretical_L,
                linestyle=':', 
                color='green',
                linewidth=1.5,
                label='Theoretical L value')
        
        # 图例和标签
        plt.xlabel('Distance(r)')
        plt.ylabel('L(r)')
        plt.title('ArcgisL-function')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()
    
    return L_list,theoretical_L

def LFunction(r_list,k_list,theoretical_K_value,bound_lower=None,bound_high=None,is_plot=True):
    """
    普通的L(r)的计算方法
    Args:
        r_list:半径的列表,为KFunction返回result里的第0个结果
        k_list:计算的搭配的k值，为KFunction返回result里返回的第1个结果
        theoretical_K_value:理论k值即πr²，为KFunction返回result里返回的第2个结果
        bound_lower=None:置信度下界，为KFunction返回result里返回的第3个结果
        bound_high=None:置信度下界，为KFunction返回result里返回的第4个结果
        is_plot:是否绘图
    Returns:
        L(r):计算方式为sqrt(k/π)-r
    """
         # 计算L(r)值
    L_list=np.sqrt(np.array(k_list)/np.pi)-np.array(r_list)
    theoretical_L=np.sqrt(np.array(theoretical_K_value)/np.pi)-np.array(r_list)
    if is_plot:
        plt.figure(figsize=(10, 6))
        # 绘制观测L函数（黑色实线）
        plt.plot(r_list,L_list, 
                color='black', 
                linewidth=2, 
                label='Observed L-function')
        if (bound_lower!=None)and(bound_high!=None):
            # 转换置信区间到L尺度
            bund_lower_L=np.sqrt(np.array(bound_lower)/np.pi)-np.array(r_list)
            bound_high_L=np.sqrt(np.array(bound_high)/np.pi)-np.array(r_list)
            
            # 绘制置信区间（浅蓝色填充）
            plt.fill_between(r_list, 
                            bund_lower_L, 
                            bound_high_L, 
                            color='lightblue', 
                            alpha=0.5, 
                            label='Confidence Envelope')
        
        # 图例和标签
        plt.xlabel('Distance(r)')
        plt.ylabel('L(r)')
        plt.title('L(r)')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

import pandas as pd 

if __name__=="__main__":
    # 加载点数据和研究区域
    point_list=getPointsCoordinates(r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\实习二\data\武汉银行gsc2000 164.shp")
    study_area_shp_path=r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\实习二\data\武汉市cgcs2000 114E.shp"
    # 计算研究区域面积
    #study_area_shp_path=None
    A = calStudyAreaSize(study_area_shp_path, point_list,is_show_study_area=True)[0]
    # 调用KFunction
    result = KFunction(
        point_list=point_list,
        start=0, # 起始距离
        end=35000,  # 终止距离
        step_size=500,  # 步长
        study_area_shp_path=study_area_shp_path,  # 研究区域SHP路径
        is_plot=True,    # 自动绘图
        output_path="temp/ripley_k_results_with_ci.csv",  # 结果保存路径
        cal_confidence=True,   # 计算置信区间
        ci_lower=2.5, # 置信区间下限2.5%
        ci_higher=97.5,  # 置信区间上限97.5%
        num_simulated_points=99,  # 每次模拟点数
        n_simulations=100  # 模拟次数
    )
    # 计算和Arcgis同款的L函数
    ArcgisLFunction(result[0],result[1],result[2],result[3],result[4],True)
    LFunction(result[0],result[1],result[2],result[3],result[4],True)

