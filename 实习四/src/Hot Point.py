import geopandas as gpd
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
from tqdm import tqdm
import math
import numpy as np
from scipy.stats import norm  # 用于计算 p 值
import matplotlib.colors as mcolors
import pandas as pd




# 生成格网并统计每个格网里的点
def generateGridAndCountPoints(refrence_gdf_points,x_num=None,y_num=None,x_interval=None,y_interval=None,is_plot=False,saved_shp_path=None):
    """
    用于生成格网地图,并统计格网里的点的数量,格网类型为面类型,创建的格网一定能覆盖所有的点，尤其注意数量并非完全和指定的数量一样，若选用x_num和y_num方法，为覆盖所有点，会比目标数量多一到两行和一到两列
    Args:
        refrence_gdf_points:参考的点，若有则从此获取格网的范围，即左上和右下的点以及，crs坐标
        x_num=None:水平方向需要分成的格网
        y_num=None:垂直方向需要分成的格网
        x_interval:水平方向格网的距离,与x_num必须填一个，若都填，以x_num为准
        y_interval:垂直方向格网的距离,与y_num必须填一个，若都填，以y_num为准
        is_plot:是否绘图
        shaved_shp_path:shp文件保存地址
    Returns:
        放回格网的gdf类型，其中"num_pts"列存储了每个格子里有几个点
    """
    grid_cells=[] # 格网中的格子
    grid_crs=refrence_gdf_points.crs # 坐标系和参考店的坐标系保持一致
    minx,miny,maxx,maxy=refrence_gdf_points.total_bounds   #[minx,miny,maxx,maxy]

    if x_num is not None:
        x_interval=(maxx-minx)/x_num        
    if y_num is not None:
        y_interval=(maxy-miny)/y_num

    if (x_interval is None) or (y_interval is None): # 如果num和interval两个都没有填
        raise ValueError("分割间隔和分割数量至少填一个")
    # 为了让点不落在外边界上和覆盖所有点，将最大最小值扩大一圈
    padding=1e-6
    minx=minx-padding
    miny=miny-padding
    maxx=maxx+padding
    maxy=maxy+padding

    current_x=minx
    current_y=miny
    # 进度条
    x_num = math.ceil((maxx - minx) / x_interval)  # 向上取整确保数目绝对正确
    y_num = math.ceil((maxy - miny) / y_interval)
    for i in tqdm(range(y_num),desc="创建格网"):
        for j in range(x_num):
            cell_left=current_x # 格子的左边界
            cell_right=current_x+x_interval # 格子的右边界
            cell_down=current_y # 格子的下边界
            cell_up=current_y+y_interval # 格子的上边界
            # 顶点坐标，保持顺时针顺序
            coords=[(cell_left,cell_down),
                    (cell_left,cell_up),
                    (cell_right,cell_up),
                    (cell_right,cell_down)
                    ]
            grid_cells.append(Polygon(coords))
            current_x+=x_interval # 移动y

        current_y+=y_interval # 移动x
        current_x=minx # 重置y
    # 生成网格
    grid=gpd.GeoDataFrame({"geometry":grid_cells},crs=grid_crs)

    # 计算落在网格里的点
    grid["num_pts"]=0
    for point in tqdm(refrence_gdf_points.geometry,desc="统计格网点数量"):
        x=point.x
        y=point.y
        x_index=int((x-minx)/x_interval) # 网格的列号（左下角开始数）
        y_index=int((y-miny)/y_interval) # 网格的行号（左下角开始数）
        index=x_index+y_index*x_num
        grid.at[index,"num_pts"]+=1

    # 保存shp文件
    if saved_shp_path is not None:
        grid.to_file(saved_shp_path,encoding="utf-8")

    # 绘图
    if is_plot:
        fig, ax = plt.subplots(figsize=(12, 8))
        grid.plot(
            ax=ax,
            edgecolor='gray',
            facecolor='lightblue',
            alpha=0.6,
            legend=True,
        )
        refrence_gdf_points.plot(
            ax=ax,
            markersize=0.5
        )
        plt.title("Generated Grid")
        plt.show()

        # 按点数量绘制网格图
        fig2, ax2 = plt.subplots(figsize=(12, 8))
        grid.plot(
            ax=ax2,
            column="num_pts",
            cmap="OrRd",
            edgecolor="gray",
            legend=True,
            legend_kwds={"label": "Number of Points", "orientation": "vertical"}
        )
        refrence_gdf_points.plot(
            ax=ax2,
            markersize=0.5
        )
        plt.title("Grid Colored by Number of Points")
        plt.show()
        
    return grid
