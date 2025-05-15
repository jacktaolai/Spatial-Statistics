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
![银行最远距离34000步长300](assets\银行rmax34000_stepsize300.png)花时1分钟
![银行最远距离34000步长1](assets\银行rmax34000_stepsize1.png)花时三小时
从结果上来看好像这个函数对步长不是很敏感
加上置信度功能
![银行rmax34000_stepsize500](assets\银行rmax34000_stepsize500.png)
若加上Πr**2的曲线可以发现，模拟出来的置信度还是比理论值略小的，这说明了没有纠正时整体计算出来的值会较小
![arcgis]
![argis计算置信度](assets\arcgis_置信度.png)

![使用none模式](assets\银行rmax34000_stepsize500_studyareaNone.png)
使用点的外接矩形模式反而模拟值比理论值偏大,因为这个理论值计算出来的是假想一个无限大平面上生成随机点，而我设置的函数随机点在为在矩形范围内，相当于所有随机点都在外接矩形外，而不是无限平面内

