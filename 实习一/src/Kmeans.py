import shapefile
from matplotlib import pyplot as plt
import random
import math

# 获取文件点的坐标
def getPointsCoordinates(path):
    """
    Args:
        path:shp文件路径
    """
    # 使用Reader读取shapefile文件
    point_file=shapefile.Reader(path)
    print(point_file)
    # 使用shapes得到文件夹里的所有Shape类（返回列表）包括点线面
    nanjing_point=point_file.shapes()
    # 可使用Shape类提供了获取点坐标的方法获取点坐标
    print(nanjing_point[0].points) # 查看点的结构
    # 获取点坐标的列表方便绘图
    point_list=[]
    for point in nanjing_point:
        point_list.append((point.points)[0])
    print(len(point_list)) # 检查点是否为800个
    print(point_list)

    # 使用matplot绘图
    x,y=zip(*point_list)
    fig, ax = plt.subplots()  # 生成一张图和一张子图
    # plt.plot(x,y,'k-') # x横坐标 y纵坐标 ‘k-’线性为黑色
    plt.scatter(x, y, color='#6666ff', label='fungis')  # x横坐标 y纵坐标 ‘k-’线性为黑色
    ax.axis('equal')
    plt.show()

    return point_list

# 获取两点之间距离
def getDistance(a,b):
    x1,y1=a
    x2,y2=b
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# 获取初始聚类中心坐标
def getCenterCoordinates(point_list,center_num):
    """
    Args:
        point_list:点坐标列表[(x1,y1),(x2,y2)...]
        center_num:聚类中心个数
    """
    random_index = random.randint(0, len(point_list) - 1)  # 生成随机索引
    center_point_index=[] # 存储聚类中心的索引
    center_point_index.append(random_index)
    # 获取最小距离里的最大者
    while (len(center_point_index)<center_num):
        center_point_index.append(500)
        max_distance=0
        for i in range(len(point_list)):
            min_distance=float('inf')
            for j in range(len(center_point_index)-1):
                current_distance=getDistance(point_list[i],point_list[center_point_index[j]])
                # 和已知中心点比选最小距离
                if (j==0) or (current_distance<min_distance):
                    min_distance=current_distance
            # 和暂定的点比选最大距离
            if min_distance>max_distance:
                max_distance=min_distance # 注意更新最远距离！
                center_point_index[-1]=i   

    center_point=[]
    for index in center_point_index:
        center_point.append(point_list[index])

    x,y=zip(*center_point)
    fig, ax = plt.subplots()  # 生成一张图和一张子图
    # plt.plot(x,y,'k-') # x横坐标 y纵坐标 ‘k-’线性为黑色
    plt.scatter(x, y, color='#6666ff', label='fungis')  # x横坐标 y纵坐标 ‘k-’线性为黑色
    ax.grid()  # 添加网格线
    ax.axis('equal')
    plt.show()
    return center_point

# 更新聚类中心
def updateCenter(point_list,labes_list,center_point_list):
    """
    Args:
        point_list:点坐标列表[(x1,y1),(x2,y2)...]
        labes_list:存储所有点的标签列表，每位的数字代表聚类中心center_point_linst的索引，例如：[0,0,1,3,2...]
        center_point_list:当前聚类中心坐标列表[(x1,y1),(x2,y2)...]
    Returns:
        return:新中心的列表
    """
    #sum_point=[[0,0]]*len(center_list)    # 这里千万不能用列表来初始化，要不然会造成浅拷贝，所有数据一样！
    sum_point=[]# 创建一个列表记录每一类的所有点的x，y的和，方便求均值
    count=[]# 统计每类的数量
    for i in range(len(center_point_list)):
        sum_point.append([0,0])
        count.append(0)

    for point_index in range(len(point_list)):
        point=point_list[point_index]
        labe=labes_list[point_index]
        sum_point[labe][0] += point[0]  # x累加
        sum_point[labe][1] += point[1]  # y累加
        count[labe] += 1    
    # 计算新中心（均值）
    new_centers = []
    for i in range(len(center_list)):
        if count[i] > 0:
            new_x = sum_point[i][0] / count[i]
            new_y = sum_point[i][1] / count[i]
            new_centers.append((new_x, new_y))
        else:
            new_centers.append(center_list[i])  # 如果簇无点,保留旧中心
    return new_centers