#-------权重矩阵计算 ，复用莫兰指数部分的计算方法---------

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

#-------权重矩阵计算结束---------

# G*指数的计算
def GStarLocal(gdf_polygons,study_attribute,mode="inverseDistance",W=None,is_std=True,distance_threshold=None,is_plot=True,saved_shp_path=None):
    """
    对面进行局部G指数的计算，可生成制图，mode为权重的计算方法，有"contiguityEdgesOnly","contiguityEdgesOnly","fixedDistanceBand"(需传入距离阈值)三种方法可选
    Args:
        gdf_polygons:需要分析的面，若为点可传入点个数的格网
        study_attribute:需要研究的属性，例如使用本项目生成的格网填"num_pts"
        mode="inverseDistance":mode为权重的计算方法，有"contiguityEdgesOnly","inverseDistance","fixedDistanceBand"(需传入距离阈值distance_threshold)三种方法可选,具体计算方法见三个同名函数
        distance_threshold:距离阈值
        W:权重矩阵，若传入权重矩阵，优先使用权重矩阵（不建议使用，除非你明确知道权重和研究的属性顺序是一一对应的）
        is_std=True:若使用模式计算权重矩阵，对权重矩阵是否标准化
        is_plot=True:是否绘制地图
        saved_shp_path=None:存储为shp的地址，若为None则不储存
    Returns:
        返回gdf类型，增加了G指数得分，列名为"GStar"
    """
    if W is None:
        if mode=="contiguityEdgesOnly":
            W,ids=contiguityEdgesOnly(gdf_polygon=gdf_polygons,  # 研究的地图
                                    is_std=is_std,                    # 权重矩阵是否标准化
                                    )
        elif mode=="inverseDistance":
            W,ids=inverseDistance(gdf_polygon=gdf_polygons,  # 研究的地图
                        is_std=is_std,                    # 权重矩阵是否标准化
                        )
        elif mode=="fixedDistanceBand":
            W,ids=fixedDistanceBand(gdf_polygon=gdf_polygons,  # 研究的地图
                        distance_threshold=distance_threshold, # 距离阈值
                        is_std=is_std,                    # 权重矩阵是否标准化
                        )
        else:
            raise ValueError("未定义该模式")
    
    study_values=gdf_polygons[study_attribute].to_numpy()  # 需要研究的属性
    mean_study_values=np.mean(study_values)
    n=len(study_values)
    s=np.sqrt(np.sum(study_values**2)/n-mean_study_values**2)   # s不可直接使用std，不是标准的标准差
    gdf_polygons["g_stars"]=0.0
    gdf_polygons["p_value"] = 0.0  # 新增 p 值列
    gdf_polygons["GiBin"] = "Not Significant"
    for i in tqdm(range(len(study_values)),desc="计算G指数"):
        g_numerator=np.sum(W[i,:]*study_values)-mean_study_values*np.sum(W[i,:]) # 分子
        g_denominator=s*np.sqrt((n*np.sum(W[i,:]**2)-(np.sum(W[i,:]))**2)/(n-1)) #分母
        g_star=g_numerator/g_denominator
        gdf_polygons.at[i,"g_stars"]=g_star # 将g值写入面属性
        # 计算 p 值（双侧检验）
        p_value = 2 * (1 - norm.cdf(abs(g_star)))  # 标准正态分布
        gdf_polygons.at[i, "p_value"] = p_value
        # 分类逻辑（基于 z 分数）
        if p_value <= 2.58:
            category = "HotSpot-99%Confidence"
        elif g_star >= 1.96:
            category = "HotSpot-95%Confidence"
        elif g_star >= 1.65:
            category = "HotSpot-90%Confidence"
        elif g_star <= -2.58:
            category = "Cold Spot-99%Confidence"
        elif g_star <= -1.96:
            category = "Cold Spot-95%Confidence"
        elif g_star <= -1.65:
            category = "Cold Spot-90% Confidence"
        else:
            category = "Not Significant"

        gdf_polygons.at[i, "GiBin"] = category

    
    if saved_shp_path is not None:
        gdf_polygons.to_file(saved_shp_path,encoding="utf-8")

    if is_plot:
        #fig,ax=plt.subplots(figsize=(10,8))

        # # 按G*值赋颜色
        # gdf_polygons.plot(
        #     column="p_value",   # G*所在列
        #     cmap="coolwarm",     # 红=热点，蓝=冷点
        #     ax=ax,
        #     edgecolor="gray",
        #     linewidth=0.5,
        #     legend=True

        # )
        # ax.set_title("Getis-Ord Gi* Hotspot Analysis")
        # plt.axis("off")
        # plt.show()
        # 设置类别及对应颜色
        category_colors = {
            "Cold Spot-99%Confidence": "#08306b",
            "Cold Spot-95%Confidence": "#2171b5",
            "Cold Spot-90% Confidence": "#6baed6",
            "Not Significant": "#f0f0f0",
            "HotSpot-90%Confidence": "#fcae91",
            "HotSpot-95%Confidence": "#fb6a4a",
            "HotSpot-99%Confidence": "#cb181d"
        }

        # 确保 GiBin 是分类型，便于保持图例顺序
        gdf_polygons["GiBin"] = pd.Categorical(
            gdf_polygons["GiBin"],
            categories=list(category_colors.keys()),
            ordered=True
        )

        # 画图
        fig, ax = plt.subplots(figsize=(12, 8))
        gdf_polygons.plot(
            column="GiBin",
            ax=ax,
            cmap=mcolors.ListedColormap([category_colors[k] for k in gdf_polygons["GiBin"].cat.categories]),
            edgecolor="gray",
            linewidth=0.5,
            legend=True,
            legend_kwds={'title': 'grid type', 'loc': 'lower right'},

        )
        ax.set_title("Getis-Ord Gi* Hotspot Analysis (Categorical)", fontsize=14)
        plt.axis("off")
        plt.show()

    return gdf_polygons
    






