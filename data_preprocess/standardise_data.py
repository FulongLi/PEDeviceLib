"""
Standardise Data - Convert XML semiconductor model files to JSON format

This script traverses the DUTs folder and converts all XML model files
to standardized JSON format for easier processing and analysis.
"""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


def parse_axis(axis_text: str) -> List[float]:
    """Parse space-separated axis values into a list of floats."""
    if not axis_text or not axis_text.strip():
        return []
    return [float(x) for x in axis_text.strip().split() if x]


def parse_voltage_data(voltage_elem) -> List[float]:
    """Parse voltage element text into a list of floats."""
    if voltage_elem.text:
        return parse_axis(voltage_elem.text)
    return []


def parse_temperature_data(temperature_elem) -> List[List[float]]:
    """Parse temperature element containing multiple voltage elements."""
    voltage_data = []
    for voltage in temperature_elem.findall('Voltage'):
        voltage_data.append(parse_voltage_data(voltage))
    return voltage_data


def parse_energy_or_voltage_drop(elem, data_type: str) -> Dict[str, Any]:
    """Parse Energy or VoltageDrop element."""
    result = {}
    scale = elem.get('scale', '1')
    result['scale'] = float(scale) if scale else 1.0
    
    temperature_data = []
    for temp_elem in elem.findall('Temperature'):
        # Check if this is Energy (has Voltage children) or VoltageDrop (direct text)
        voltage_children = temp_elem.findall('Voltage')
        if voltage_children:
            # Energy structure: Temperature -> Voltage elements
            temp_data = parse_temperature_data(temp_elem)
            temperature_data.append(temp_data)
        else:
            # VoltageDrop structure: Temperature has direct text data
            if temp_elem.text:
                voltage_values = parse_axis(temp_elem.text)
                temperature_data.append(voltage_values)
            else:
                temperature_data.append([])
    
    result['data'] = temperature_data
    return result


def parse_loss_section(loss_elem) -> Dict[str, Any]:
    """Parse TurnOnLoss, TurnOffLoss, or ConductionLoss section."""
    result = {}
    
    # ComputationMethod
    method_elem = loss_elem.find('ComputationMethod')
    if method_elem is not None and method_elem.text:
        result['computation_method'] = method_elem.text.strip()
    
    # Formula (optional)
    formula_elem = loss_elem.find('Formula')
    if formula_elem is not None and formula_elem.text:
        result['formula'] = formula_elem.text.strip()
    
    # Axes
    current_axis = loss_elem.find('CurrentAxis')
    if current_axis is not None and current_axis.text:
        result['current_axis'] = parse_axis(current_axis.text)
    
    voltage_axis = loss_elem.find('VoltageAxis')
    if voltage_axis is not None and voltage_axis.text:
        result['voltage_axis'] = parse_axis(voltage_axis.text)
    
    temperature_axis = loss_elem.find('TemperatureAxis')
    if temperature_axis is not None and temperature_axis.text:
        result['temperature_axis'] = parse_axis(temperature_axis.text)
    
    # Energy or VoltageDrop
    energy_elem = loss_elem.find('Energy')
    if energy_elem is not None:
        result['energy'] = parse_energy_or_voltage_drop(energy_elem, 'energy')
    
    voltage_drop_elem = loss_elem.find('VoltageDrop')
    if voltage_drop_elem is not None:
        result['voltage_drop'] = parse_energy_or_voltage_drop(voltage_drop_elem, 'voltage_drop')
    
    # Gate attribute for ConductionLoss
    gate_attr = loss_elem.get('gate')
    if gate_attr:
        result['gate'] = gate_attr
    
    return result


def parse_variables(variables_elem) -> List[Dict[str, Any]]:
    """Parse Variables section."""
    variables = []
    for var_elem in variables_elem.findall('Variable'):
        var_dict = {}
        
        name_elem = var_elem.find('Name')
        if name_elem is not None and name_elem.text:
            var_dict['name'] = name_elem.text.strip()
        
        desc_elem = var_elem.find('Description')
        if desc_elem is not None and desc_elem.text:
            var_dict['description'] = desc_elem.text.strip()
        
        default_elem = var_elem.find('DefaultValue')
        if default_elem is not None and default_elem.text:
            try:
                var_dict['default_value'] = float(default_elem.text.strip())
            except ValueError:
                var_dict['default_value'] = default_elem.text.strip()
        
        min_elem = var_elem.find('MinValue')
        if min_elem is not None and min_elem.text:
            try:
                var_dict['min_value'] = float(min_elem.text.strip())
            except ValueError:
                var_dict['min_value'] = min_elem.text.strip()
        
        max_elem = var_elem.find('MaxValue')
        if max_elem is not None and max_elem.text:
            try:
                var_dict['max_value'] = float(max_elem.text.strip())
            except ValueError:
                var_dict['max_value'] = max_elem.text.strip()
        
        variables.append(var_dict)
    
    return variables


