import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
import pandas as pd
from tqdm import tqdm 
def getPolygonFromShpFile(path,csv_path=None,shp_on=None,csv_on=None):
    """
    将只包含面的shapfile文件转为Polygon列表，代码不检查文件中是否为纯多边形，请只传入纯多边形shapefile
    Args:
        path:接收.shp文件的地址
        csv_path=None:需要分析的csv表格，若需要分析的属性在表格里而不在shp文件里，可以添加此字段将属性加入shp文件里，若为None则不开启此功能，连接为左连接，保留shp的全量内容
        shp_on=None:连接属性时shp里的连接字段（和csv文件具有相同的内容，如"id",也可为多个属性["id","日期"]）
        csv_on=None:连接属性时csv里的连接字段（和shp文件具有相同的内容，如"id",也可为多个属性["id","日期"]）
    Returns:
        返回gdf类型，同时控制台打印文件具有的属性列表
    """
    gdf=gpd.read_file(path)
    # 读取CSV
    if csv_path is not None:
        csv_data = pd.read_csv(csv_path)
        gdf = gdf.merge(
        csv_data,
        left_on=shp_on,     # gdf的键列
        right_on=csv_on,    # csv的键列
        how="left"          # 保留所有空间数据
        )
    
    # 添加gdfid保证唯一标识
    gdf["gdfid"] = range(1, len(gdf) + 1)
    print("形状个数：",len(gdf))
    print("形状具有以下属性:",gdf.columns,)
    return gdf
# 邻接边法
def contiguityEdgesOnly(gdf_polygon,gdf_id,is_std=True,ignored_attributes=None,ignored_values=None):
    """
    计算权重的方法，相当于Arcgis里的CONTIGUITY_EDGES_ONLY，与多边形邻接则权重置为1，否则为0，邻接的判定标准使用shapely的intersects方法，点接触，边接触，有重叠区域均算邻接
    Args:
        gdf_polygon:包含面数据的gdf类型，可以从getPolygonFromShpFile获取，并确保有相应的研究属性
        gdf_id:可以标识一个面的属性字段，如果例如行政区的名字（推荐），如果没有，使用getPolygonFromShpFile生成的id也行
        is_std=True:是否对返回的权重矩阵进行标准化，若为真则将该位置的权重除以该行的权重和
        ignored_attributes=None:和ignored_values配合使用，用于忽略缺失值，为具有缺失值的属性名，可为列表，例如["name","GDP"]
        ignored_values=None:具体忽略值，若忽略属性具有该值，则该多边形不被放入分析，可为列表，但需要和ignored_attributes保持一致，例如[["香港特别行政区","澳门特别行政区","台湾省"],[0]]，注意一定要列表里套列表！分别对应忽略属性里的["name","GDP"]（例如港澳台无统计数据，GDP为0显然为异常值）
    Returns:
        返回权重矩阵和每一行对应的标识符（gdfid）,n×n的numpy类型，权重矩阵里的顺序和gdf_polygon多边形的出现顺序一一对应，
        例如权重矩阵为:
                [[0,1],
                [1,0]]
        唯一标识符为:
                ["江西省","广东省"]

    """
    
    if ignored_attributes and ignored_values: # 如果有需要忽略的值
        for i,attribute in enumerate(ignored_attributes):
            index_to_drop=gdf_polygon[gdf_polygon[attribute].isin(ignored_values[i])].index # 找到需要忽略的索引
            gdf_polygon=gdf_polygon.drop(index_to_drop).reset_index(drop=True) # 要重置索引不然混乱！
    polygons=list(gdf_polygon.geometry) # 将gdf的类型提取为shapely的Polygon类型 
    ids=gdf_polygon[gdf_id].tolist()    #每个面元素的唯一标识符


    # 权重矩阵的核心计算代码
    n=len(polygons)
    W=np.zeros((n, n))
    for i in tqdm(range(n),desc="计算权重矩阵"):
        for j in range(n):
            if i != j and polygons[i].intersects(polygons[j]):
                W[i, j] = 1
    # 标准化
    if is_std:
        row_sums = W.sum(axis=1, keepdims=True)
        row_sums[row_sums== 0] = 1  # 避免除0（孤立的多边形）
        W = W / row_sums  # 行标准化

    return W,ids

