## K函数（Ripley’s K Function）与L函数分析工具

### K函数说明
K函数（Ripley’K Function）可用于研究不同模式下空间尺度的点分布规律，计算方法是：
$$
\hat{K}(r) = \frac{|A|}{n(n-1)} \sum_{i=1}^{n} \sum_{j \neq i} I(d_{ij} \leq r) 
$$
为更直观展示，常使用L函数：
$$
L(r) = \sqrt{\frac{K(r)}{\pi}} - r
$$
但是Arcgis实际使用的是
$$
L(r) = \sqrt{\frac{K(r)}{\pi}}
$$
本项目实现了以上三种函数的计算以及可视化制图。

---
### 函数说明

#### `KFunction`

* **作用**：完整的 K 函数计算，包括多种参数可以选择
* **使用提示**：
    * 可通过设置 `getPointsCoordinates` 中的 `is_plot=True` 来可视化研究点的分布，并判断是否为经纬度坐标（一般若使用地理坐标系横坐标落在 0-180 区间）。
    * `point_list`可通过 `getPointsCoordinates()` 获取

#### ⚠ 使用注意

> 请确保输入的研究点和研究区域（如果有）为 **投影坐标系**！项目不设自动检测机制，经纬度输入会导致计算错误！

#### `LFunction` 和 `ArcgisLFunction`

* **作用**：分别实现两种形式的 L 函数计算
* **要求**：传入已计算出的 K 函数值（请先运行 `KFunction`）

---

### 依赖库安装

请确保已安装以下库：

```bash
pip install pyshp matplotlib numpy tqdm shapely
```

### 特性

* 多种参数，多种模式的选择
* 快捷的可视化
* 进度条的显示，让等待不那么焦急

---

### 实施例：以武汉市银行为例

* 数据来源：使用高德 API 抓取，工具见：[POI 抓取工具](https://github.com/liujiao111/poi)
* 投影方式：使用 ArcGIS 将 WGS84 坐标系转换为 **CGCS2000 东经114投影坐标系**

#### 与Arcgis分析工具对比

![](assets/arcgis的K函数计算结果.png)
图1: Arcgis K函数计算结果</em></p>

![](assets\arcgis_置信度.png)
图2: Arcgis 置信区间分析</em></p>
    
 ![](assets\银行最远距离34000步长300L函数.png)
 图3: ArcgisLFunction计算结果

>结论1：和arcgis的结果无明显差异，公式的正确性以及代码实施的准确性。此外，设置Arcgis的步数为100，Arcgis不加缓冲区大约需要3分钟，加入缓冲区为5小时。代码运行时间为1分钟，说明程序运算时间上的优越性。

#### 不同步长的设置结果

![](assets\武汉银行最大距离34000步长500.png)
图4: 步长500m计算结果

![](assets\银行rmax34000_stepsize1.png)
图5: 步长1m计算结果


>结论2：步长为500m的计算使用越1分钟，步长为1m的使用3小时，可以看出，步长会极大地影响代码的运行时间，但是从结果上来看这个函数对步长不是很敏感，因此可以一定程度地选择大步长

#### 边界效应的影响

![](assets\银行rmax34000_stepsize500.png)
图6: 加入95%的置信度

>结论3：加上置信度功能，若加上理论值πr²的曲线可以发现，模拟出来的置信度还是比理论值略小的，这说明了没有边界纠正整体计算出来的值会较小


![](assets\银行rmax34000_stepsize500_studyareaNone.png)
图7：使用外接矩形计算K函数值与置信度

>结论4：若不传入研究区域，程序功能也正常，能自动使用点的外接矩形就行计算，但该模式反而模拟值比理论值偏大（后续增加实验也发现有比其小的情况）,我的解释是理论值计算出来的是假想一个无限大平面上生成随机点，而我设置的函数随机点在为在矩形范围内，相当于所有随机点都在外接矩形外，而不是无限平面内

![alt text](assets\武汉银行35000步长300L函数.png)
图8 L函数的计算结果
>结论5：从L函数小于0来看就可以看出为加边界借助功能会使得计算结果偏小，另外L函数总体大于0，说明在研究范围内，武汉银行的点分布模式为聚集模式，且在距离达到16000m的时候聚集程度最大

---

### 致谢
本项目直接依赖以下开源工具：

- **[PyShp](https://github.com/GeospatialPython/pyshp)** - Shapefile文件读写
- **[Shapely](https://shapely.readthedocs.io/)** - 空间几何计算（多边形面积/随机点生成）
- **[NumPy](https://numpy.org/)** - 距离矩阵和数值计算
- **[Matplotlib](https://matplotlib.org/)** - 结果可视化
- **[tqdm](https://github.com/tqdm/tqdm)** - 计算进度显示

特别感谢：
- **[高德地图API](https://lbs.amap.com/)** - 提供原始POI数据
- **[开源POI抓取工具](https://github.com/liujiao111/poi)** - 使用API获取POI 

---

<div align="center">
  <span style="font-size: 2em;">🌌</span>
  <br>
  <b>如引用本项目，您就是我们的同星者</b>
  <br>
  <i>—— 数据如星尘，算法似银河 ——</i>
</div>

---