def parse_thermal_model(thermal_elem) -> Dict[str, Any]:
    """Parse ThermalModel section."""
    result = {}
    
    branch_elem = thermal_elem.find('Branch')
    if branch_elem is not None:
        branch_type = branch_elem.get('type', '')
        result['type'] = branch_type
        
        rc_elements = []
        for rc_elem in branch_elem.findall('RCElement'):
            rc_dict = {}
            r_val = rc_elem.get('R')
            c_val = rc_elem.get('C')
            if r_val:
                rc_dict['R'] = float(r_val)
            if c_val:
                rc_dict['C'] = float(c_val)
            rc_elements.append(rc_dict)
        
        result['rc_elements'] = rc_elements
    
    return result


def parse_comment(comment_elem) -> List[str]:
    """Parse Comment section."""
    lines = []
    for line_elem in comment_elem.findall('Line'):
        if line_elem.text:
            lines.append(line_elem.text)
        else:
            lines.append('')
    return lines


def parse_semiconductor_data(semiconductor_elem) -> Dict[str, Any]:
    """Parse SemiconductorData section."""
    result = {}
    data_type = semiconductor_elem.get('type', '')
    result['type'] = data_type
    
    # TurnOnLoss
    turnon_elem = semiconductor_elem.find('TurnOnLoss')
    if turnon_elem is not None:
        result['turn_on_loss'] = parse_loss_section(turnon_elem)
    
    # TurnOffLoss
    turnoff_elem = semiconductor_elem.find('TurnOffLoss')
    if turnoff_elem is not None:
        result['turn_off_loss'] = parse_loss_section(turnoff_elem)
    
    # ConductionLoss (can have multiple with gate attribute)
    conduction_losses = []
    for cond_elem in semiconductor_elem.findall('ConductionLoss'):
        conduction_losses.append(parse_loss_section(cond_elem))
    
    if conduction_losses:
        if len(conduction_losses) == 1:
            result['conduction_loss'] = conduction_losses[0]
        else:
            result['conduction_loss'] = conduction_losses
    
    return result


def extract_material_type_from_path(file_path: str) -> str:
    """Extract material type (Si, SiC, GaN) from file path."""
    path_parts = Path(file_path).parts
    for part in path_parts:
        if part in ['Si', 'SiC', 'GaN']:
            return part
    return 'Unknown'


def extract_manufacturer_from_path(file_path: str) -> str:
    """Extract manufacturer name from file path."""
    path_parts = Path(file_path).parts
    # Common manufacturer folders in DUTs structure
    manufacturers = ['Wolfspeed', 'Infineon', 'STMicroelectronics', 'ON_Semiconductor', 
                     'Vishay', 'Littelfuse', 'Microchip', 'ROHM', 'Mitsubishi_Electric',
                     'GaN_Systems', 'Navitas', 'Power_Integrations', 'Transphorm', 'EPC']
    
    for part in path_parts:
        if part in manufacturers:
            return part.replace('_', ' ')
    return 'Unknown'


def extract_package_type_from_path(file_path: str) -> str:
    """Extract package type (discrete or power module) from file path."""
    path_parts = Path(file_path).parts
    path_lower = str(file_path).lower()
    
    # Check for module indicators in path
    if 'modules' in path_lower or 'module' in path_lower:
        return 'power module'
    
    # Check for discrete indicators
    if 'mosfets' in path_lower or 'diodes' in path_lower or 'diode' in path_lower:
        return 'discrete'
    
    # Default to discrete if not clear
    return 'discrete'