# 距离倒数法
def inverseDistance(gdf_polygon,gdf_id,is_std=True,ignored_attributes=None,ignored_values=None,power=1):
    """
    计算权重的方法，相当于Arcgis里的INVERSE_DISTANCE，距离计算的基于每个面元素的中心点距离
    Args:
        gdf_polygon:包含面数据的gdf类型，可以从getPolygonFromShpFile获取，并确保有相应的研究属性
        gdf_id:可以标识一个面的属性字段，如果例如行政区的名字（推荐），如果没有，使用getPolygonFromShpFile生成的id也行
        is_std=True:是否对返回的权重矩阵进行标准化，若为真则将该位置的权重除以该行的权重和
        ignored_attributes=None:和ignored_values配合使用，用于忽略缺失值，为具有缺失值的属性名，可为列表，例如["name","GDP"]
        ignored_values=None:具体忽略值，若忽略属性具有该值，则该多边形不被放入分析，可为列表，但需要和ignored_attributes保持一致，例如[["香港特别行政区","澳门特别行政区","台湾省"],[0]]，注意一定要列表里套列表！分别对应忽略属性里的["name","GDP"]（例如港澳台无统计数据，GDP为0显然为异常值）
        power=1:衰减系数，具体用在权重的计算上，即：w=1/(d^power)
    Returns:
        返回权重矩阵和每一行对应的标识符（gdfid）,n×n的numpy类型，权重矩阵里的顺序和gdf_polygon多边形的出现顺序一一对应，
        例如权重矩阵为:
                [[0,1],
                [1,0]]
        唯一标识符为:
                ["江西省","广东省"]

    """
    
    if ignored_attributes and ignored_values: # 如果有需要忽略的值
        for i,attribute in enumerate(ignored_attributes):
            index_to_drop=gdf_polygon[gdf_polygon[attribute].isin(ignored_values[i])].index # 找到需要忽略的索引
            gdf_polygon=gdf_polygon.drop(index_to_drop).reset_index(drop=True) # 要重置索引不然混乱！
    
    print("提取面的中心...")
    centroids=gdf_polygon.geometry.centroid # 提取每个面元素的中心点

    ids=gdf_polygon[gdf_id].tolist()    #每个面元素的唯一标识符

    # 权重矩阵的核心计算代码
    n=len(centroids)
    W=np.zeros((n, n))
    for i in tqdm(range(n),desc="计算权重矩阵"):
        for j in range(n):
            if i!=j:
                distance=centroids[i].distance(centroids[j])   # 计算两个面的中心点距离
                W[i,j]=1.0/(distance+1e-6)**power # 加微小量防止除0
    # 标准化
    if is_std:
        row_sums=W.sum(axis=1, keepdims=True)
        row_sums[row_sums==0]=1  # 避免除0（孤立的多边形）
        W=W/row_sums  # 行标准化


    return W,ids

# 固定距离带
def fixedDistanceBand(gdf_polygon,gdf_id,distance_threshold,is_std=True,ignored_attributes=None,ignored_values=None):
    """
    计算权重的方法，相当于Arcgis里的FIXED_DISTANCE_BAND。在指定临界距离（距离范围或距离阈值）内的邻近要素将分配有值为 1 的权重，在指定临界距离外的邻近要素将分配值为0的权重。距离计算的基于每个面元素的中心点距离
    Args:
        gdf_polygon:包含面数据的gdf类型，可以从getPolygonFromShpFile获取，并确保有相应的研究属性
        gdf_id:可以标识一个面的属性字段，如果例如行政区的名字（推荐），如果没有，使用getPolygonFromShpFile生成的id也行
        distance_threshold:距离阈值
        is_std=True:是否对返回的权重矩阵进行标准化，若为真则将该位置的权重除以该行的权重和
        ignored_attributes=None:和ignored_values配合使用，用于忽略缺失值，为具有缺失值的属性名，可为列表，例如["name","GDP"]
        ignored_values=None:具体忽略值，若忽略属性具有该值，则该多边形不被放入分析，可为列表，但需要和ignored_attributes保持一致，例如[["香港特别行政区","澳门特别行政区","台湾省"],[0]]，注意一定要列表里套列表！分别对应忽略属性里的["name","GDP"]（例如港澳台无统计数据，GDP为0显然为异常值）
    Returns:
        返回权重矩阵和每一行对应的标识符（gdfid）,n×n的numpy类型，权重矩阵里的顺序和gdf_polygon多边形的出现顺序一一对应，
        例如权重矩阵为:
                [[0,1],
                [1,0]]
        唯一标识符为:
                ["江西省","广东省"]

    """
    
    if ignored_attributes and ignored_values: # 如果有需要忽略的值
        for i,attribute in enumerate(ignored_attributes):
            index_to_drop=gdf_polygon[gdf_polygon[attribute].isin(ignored_values[i])].index # 找到需要忽略的索引
            gdf_polygon=gdf_polygon.drop(index_to_drop).reset_index(drop=True) # 要重置索引不然混乱！
    
    print("提取面的中心...")
    centroids=gdf_polygon.geometry.centroid # 提取每个面元素的中心点

    ids=gdf_polygon[gdf_id].tolist()    #每个面元素的唯一标识符

    # 权重矩阵的核心计算代码
    n=len(centroids)
    W=np.zeros((n, n))
    for i in tqdm(range(n),desc="计算权重矩阵"):
        for j in range(n):
            if i!=j:
                distance=centroids[i].distance(centroids[j])   # 计算两个面的中心点距离
                if distance<distance_threshold:
                    W[i,j]=1
    # 标准化
    if is_std:
        row_sums=W.sum(axis=1, keepdims=True)
        row_sums[row_sums==0]=1  # 避免除0（孤立的多边形）
        W=W/row_sums  # 行标准化


    return W,ids

