utils里提供更具关键词从百度地图提供的api获取关键词的地点，坐标为百度加密坐标，可近似看为WGS坐标，首先将地理坐标转换为投影坐标
请确保你安装了requests
pip install requests

使用了开源工具从高德获取数据：https://github.com/liujiao111/poi
武汉的数据由wgs转为cgcs2000 114E

$
\hat{K}(r) = \frac{|A|}{n(n-1)} \sum_{i=1}^{n} \sum_{j \neq i} I(d_{ij} \leq r) \cdot w_{ij}
$
为更直观展示，常使用L函数：
$$
L(r) = \sqrt{\frac{K(r)}{\pi}} - r
$$
但是arcgis实际使用的是
$$
L(r) = \sqrt{\frac{K(r)}{\pi}}
$$
本项目和arcgis保持一致
![arcgis的K函数计算结果](assets\arcgis的K函数计算结果.png)
![银行最远距离6000步长30](assets\银行rmax6000_stepsize30.png)

![alt text](image.png)