# 更新每个点的标签
def updateLabes(point_list,center_point_list):
    """
    Args:
        point_list:点坐标列表[(x1,y1),(x2,y2)...]
        center_point_list:原始聚类中心坐标列表[(x1,y1),(x2,y2)...]
    Returns:
        return:所有点的标签列表，每位的数字代表聚类中心center_point_linst的索引，例如：[0,0,1,3,2...]
    """
    lables=[]
    for point_index in range(len(point_list)):
        lables.append(-1) #提供默认初始值，若出现-1说明流程出错
        point=point_list[point_index]
        min_distance=float("inf")
        for center_index in range(len(center_point_list)):
            center=center_point_list[center_index]
            distance=getDistance(point,center)
            if distance<min_distance:
                min_distance=distance #记得更新min_distance!min_distance!
                lables[point_index]=center_index
    return lables

# 判断标签是否发生改变
def isLableChange(old_lables_list,new_lables_list):
    """
    辅助代码，给出两个labels，判断是否发生改变
    Returns:
        return:返回改变数量
    """
    count=0
    for i in range(len(old_lables_list)):
        old_lable=old_lables_list[i]
        new_lable=new_lables_list[i]
        if old_lable!=new_lable:
            count+=1
    return count

# 判断聚类中心是否发生变化
def isCenterChange(old_center_list,new_center_list):
    """
    辅助代码，给出两个聚类中心坐标的列表，判断是否发生改变
    Returns:
        return:返回总的中心偏移距离
    """
    distance=0
    for i in range(len(old_center_list)):
        distance+=getDistance(old_center_list[i],new_center_list[i])
    return distance
        

def Kmeans(point_list,center_point_list,count=10000):
    """
    Args:
        point_list:所有点坐标列表[(x1,y1),(x2,y2)...]
        center_point_list:初始聚类中心坐标列表[(x1,y1),(x2,y2)...]
        count:聚类循环的最大次数
    """
    labels=[]
    is_lable_change=True
    is_center_change=True
    while is_center_change and is_lable_change and count:
        new_labels=updateLabes(point_list,center_point_list)
        new_center_point_list=updateCenter(point_list,new_labels,center_point_list)
        # 判断条件1：标签是否改变
        is_lable_change=isLableChange(labels,new_labels)
        #判断条件2：聚类中心是否改变
        is_center_change=isCenterChange(center_point_list,new_center_point_list)
        labels=new_labels
        center_point_list=new_center_point_list
        count-=1
    return labels


def plotClusters(point_list, labels):
    """
    不同类别绘制不同颜色的点
    Args:
        point_list: 点坐标列表 [(x1, y1), (x2, y2), ...]
        labels: 每个点的类别 [0, 1, 2, ...]
    """
    # 定义颜色（类别多了会循环）
    colors = ['red', 'green', 'blue', 'cyan', 'magenta', 'yellow', 'black']
    # 遍历所有点，按类别上色
    for i, (x, y) in enumerate(point_list):
        color = colors[labels[i] % len(colors)]  # 防止类别超出颜色列表
        plt.scatter(x, y, c=color, label=f'Cluster {labels[i]}')
    # 避免重复图例
    handles, labels_legend = plt.gca().get_legend_handles_labels()
    unique = [(h, l) for i, (h, l) in enumerate(zip(handles, labels_legend)) if l not in labels_legend[:i]]
    plt.legend(*zip(*unique))
    plt.show()


import os
if __name__=="__main__":
    # 使用相对路径请好好检查你的当前路径吧
    print(os.getcwd())
    point_list=getPointsCoordinates(r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\实习一\data\实验一\Test1.shp")
    center_list=getCenterCoordinates(point_list,3)
    lables=Kmeans(point_list,center_list)
    plotClusters(point_list,lables)

