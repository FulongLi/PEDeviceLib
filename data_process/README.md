# Data Process - Figure Generation Module

## 功能说明

`figure_process.py` 模块用于从 JSON 格式的半导体器件数据生成可视化图表，为 PDF 数据表生成提供图片支持。

## 主要功能

### 1. 开关损耗曲线 (Turn-On/Turn-Off Loss)
- **Turn-On Loss**: 开关导通能量损耗曲线
- **Turn-Off Loss**: 开关关断能量损耗曲线
- 显示不同温度下的能量损耗特性
- 横轴：电流 (A)
- 纵轴：能量 (mJ)

### 2. 导通特性曲线 (Conduction Characteristics)
- 显示器件的 V-I 特性
- 不同温度下的电压-电流关系
- 支持正向和反向导通特性
- 横轴：电流 (A)
- 纵轴：电压降 (V)

### 3. 热阻抗曲线 (Thermal Impedance)
- 热阻抗随时间的变化曲线
- RC 网络结构可视化
- 总热阻值标注
- 左图：热阻抗 vs 时间（对数坐标）
- 右图：RC 网络结构

## 使用方法

### 单个文件处理

```python
from figure_process import generate_all_figures
import json

# 加载 JSON 数据
with open('standard_database/C2M0025120D.json', 'r') as f:
    json_data = json.load(f)

# 生成所有图表
figures = generate_all_figures(json_data, output_dir='figures')

# figures 字典包含：
# {
#     'turnon_loss': 'path/to/turnon_loss.png',
#     'turnoff_loss': 'path/to/turnoff_loss.png',
#     'conduction': 'path/to/conduction.png',
#     'thermal': 'path/to/thermal.png'
# }
```

### 批量处理

```bash
# 处理整个目录
python figure_process.py --input standard_database --output figures

# 处理单个文件
python figure_process.py --input standard_database/C2M0025120D.json --output figures
```

### 单独生成特定图表

```python
from figure_process import (
    plot_turnon_loss,
    plot_turnoff_loss,
    plot_conduction_characteristics,
    plot_thermal_impedance
)

# 生成开关损耗曲线
plot_turnon_loss(json_data, 'output/turnon.png')
plot_turnoff_loss(json_data, 'output/turnoff.png')

# 生成导通特性曲线
plot_conduction_characteristics(json_data, 'output/conduction.png')

# 生成热阻抗曲线
plot_thermal_impedance(json_data, 'output/thermal.png')
```

## 测试

运行测试脚本验证功能：

```bash
cd data_process
python test_figure_process.py
```

## 输出格式

- **格式**: PNG
- **分辨率**: 300 DPI（适合打印和 PDF 嵌入）
- **尺寸**: 
  - 单图：10×6 英寸
  - 热阻抗图：10×6 英寸（双子图）

## 依赖库

- `matplotlib`: 图表生成
- `numpy`: 数值计算
- `json`: JSON 数据处理

安装依赖：
```bash
pip install matplotlib numpy
```

## 注意事项

1. 如果数据中缺少某些信息（如热模型），相应的图表将不会生成
2. 图表使用非交互式后端（Agg），适合批量处理和服务器环境
3. 所有图表都包含设备型号和标题信息
4. 图表使用专业配色方案，适合技术文档

## 与 PDF 生成集成

生成的 PNG 图片可以直接嵌入到 PDF 数据表中：

```python
from reportlab.platypus import Image

# 在 PDF 中使用生成的图片
figures = generate_all_figures(json_data, 'figures')
turnon_img = Image(figures['turnon_loss'], width=6*inch, height=3.6*inch)
```

## 示例输出

测试设备 `C2M0025120D` 生成的图表：
- `C2M0025120D_turnon_loss.png` - 开关导通损耗曲线
- `C2M0025120D_turnoff_loss.png` - 开关关断损耗曲线
- `C2M0025120D_conduction.png` - 导通特性曲线
- `C2M0025120D_thermal.png` - 热阻抗曲线

所有图表已保存在 `test_figures/` 目录中，可用于评估和测试。

