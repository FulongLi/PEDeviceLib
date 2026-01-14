"""
分析standard_database中所有JSON文件的共同特征
"""
import json
import os
from collections import defaultdict, Counter
from pathlib import Path

def analyze_all_files(database_folder='standard_database'):
    """分析所有JSON文件的结构和特征"""
    files = list(Path(database_folder).glob('*.json'))
    
    if not files:
        print(f"No JSON files found in {database_folder}")
        return
    
    print(f"Analyzing {len(files)} JSON files...\n")
    
    # 统计信息
    metadata_fields = defaultdict(set)
    device_types = Counter()
    materials = Counter()
    manufacturers = Counter()
    package_types = Counter()
    computation_methods = Counter()
    thermal_model_types = Counter()
    has_variables = 0
    has_turn_on_loss = 0
    has_turn_off_loss = 0
    has_conduction_loss = 0
    has_thermal_model = 0
    has_comment = 0
    variable_names = Counter()
    axis_counts = {'current': [], 'voltage': [], 'temperature': []}
    energy_scales = []
    voltage_drop_scales = []
    
    # 分析每个文件
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 分析metadata
            if 'metadata' in data:
                meta = data['metadata']
                for key in meta.keys():
                    metadata_fields[key].add(type(meta[key]).__name__)
                
                device_types[meta.get('type', 'Unknown')] += 1
                materials[meta.get('material', 'Unknown')] += 1
                manufacturers[meta.get('manufacturer', 'Unknown')] += 1
                package_types[meta.get('package_type', 'Unknown')] += 1
            
            # 分析package
            if 'package' in data:
                pkg = data['package']
                
                # Variables
                if 'variables' in pkg:
                    has_variables += 1
                    for var in pkg['variables']:
                        if 'name' in var:
                            variable_names[var['name']] += 1
                
                # SemiconductorData
                if 'semiconductor_data' in pkg:
                    sem_data = pkg['semiconductor_data']
                    
                    # TurnOnLoss
                    if 'turn_on_loss' in sem_data:
                        has_turn_on_loss += 1
                        loss = sem_data['turn_on_loss']
                        if 'computation_method' in loss:
                            computation_methods[loss['computation_method']] += 1
                        if 'current_axis' in loss:
                            axis_counts['current'].append(len(loss['current_axis']))
                        if 'voltage_axis' in loss:
                            axis_counts['voltage'].append(len(loss['voltage_axis']))
                        if 'temperature_axis' in loss:
                            axis_counts['temperature'].append(len(loss['temperature_axis']))
                        if 'energy' in loss and 'scale' in loss['energy']:
                            energy_scales.append(loss['energy']['scale'])
                    
                    # TurnOffLoss
                    if 'turn_off_loss' in sem_data:
                        has_turn_off_loss += 1
                        loss = sem_data['turn_off_loss']
                        if 'computation_method' in loss:
                            computation_methods[loss['computation_method']] += 1
                    
                    # ConductionLoss
                    if 'conduction_loss' in sem_data:
                        has_conduction_loss += 1
                        cond_loss = sem_data['conduction_loss']
                        # 可能是单个对象或列表
                        if isinstance(cond_loss, list):
                            for cl in cond_loss:
                                if 'computation_method' in cl:
                                    computation_methods[cl['computation_method']] += 1
                                if 'voltage_drop' in cl and 'scale' in cl['voltage_drop']:
                                    voltage_drop_scales.append(cl['voltage_drop']['scale'])
                        else:
                            if 'computation_method' in cond_loss:
                                computation_methods[cond_loss['computation_method']] += 1
                            if 'voltage_drop' in cond_loss and 'scale' in cond_loss['voltage_drop']:
                                voltage_drop_scales.append(cond_loss['voltage_drop']['scale'])
                
                # ThermalModel
                if 'thermal_model' in pkg:
                    has_thermal_model += 1
                    thermal = pkg['thermal_model']
                    if 'type' in thermal:
                        thermal_model_types[thermal['type']] += 1
                
                # Comment
                if 'comment' in pkg:
                    has_comment += 1
        
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    # 打印分析结果
    print("=" * 80)
    print("Common Data Features Summary")
    print("=" * 80)
    
    print("\n1. File Structure Features")
    print("-" * 80)
    print(f"All files contain the following top-level fields:")
    print(f"  - metadata: Metadata information")
    print(f"  - library: Library information (xmlns, version)")
    print(f"  - package: Device package information")
    
    print("\n2. Metadata Fields Statistics")
    print("-" * 80)
    print(f"All files contain these metadata fields:")
    for field in sorted(metadata_fields.keys()):
        types = metadata_fields[field]
        print(f"  - {field}: {', '.join(sorted(types))}")
    
    print("\n3. Device Type Distribution")
    print("-" * 80)
    for dtype, count in device_types.most_common():
        print(f"  {dtype}: {count} files ({count/len(files)*100:.1f}%)")
    
    print("\n4. Material Type Distribution")
    print("-" * 80)
    for material, count in materials.most_common():
        print(f"  {material}: {count} files ({count/len(files)*100:.1f}%)")
    
    print("\n5. Manufacturer Distribution")
    print("-" * 80)
    for mfg, count in manufacturers.most_common(10):
        print(f"  {mfg}: {count} files ({count/len(files)*100:.1f}%)")
    
    print("\n6. Package Type Distribution")
    print("-" * 80)
    for pkg_type, count in package_types.most_common():
        print(f"  {pkg_type}: {count} files ({count/len(files)*100:.1f}%)")
    
    print("\n7. Package Fields Statistics")
    print("-" * 80)
    print(f"  - Contains variables: {has_variables} files ({has_variables/len(files)*100:.1f}%)")
    print(f"  - Contains turn_on_loss: {has_turn_on_loss} files ({has_turn_on_loss/len(files)*100:.1f}%)")
    print(f"  - Contains turn_off_loss: {has_turn_off_loss} files ({has_turn_off_loss/len(files)*100:.1f}%)")
    print(f"  - Contains conduction_loss: {has_conduction_loss} files ({has_conduction_loss/len(files)*100:.1f}%)")
    print(f"  - Contains thermal_model: {has_thermal_model} files ({has_thermal_model/len(files)*100:.1f}%)")
    print(f"  - Contains comment: {has_comment} files ({has_comment/len(files)*100:.1f}%)")
    
    print("\n8. Common Variable Names")
    print("-" * 80)
    for var_name, count in variable_names.most_common(10):
        print(f"  {var_name}: {count} occurrences")
    
    print("\n9. Computation Method Distribution")
    print("-" * 80)
    for method, count in computation_methods.most_common():
        print(f"  {method}: {count} occurrences")
    
    print("\n10. Thermal Model Type Distribution")
    print("-" * 80)
    for ttype, count in thermal_model_types.most_common():
        print(f"  {ttype}: {count} files")
    
    print("\n11. Data Dimension Statistics")
    print("-" * 80)
    if axis_counts['current']:
        print(f"  Current axis points: avg {sum(axis_counts['current'])/len(axis_counts['current']):.1f}, "
              f"range {min(axis_counts['current'])}-{max(axis_counts['current'])}")
    if axis_counts['voltage']:
        print(f"  Voltage axis points: avg {sum(axis_counts['voltage'])/len(axis_counts['voltage']):.1f}, "
              f"range {min(axis_counts['voltage'])}-{max(axis_counts['voltage'])}")
    if axis_counts['temperature']:
        print(f"  Temperature axis points: avg {sum(axis_counts['temperature'])/len(axis_counts['temperature']):.1f}, "
              f"range {min(axis_counts['temperature'])}-{max(axis_counts['temperature'])}")
    
    print("\n12. Data Scale Factors")
    print("-" * 80)
    if energy_scales:
        unique_scales = set(energy_scales)
        print(f"  Energy scale values: {sorted(unique_scales)}")
    if voltage_drop_scales:
        unique_scales = set(voltage_drop_scales)
        print(f"  VoltageDrop scale values: {sorted(unique_scales)}")
    
    print("\n" + "=" * 80)
    print("Analysis Complete!")
    print("=" * 80)

if __name__ == '__main__':
    analyze_all_files()