if __name__=="__main__":
    points_file_path=r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\实习四\data\Test4.shp"
    saved_shp_path=None
    saved_shp_path=r"D:\必须用电脑解决的作业\空间统计分析\Spatial Statistics\temp\实习四\result\grid1000m.shp"
    points=gpd.read_file(points_file_path)
    points.boundary
    print("投影为：",points.crs) # EPSG:4547对应的是CSGS114E
    print(points)
    pos=points.geometry.x

    print(pos)

    grid=generateGridAndCountPoints(refrence_gdf_points=points,
               # x_num=40,
               # y_num=40,
               x_interval=500,
               y_interval=500,
               is_plot=True,
               saved_shp_path=saved_shp_path
        )
    result_saved_path=None

    grid=GStarLocal(
        gdf_polygons=grid,                  # 要分析的面
        study_attribute="num_pts",          # 要研究的属性，使用本项目生成的格网填"num_pts"
        mode="contiguityEdgesOnly",             # 空间权重矩阵的计算方式"contiguityEdgesOnly""inverseDistance"
        distance_threshold=3000,             # 若使用fixedDistanceBand需要填这个
        is_plot=True,                       # 是否绘图
        saved_shp_path=None,#saved_shp_path,       # 分析结果的保存地址  
        is_std=False                       # 改变这个不影响结果

    )

    

