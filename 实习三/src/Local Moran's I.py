import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
import pandas as pd
from tqdm import tqdm 
import pandas as pd
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
    
    print("形状个数：",len(gdf))
    print("形状具有以下属性:",gdf.columns,)
    return gdf

# 删除有忽略值的元素
def dropIgnoredValues(gdf_polygon,ignored_attributes=None,ignored_values=None):
    """
    Args:
        gdf_polygon:包含面数据的gdf类型，可以从getPolygonFromShpFile获取，并确保有相应的研究属性
        ignored_attributes=None:和ignored_values配合使用，用于忽略缺失值，为具有缺失值的属性名，可为列表，例如["name","GDP"]
        ignored_values=None:具体忽略值，若忽略属性具有该值，则该多边形不被放入分析，可为列表，但需要和ignored_attributes保持一致，例如[["香港特别行政区","澳门特别行政区","台湾省"],[0]]，注意一定要列表里套列表！分别对应忽略属性里的["name","GDP"]（例如港澳台无统计数据，GDP为0显然为异常值）
    returns
        删除后的新gdf地图数据
    """
    for i,attribute in enumerate(ignored_attributes):
        index_to_drop=gdf_polygon[gdf_polygon[attribute].isin(ignored_values[i])].index # 找到需要忽略的索引
        gdf_polygon=gdf_polygon.drop(index_to_drop).reset_index(drop=True) # 要重置索引不然混乱！
    return gdf_polygon