def xml_to_json(xml_file_path: str, author: str = 'Fulong Li') -> Dict[str, Any]:
    """Convert XML file to JSON dictionary with metadata."""
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    # Remove namespace for easier parsing
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}')[1]
    
    # Extract metadata from path
    material_type = extract_material_type_from_path(xml_file_path)
    manufacturer = extract_manufacturer_from_path(xml_file_path)
    package_type = extract_package_type_from_path(xml_file_path)
    
    # Parse Package element
    package_elem = root.find('Package')
    vendor = ''
    device_type = ''
    partnumber = ''
    
    if package_elem is not None:
        vendor = package_elem.get('vendor', '')
        device_type = package_elem.get('class', '')
        partnumber = package_elem.get('partnumber', '')
    
    # Use vendor from XML if available, otherwise use path-based manufacturer
    if vendor:
        manufacturer = vendor
    
    # Build result with metadata
    result = {
        'metadata': {
            'manufacturer': manufacturer,
            'type': device_type or 'Unknown',
            'material': material_type,
            'package_type': package_type,
            'part_number': partnumber,
            'author': author,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source_file': str(Path(xml_file_path).name),
            'source_path': str(Path(xml_file_path).relative_to(Path('DUTs'))) if 'DUTs' in xml_file_path else ''
        },
        'library': {
            'xmlns': root.get('xmlns', ''),
            'version': root.get('version', '')
        }
    }
    
    # Parse Package element
    if package_elem is not None:
        package_dict = {
            'class': device_type,
            'vendor': vendor,
            'partnumber': partnumber
        }
        
        # Variables
        variables_elem = package_elem.find('Variables')
        if variables_elem is not None:
            variables = parse_variables(variables_elem)
            if variables:
                package_dict['variables'] = variables
        
        # SemiconductorData
        semiconductor_elem = package_elem.find('SemiconductorData')
        if semiconductor_elem is not None:
            package_dict['semiconductor_data'] = parse_semiconductor_data(semiconductor_elem)
        
        # ThermalModel
        thermal_elem = package_elem.find('ThermalModel')
        if thermal_elem is not None:
            package_dict['thermal_model'] = parse_thermal_model(thermal_elem)
        
        # Comment
        comment_elem = package_elem.find('Comment')
        if comment_elem is not None:
            package_dict['comment'] = parse_comment(comment_elem)
        
        result['package'] = package_dict
    
    return result


def convert_xml_to_json(xml_path: str, output_path: Optional[str] = None, author: str = 'Fulong Li') -> str:
    """Convert a single XML file to JSON and save it."""
    try:
        json_data = xml_to_json(xml_path, author)
        
        if output_path is None:
            # Save in same location with .json extension
            output_path = str(Path(xml_path).with_suffix('.json'))
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write JSON file with pretty formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        return output_path
    except Exception as e:
        print(f"Error converting {xml_path}: {str(e)}")
        raise


def process_duts_folder(duts_folder: str = 'DUTs', output_folder: Optional[str] = None, author: str = 'Fulong Li'):
    """Process all XML files in the DUTs folder."""
    duts_path = Path(duts_folder)
    
    if not duts_path.exists():
        raise FileNotFoundError(f"DUTs folder not found: {duts_folder}")
    
    # Default output folder
    if output_folder is None:
        output_folder = 'standard_database'
    
    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True)
    
    # Find all XML files
    xml_files = list(duts_path.rglob('*.xml'))
    
    if not xml_files:
        print(f"No XML files found in {duts_folder}")
        return
    
    print(f"Found {len(xml_files)} XML files to convert")
    print(f"Output folder: {output_folder}")
    
    converted_count = 0
    error_count = 0
    
    for xml_file in xml_files:
        try:
            # Save all files directly in output folder (no subdirectories)
            # Use part number as filename, or fallback to original filename
            json_filename = xml_file.stem + '.json'
            output_file_path = output_path / json_filename
            
            # Handle duplicate filenames by adding a counter
            counter = 1
            original_output_path = output_file_path
            while output_file_path.exists():
                json_filename = f"{xml_file.stem}_{counter}.json"
                output_file_path = output_path / json_filename
                counter += 1
            
            json_path = convert_xml_to_json(str(xml_file), str(output_file_path), author)
            converted_count += 1
            
            if converted_count % 50 == 0:
                print(f"Converted {converted_count}/{len(xml_files)} files...")
        
        except Exception as e:
            error_count += 1
            print(f"Failed to convert {xml_file}: {str(e)}")
    
    print(f"\nConversion complete!")
    print(f"Successfully converted: {converted_count} files")
    if error_count > 0:
        print(f"Errors: {error_count} files")
    print(f"All JSON files saved to: {output_folder}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert XML semiconductor models to JSON format')
    parser.add_argument('--duts', type=str, default='DUTs',
                        help='Path to DUTs folder (default: DUTs)')
    parser.add_argument('--output', type=str, default='standard_database',
                        help='Output folder for JSON files (default: standard_database)')
    parser.add_argument('--author', type=str, default='Fulong Li',
                        help='Author name for metadata (default: Fulong Li)')
    
    args = parser.parse_args()
    
    process_duts_folder(args.duts, args.output, args.author)