# 只计算莫兰指数
def calLocalMoran(gdf_polygon,gdf_id,W,study_attribute):
    """
    用于计算某一地图的局部莫兰指数值，不包含假设检验
    Args:
        gdf_polygon:gdf类型地图数据，若有忽略值，应为删除忽略值后的gdf数据，引入这个是为了删除缺失值后仍然能找到指数值和面的对应关系
        W:权重矩阵
        gdf_id:可以唯一标识一个面的id属性名称，例如生成的gdf_id
        study_attribute:字符串类型，研究的属性名，例如："GDP"，研究属性下的具体数值必须为数值型
    Returns:
        莫兰指数值列表，以及id列表，用于标识每一个莫兰指数值对应的面id
    """
    ids=gdf_polygon[gdf_id]

    study_values=gdf_polygon[study_attribute].to_numpy() # 研究属性的具体值
    mean_study_values=np.mean(study_values) # 所有属性的均值
    # var_study_values=np.var(study_values,ddof=1) # 采用无偏估计
    n=len(study_values) # 研究属性的个数
    S2=np.zeros_like(ids) # 属性值的方差的变种，对应公式里的S²
    w_x=np.zeros_like(ids) # 对应公式里最大的那一坨，计算方法为：∑W[i,j]*(x_j-mean)
    for i in range(n):
        for j in range(n):
            if i!=j:
                S2[i]=S2[i]+(study_values[j]-mean_study_values)
                w_x[i]=w_x[i]+W[i][j]*(study_values[j]-mean_study_values)**2
        S2=S2/(n-1) # np自带广播机制
    I=(study_values-mean_study_values)/S2*w_x   # 这里是矩阵运算直接得到矩阵

    return I,ids

# 全量的莫兰指数计算
def localMoran(gdf_polygon,gdf_id,distance_threshold,is_std=True,ignored_attributes=None,ignored_values=None):
    """
    计算权重的方法，相当于Arcgis里的FIXED_DISTANCE_BAND。在指定临界距离（距离范围或距离阈值）内的邻近要素将分配有值为 1 的权重，在指定临界距离外的邻近要素将分配值为0的权重。距离计算的基于每个面元素的中心点距离
    Args:
        gdf_polygon:包含面数据的gdf类型，可以从getPolygonFromShpFile获取，并确保有相应的研究属性
        gdf_id:可以标识一个面的属性字段，如果例如行政区的名字（推荐），如果没有，使用getPolygonFromShpFile生成的id也行
        distance_threshold:距离阈值
        is_std=True:是否对返回的权重矩阵进行标准化，若为真则将该位置的权重除以该行的权重和
        ignored_attributes=None:和ignored_values配合使用，用于忽略缺失值，为具有缺失值的属性名，可为列表，例如["name","GDP"]
        ignored_values=None:具体忽略值，若忽略属性具有该值，则该多边形不被放入分析，可为列表，但需要和ignored_attributes保持一致，例如[["香港特别行政区","澳门特别行政区","台湾省"],[0]]，注意一定要列表里套列表！分别对应忽略属性里的["name","GDP"]（例如港澳台无统计数据，GDP为0显然为异常值）
    Returns:
        返回权重矩阵和每一行对应的标识符（gdfid）,n×n的numpy类型，权重矩阵里的顺序和gdf_polygon多边形的出现顺序一一对应，
        例如权重矩阵为:
                [[0,1],
                [1,0]]
        唯一标识符为:
                ["江西省","广东省"]

    """
    






if __name__=="__main__":
    """
    调试小技巧：
    由于vscode的运行环境是处于根目录，所以这里提供相对路径反而会有运行错误
    若希望使用相对路径建议先先加上以下代码查看当前工作文件夹地址
    >>import os
    >>print(os.getcwd())
    然后在根据当前相对地址修改相对路径
    如果不考虑迁移，优先选择绝对地址
    """
    # import os
    # print(os.getcwd())
    gdf=getPolygonFromShpFile(r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\实习三\data\China.shp")

    W,ids=fixedDistanceBand(
        gdf_polygon=gdf,                            # 研究的面
        gdf_id="NAME",                              # 标识每一面的属性名称
        distance_threshold=500000,
        is_std=True,                                # 是否标准化
        ignored_attributes=["NAME"],                # 有忽略值的属性
        ignored_values=[["香港","澳门","台湾"]] ,     # 具体的忽略值，一定要列表里套列表！
    )
    print(W,W.shape)
    print(ids)
    
    # print(list(gdf))

    # # 提取 Shapely Polygon


    # print("空间权重矩阵（标准化后）:")
    # print(W_std)