# 邻接边法
def contiguityEdgesOnly(gdf_polygon,is_std=True,gdf_id=None,ignored_attributes=None,ignored_values=None):
    """
    计算权重的方法，相当于Arcgis里的CONTIGUITY_EDGES_ONLY，与多边形邻接则权重置为1，否则为0，邻接的判定标准使用shapely的intersects方法，点接触，边接触，有重叠区域均算邻接
    Args:
        gdf_polygon:包含面数据的gdf类型，可以从getPolygonFromShpFile获取，并确保有相应的研究属性
        is_std=True:是否对返回的权重矩阵进行标准化，若为真则将该位置的权重除以该行的权重和
        gdf_id=None:可以标识一个面的属性字段，如果例如行政区的名字（推荐），如果没有，使用getPolygonFromShpFile生成的gdf_id也行,若为None,则返回的唯一标识符ids也为None
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
        gdf_polygon=dropIgnoredValues(gdf_polygon,ignored_attributes,ignored_values)

    polygons=list(gdf_polygon.geometry) # 将gdf的类型提取为shapely的Polygon类型
    if gdf_id is None:
        ids=None
    else: 
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
def inverseDistance(gdf_polygon,is_std=True,gdf_id=None,ignored_attributes=None,ignored_values=None,power=1):
    """
    计算权重的方法，相当于Arcgis里的INVERSE_DISTANCE，距离计算的基于每个面元素的中心点距离
    Args:
        gdf_polygon:包含面数据的gdf类型，可以从getPolygonFromShpFile获取，并确保有相应的研究属性
        is_std=True:是否对返回的权重矩阵进行标准化，若为真则将该位置的权重除以该行的权重和
        gdf_id=None:可以标识一个面的属性字段，如果例如行政区的名字（推荐），如果没有，使用getPolygonFromShpFile生成的gdf_id也行,若为None,则返回的唯一标识符ids也为None
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
        gdf_polygon=dropIgnoredValues(gdf_polygon,ignored_attributes,ignored_values)
          
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
def fixedDistanceBand(gdf_polygon,distance_threshold,is_std=True,gdf_id=None,ignored_attributes=None,ignored_values=None):
    """
    计算权重的方法，相当于Arcgis里的FIXED_DISTANCE_BAND。在指定临界距离（距离范围或距离阈值）内的邻近要素将分配有值为 1 的权重，在指定临界距离外的邻近要素将分配值为0的权重。距离计算的基于每个面元素的中心点距离
    Args:
        gdf_polygon:包含面数据的gdf类型，可以从getPolygonFromShpFile获取，并确保有相应的研究属性
        distance_threshold:距离阈值
        is_std=True:是否对返回的权重矩阵进行标准化，若为真则将该位置的权重除以该行的权重和
        gdf_id=None:可以标识一个面的属性字段，如果例如行政区的名字（推荐），如果没有，使用getPolygonFromShpFile生成的gdf_id也行,若为None,则返回的唯一标识符ids也为None
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
        gdf_polygon=dropIgnoredValues(gdf_polygon,ignored_attributes,ignored_values)
        
    
    print("提取面的中心...")
    centroids=gdf_polygon.geometry.centroid # 提取每个面元素的中心点
    if gdf_id is None:
        ids=None
    else:
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
def calLocalMoran(gdf_polygon,W,study_attribute,study_values:np=None,gdf_id=None):
    """
    用于计算某一地图的局部莫兰指数值，不包含假设检验
    Args:
        gdf_polygon:gdf类型地图数据，若有忽略值，应为删除忽略值后的gdf数据，引入这个是为了删除缺失值后仍然能找到指数值和面的对应关系
        W:权重矩阵
        study_attribute:字符串类型，研究的属性名，例如："GDP"，研究属性下的具体数值必须为数值型
        study_values:np类型列表，包含所有研究属性的具体研究值，若未传入则从gdf里获取,设置该参数主要是为了方便不哥哥gdf还能计算指数
        gdf_id:可以唯一标识一个面的id属性名称，例如生成的gdf_id,若为None则返回的id也为空

    Returns:
        莫兰指数值列表，以及id列表，用于标识每一个莫兰指数值对应的面id
    """
    if gdf_id is None:
        ids=None
    else:
        ids=gdf_polygon[gdf_id]
    if study_values is None:
        study_values=gdf_polygon[study_attribute].to_numpy() # 研究属性的具体值
    mean_study_values=np.mean(study_values) # 所有属性的均值
    # var_study_values=np.var(study_values,ddof=1) # 采用无偏估计
    n=len(study_values) # 研究属性的个数
    S2=np.zeros_like(study_values) # 属性值的方差的变种，对应公式里的S²
    w_x=np.zeros_like(study_values) # 对应公式里最大的那一坨，计算方法为：∑W[i,j]*(x_j-mean)
    for i in range(n):
        for j in range(n):
            if i!=j:
                S2[i]=S2[i]+(study_values[j]-mean_study_values)**2
                w_x[i]=w_x[i]+W[i][j]*(study_values[j]-mean_study_values)
    S2=S2/(n-1) # np自带广播机制
    I=(study_values-mean_study_values)/S2*w_x   # 这里是矩阵运算直接得到矩阵

    return I,ids
# 计算邻居研究属性的平均值
def calNeighbor_mean(gdf_polygon,study_attribute):
    """
    计算邻居研究属性的平均值,目的是用于后续判断高低异常还是低高异常或者是高高聚类还是低高聚类
    Args:
        gdf_polygon:包含面的gdf数据
        study_attribute:研究的属性
    Returns:
        返回平均值的列表
    """
    neighbor_means=np.zeros(len(gdf_polygon))

    # 遍历每一个面
    for i in range(len(gdf_polygon)):
        current_polygon=gdf_polygon.geometry.iloc[i]    # 取出第i个面
        neighbor_values=[]
        for j in range(len(gdf_polygon)):
            if i!=j and current_polygon.intersects(gdf_polygon.geometry.iloc[j]):
                neighbor_values.append(gdf_polygon[study_attribute].iloc[j])    #将邻居的研究属性加进去
                    # 计算邻域均值（如果有邻接面）
        if neighbor_values: # 如果有邻接面计算平均值
            neighbor_means[i] = np.mean(neighbor_values)
    return neighbor_means


# 全量的莫兰指数计算
def localMoran(gdf_polygon,study_attribute,mode="inverseDistance",W=None,is_std=True,distance_threshold=None,n_simulations=99,p_threshold=0.3,
ignored_attributes=None,ignored_values=None,is_plot=True,gdf_background=None,saved_shp_path=None):
    """
    全参数量的莫兰指数计算，可生成制图，mode为权重的计算方法，有"contiguityEdgesOnly","contiguityEdgesOnly","fixedDistanceBand"(需传入距离阈值)三种方法可选
    Args:
        gdf_polygon:包含面数据的gdf类型，可以从getPolygonFromShpFile获取，并确保有相应的研究属性
        study_attribute:研究的属性名，为字符串，如"GDP"
        mode="inverseDistance":mode为权重的计算方法，有"contiguityEdgesOnly","inverseDistance","fixedDistanceBand"(需传入距离阈值distance_threshold)三种方法可选,具体计算方法见三个同名函数
        distance_threshold:距离阈值
        W:权重矩阵，若传入权重矩阵，优先使用权重矩阵（不建议使用，除非你明确知道权重和研究的属性顺序是一一对应的）
        is_std=True:若使用模式计算权重矩阵，对权重矩阵是否标准化
        n_simulations=99:模拟的次数，默认999次
        p_threshold=0.05:置信度阈值，小于该值才会被判断为异常，建议调整
        is_plot=True:是否绘制地图
        gdf_background=None:若开启绘制地图，还可以传入底图（例如中国地图你还可以传入九段线）
        ignored_attributes=None:和ignored_values配合使用，用于忽略缺失值，为具有缺失值的属性名，可为列表，例如["name","GDP"]
        ignored_values=None:具体忽略值，若忽略属性具有该值，则该多边形不被放入分析，可为列表，但需要和ignored_attributes保持一致，例如[["香港特别行政区","澳门特别行政区","台湾省"],[0]]，注意一定要列表里套列表！分别对应忽略属性里的["name","GDP"]（例如港澳台无统计数据，GDP为0显然为异常值）
        saved_shp_path=None:存储为shp的地址，若为None则不储存
    Returns:
        返回gdf类型，增加了莫兰指数I，z得分，和p值
    """
    # 添加gdfid保证删除元素后也能找到对应的面
    gdf["gdf_id"] = range(1, len(gdf) + 1)

    if ignored_attributes and ignored_values: # 如果有需要忽略的值
        new_gdf_polygon=dropIgnoredValues(gdf_polygon,ignored_attributes,ignored_values)
    if W is None:
        if mode=="contiguityEdgesOnly":
            W,ids=contiguityEdgesOnly(gdf_polygon=new_gdf_polygon,  # 研究的地图
                                  is_std=is_std,                    # 权重矩阵是否标准化
                                  gdf_id="gdf_id"                   # 每个面的唯一标识符
                                  )
        elif mode=="inverseDistance":
            W,ids=inverseDistance(gdf_polygon=new_gdf_polygon,  # 研究的地图
                        is_std=is_std,                    # 权重矩阵是否标准化
                        gdf_id="gdf_id"                   # 每个面的唯一标识符
                        )
        elif mode=="fixedDistanceBand":
            W,ids=fixedDistanceBand(gdf_polygon=new_gdf_polygon,  # 研究的地图
                        distance_threshold=distance_threshold, # 距离阈值
                        is_std=is_std,                    # 权重矩阵是否标准化
                        gdf_id="gdf_id"                   # 每个面的唯一标识符
                        )
        else:
            raise ValueError("未定义该模式")
        
    # 计算局部莫兰指数
    local_mroan_Is,ids=calLocalMoran(new_gdf_polygon,W,study_attribute,gdf_id="gdf_id")
    
    study_values=new_gdf_polygon[study_attribute].to_numpy().copy() # 研究属性的具体值
    study_values_copy=study_values.copy()
    sim_local_mroan_Is=[]
    for i in tqdm(range(n_simulations),desc="模拟过程:"):
        np.random.shuffle(study_values_copy) # 随机打乱数据进行蒙特卡洛实验
        sim_mroan_I,_=calLocalMoran(new_gdf_polygon,W,study_attribute,study_values=study_values_copy,gdf_id="gdf_id")
        sim_local_mroan_Is.append(sim_mroan_I)

    sim_local_mroan_Is=np.array(sim_local_mroan_Is) # 转为np方便切片
    # 计算p值
    p_values=np.zeros_like(local_mroan_Is)
    for i,I in enumerate(local_mroan_Is):
        if I>0: # 若局部莫兰值大于0，计算比他大的个数
            p_values[i]=(np.sum(sim_local_mroan_Is[:,i]>=I))/n_simulations # 这里很巧妙地用了切片将列提取出来，并用广播机制和参数比较，得到0，1矩阵
        else: # 若局部莫兰值小于0，计算比他小的个数
            p_values[i]=(np.sum(sim_local_mroan_Is[:,i]<=I))/n_simulations

    mean_sim_Is=np.mean(sim_local_mroan_Is,axis=0)
    std_sim_Is=np.std(sim_local_mroan_Is,axis=0,ddof=1) # 采用无偏估计的标准差
    z_scores=(local_mroan_Is-mean_sim_Is)/std_sim_Is # z得分

    # 计算邻居的平均值（用于判断异常类型）
    neighbor_means=calNeighbor_mean(new_gdf_polygon,study_attribute)
    # 计算全局的平均值（用于判断异常类型）
    study_values_mean=np.mean(study_values)

    # 将模式分类
    pattern_labels=[]
    for i in range(len(local_mroan_Is)):
        if p_values[i]>=p_threshold:
            pattern_labels.append("Not significant")
        else:
            if local_mroan_Is[i]>0:
                if study_values[i]>study_values_mean:
                    pattern_labels.append('HH')
                elif study_values[i]<study_values_mean:
                    pattern_labels.append('LL')
                else:
                    pattern_labels.append("Not significant")
            else:
                if study_values[i]>neighbor_means[i]:
                    pattern_labels.append('HL')
                elif study_values[i]<neighbor_means[i]:
                    pattern_labels.append('LH')
                else:
                    pattern_labels.append("Not significant")


    # 将莫兰指数p、z得分合并到地图中
    moran_df=pd.DataFrame({
        "gdf_id":ids,                       # 唯一标识符
        "local_moran_I":local_mroan_Is,     # 局部莫兰值
        "p_values":p_values,                # p值
        "z_scores":z_scores,                # z得分
        "neighbor_mean":neighbor_means,     # 邻居的研究属性平均值
        "pattern":pattern_labels            # 模式名
        })
    gdf_polygon=gdf_polygon.merge(
        moran_df,
        on="gdf_id",
        how="left"
    )
    gdf_polygon['plot_pattern'] = gdf_polygon['pattern'].fillna('No Data')

    # 保存shp文件
    if saved_shp_path is not None:
        gdf_polygon.to_file(saved_shp_path,encoding="utf-8")

    # 绘图
    if is_plot:
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        # Define color mapping
        cmap = ListedColormap([
            'red',        # HH (Hot spot)
            'blue',       # LL (Cold spot)
            'pink',       # HL (High-Low outlier)
            'lightblue',  # LH (Low-High outlier)
            'lightgrey',  # Not significant
            'grey'        # No Data
        ])

        fig, ax = plt.subplots(figsize=(12, 8))
        # 加载数据（确保是线状数据）
        gdf_background = getPolygonFromShpFile(r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\实习三\data\China_line.shp")
        print(gdf_background.geometry.type)  # 确认是否为 LineString/MultiLineString
        # 定义颜色映射（LISA分类）
        cmap = ListedColormap(['red', 'blue', 'pink', 'lightblue', 'lightgrey', 'grey'])
        # 绘图
        if is_plot:
            # 1. 先绘制线状底图（黑色边界线）
            gdf_background.plot(
                ax=ax,
                edgecolor='black',  # 线颜色
                linewidth=0.5,      # 线宽
                facecolor='none'    # 无填充
            )
            # 2. 再绘制主图（LISA分类）
            gdf_polygon.plot(
                ax=ax,
                column='plot_pattern',
                categorical=True,
                cmap=cmap,
                legend=True,
                legend_kwds={'title': 'Clusters Outliers', 'loc': 'lower left'},
                alpha=0.7  # 半透明，避免完全遮盖底图
            )
            plt.title('Local Moran\'s Clusters Outliers Map')
            plt.show()

    return new_gdf_polygon
        


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
    print(gdf)
    gdf_background=getPolygonFromShpFile(r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\实习三\data\China_line.shp")
    #saved_shp_path=r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\temp\实习三\result\inverseDistance_stdrow_python_p3.shp"  
    saved_shp_path=None   

    
    print(gdf_background)
    localMoran(
        gdf_polygon=gdf,            # 研究的面
        study_attribute="受教育",   # 研究的属性名
        mode="inverseDistance",     # 权重矩阵的计算模式"inverseDistance""contiguityEdgesOnly""fixedDistanceBand"
        distance_threshold=1000000,      # 距离阈值
        is_std=True,                  # 是否对权重矩阵标准化
        W=None,                       # 权重矩阵（不传入，函数内计算）
        p_threshold=0.25,                            # p阈值（建议填大一点）
        n_simulations=999,                          # 模拟的次数
        saved_shp_path=saved_shp_path,               # 分析结果shpfile保存地址，不需要该功能填None
        ignored_attributes=["NAME"],                # 有忽略值的属性
        ignored_values=[["香港","澳门","台湾"]] ,     # 具体的忽略值，一定要列表里套列表！
        gdf_background=gdf_background               # 背景元素，提供十段线等，没有就填None
        )
    
