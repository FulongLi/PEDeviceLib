"""
Restructure Data - Convert current JSON structure to new standardized format

This script converts all JSON files in standard_database to the new
field-grouped structure based on industry best practices.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


def generate_device_id(manufacturer: str, part_number: str) -> str:
    """Generate a standardized device ID."""
    mfr = manufacturer.lower().replace(' ', '_')
    pn = part_number.lower().replace('-', '_')
    return f"{mfr}_{pn}"


def extract_family(part_number: str) -> str:
    """Extract device family from part number."""
    # Wolfspeed naming: C2M, C3M, E3M, E4M, etc.
    match = re.match(r'^([A-Z]\d[A-Z])', part_number)
    if match:
        return match.group(1)
    return ""


def extract_voltage_rating(part_number: str) -> Optional[int]:
    """Extract voltage rating from part number if possible."""
    # Wolfspeed: C2M0025120D -> 120 = 1200V, C2M1000170J -> 170 = 1700V
    match = re.search(r'(\d{3})[A-Z]$', part_number)
    if match:
        code = int(match.group(1))
        if code in [120, 65, 60]:
            return code * 10  # 1200V, 650V, 600V
        elif code == 170:
            return 1700
        elif code == 75:
            return 750
    return None


def extract_package_code(part_number: str) -> str:
    """Extract package suffix from part number."""
    match = re.search(r'([A-Z]\d?)$', part_number)
    if match:
        return match.group(1)
    return ""


def map_package_type(package_type: str, part_number: str) -> str:
    """Map package type to standard format."""
    suffix = extract_package_code(part_number)
    
    if package_type == "power module":
        return "module"
    
    # Discrete package mapping based on suffix
    package_map = {
        'D': 'TO-247-3',
        'J': 'TO-247-4',
        'K': 'TO-247-4',
        'L': 'TO-263-7',
        'E': 'TO-247-3',
        'A': 'TO-220',
        'F': 'TO-220F',
        'G': 'D2PAK-7',
        'H': 'TO-247-3',
        'P': 'TO-247-PLUS',
    }
    
    for key, value in package_map.items():
        if suffix.startswith(key):
            return value
    
    return "discrete"


def convert_loss_data(loss_dict: Dict, loss_type: str) -> Dict[str, Any]:
    """Convert loss data to new structure."""
    result = {
        "computation_method": loss_dict.get("computation_method", "Table only"),
        "data": []
    }
    
    # Add formula if present
    if "formula" in loss_dict:
        result["formula"] = loss_dict["formula"]
    
    # Get axes
    current_axis = loss_dict.get("current_axis", [])
    voltage_axis = loss_dict.get("voltage_axis", [])
    temperature_axis = loss_dict.get("temperature_axis", [])
    
    # Filter out simulation convergence temperatures (900, 1000)
    valid_temps = [t for t in temperature_axis if t < 500]
    
    # Get energy/voltage_drop data
    if "energy" in loss_dict:
        energy_data = loss_dict["energy"]
        scale = energy_data.get("scale", 1.0)
        raw_data = energy_data.get("data", [])
        
        # Determine unit based on scale
        if scale == 0.001:
            unit = "mJ"
            scale_factor = 1.0
        elif scale == 1e-06:
            unit = "uJ"
            scale_factor = 1.0
        else:
            unit = "J"
            scale_factor = scale
        
        # Group by voltage condition
        for v_idx, vdc in enumerate(voltage_axis):
            if vdc <= 0:  # Skip negative/zero voltage
                continue
            
            condition_data = {
                "conditions": {"vdc": vdc, "vgs": 15},
                "current_axis": {"values": current_axis, "unit": "A"},
                "temperature_axis": {"values": valid_temps, "unit": "C"},
                "energy": {
                    "unit": unit,
                    "data_by_temperature": {}
                },
                "quality": "original",
                "source_ref": "plecs_model"
            }
            
            # Extract data for each valid temperature
            for t_idx, temp in enumerate(temperature_axis):
                if temp >= 500:  # Skip simulation temperatures
                    continue
                
                if t_idx < len(raw_data) and v_idx < len(raw_data[t_idx]):
                    values = raw_data[t_idx][v_idx]
                    # Apply scale factor if needed
                    if scale_factor != 1.0:
                        values = [v * scale_factor for v in values]
                    condition_data["energy"]["data_by_temperature"][str(temp)] = values
            
            result["data"].append(condition_data)
    
    return result


def convert_conduction_loss(cond_loss) -> List[Dict[str, Any]]:
    """Convert conduction loss data to new structure."""
    result = []
    
    # Handle both single dict and list of dicts
    if isinstance(cond_loss, dict):
        cond_list = [cond_loss]
    else:
        cond_list = cond_loss
    
    for cond in cond_list:
        current_axis = cond.get("current_axis", [])
        temperature_axis = cond.get("temperature_axis", [])
        voltage_drop = cond.get("voltage_drop", {})
        
        # Filter out simulation temperatures
        valid_temps = [t for t in temperature_axis if t < 500]
        
        item = {
            "gate": cond.get("gate", "on"),
            "computation_method": cond.get("computation_method", "Table only"),
            "current_axis": {"values": current_axis, "unit": "A"},
            "temperature_axis": {"values": valid_temps, "unit": "C"},
            "voltage_drop": {
                "unit": "V",
                "scale": voltage_drop.get("scale", 1.0),
                "data_by_temperature": {}
            },
            "quality": "original",
            "source_ref": "plecs_model"
        }
        
        # Add formula if present
        if "formula" in cond:
            item["formula"] = cond["formula"]
        
        # Extract data for each valid temperature
        raw_data = voltage_drop.get("data", [])
        for t_idx, temp in enumerate(temperature_axis):
            if temp >= 500:  # Skip simulation temperatures
                continue
            
            if t_idx < len(raw_data):
                item["voltage_drop"]["data_by_temperature"][str(temp)] = raw_data[t_idx]
        
        result.append(item)
    
    return result


def convert_thermal_model(thermal_dict: Dict) -> Dict[str, Any]:
    """Convert thermal model to new structure."""
    result = {
        "model_type": thermal_dict.get("type", "Cauer"),
        "rc_elements": []
    }
    
    # Calculate total Rth
    total_rth = 0.0
    
    for rc in thermal_dict.get("rc_elements", []):
        element = {
            "R": rc.get("R", 0),
            "C": rc.get("C", 0),
            "R_unit": "K/W",
            "C_unit": "J/K"
        }
        result["rc_elements"].append(element)
        total_rth += rc.get("R", 0)
    
    result["rth_jc_total"] = {"value": round(total_rth, 4), "unit": "K/W"}
    
    return result


def convert_variables(variables_list: List[Dict]) -> Dict[str, Any]:
    """Convert variables to new structure."""
    result = {}
    
    for var in variables_list:
        name = var.get("name", "").lower()
        result[name] = {
            "description": var.get("description", ""),
            "default": var.get("default_value"),
            "min": var.get("min_value"),
            "max": var.get("max_value"),
            "unit": "ohm"
        }
    
    return result


def extract_datasheet_info(comment_lines: List[str]) -> Dict[str, Any]:
    """Extract datasheet info from comment lines."""
    result = {
        "revision": None,
        "date": None,
        "ron": None,
        "vf": None
    }
    
    for line in comment_lines:
        # Look for datasheet revision
        if "Datasheet Rev" in line:
            match = re.search(r'Rev\.?(\d+),?\s*(\d{4}-\d{2}-\d{2})?', line)
            if match:
                result["revision"] = f"Rev.{match.group(1)}"
                if match.group(2):
                    result["date"] = match.group(2)
        
        # Look for Ron
        if "Ron = " in line:
            match = re.search(r'Ron\s*=\s*([\d.]+)\s*', line)
            if match:
                result["ron"] = float(match.group(1))
        
        # Look for Vf
        if "Vf = " in line:
            match = re.search(r'Vf\s*=\s*([\d.]+)\s*V', line)
            if match:
                result["vf"] = float(match.group(1))
    
    return result


def restructure_device(old_data: Dict) -> Dict[str, Any]:
    """Convert old JSON structure to new structure."""
    
    metadata = old_data.get("metadata", {})
    library = old_data.get("library", {})
    package = old_data.get("package", {})
    semiconductor_data = package.get("semiconductor_data", {})
    thermal_model = package.get("thermal_model", {})
    variables = package.get("variables", [])
    comment = package.get("comment", [])
    
    # Extract info from comments
    ds_info = extract_datasheet_info(comment)
    
    # Build new structure
    part_number = metadata.get("part_number", "")
    manufacturer = metadata.get("manufacturer", "")
    
    new_data = {
        "device_id": generate_device_id(manufacturer, part_number),
        
        "identity": {
            "manufacturer": manufacturer,
            "part_number": part_number,
            "family": extract_family(part_number),
            "aliases": [],
            "datasheet_url": None,
            "lifecycle": "active"
        },
        
        "classification": {
            "technology": "SiC_MOSFET",
            "device_type": metadata.get("type", "MOSFET with Diode"),
            "polarity": "N",
            "package_type": map_package_type(metadata.get("package_type", ""), part_number),
            "integration_level": "discrete" if metadata.get("package_type") != "power module" else "module"
        },
        
        "ratings": {
            "vds_max": None,
            "id_max": None,
            "tj_max": {"value": 175, "unit": "C"},
            "pd_max": None
        },
        
        "static": {
            "rds_on": None,
            "vf_body_diode": None,
            "vgs_th": None
        },
        
        "switching": {
            "qg_total": None,
            "ciss": None,
            "coss": None,
            "crss": None
        },
        
        "loss_curves": {},
        
        "thermal": {},
        
        "variables": {},
        
        "models": {
            "plecs": {
                "available": True,
                "version": library.get("version", "1.4"),
                "source": "Wolfspeed official"
            },
            "ltspice": {"available": False},
            "spice": {"available": False}
        },
        
        "sources": {
            "plecs_model": {
                "file": metadata.get("source_file", ""),
                "path": metadata.get("source_path", ""),
                "version": library.get("version", "")
            },
            "datasheet": {
                "revision": ds_info.get("revision"),
                "date": ds_info.get("date"),
                "url": None
            }
        },
        
        "revision": {
            "version": "2.0",
            "author": metadata.get("author", ""),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Restructured from PLECS XML model"
        }
    }
    
    # Add voltage rating if extractable
    v_rating = extract_voltage_rating(part_number)
    if v_rating:
        new_data["ratings"]["vds_max"] = {"value": v_rating, "unit": "V"}
    
    # Add static parameters from comment
    if ds_info.get("ron"):
        new_data["static"]["rds_on"] = [
            {"value": ds_info["ron"] * 1000, "unit": "mohm", 
             "conditions": {"tj": 25, "vgs": 15}, "typ_max": "typ"}
        ]
    if ds_info.get("vf"):
        new_data["static"]["vf_body_diode"] = [
            {"value": ds_info["vf"], "unit": "V",
             "conditions": {"tj": 25}, "typ_max": "typ"}
        ]
    
    # Convert loss curves
    if "turn_on_loss" in semiconductor_data:
        new_data["loss_curves"]["eon"] = convert_loss_data(
            semiconductor_data["turn_on_loss"], "eon"
        )
    
    if "turn_off_loss" in semiconductor_data:
        new_data["loss_curves"]["eoff"] = convert_loss_data(
            semiconductor_data["turn_off_loss"], "eoff"
        )
    
    if "conduction_loss" in semiconductor_data:
        new_data["loss_curves"]["vf"] = convert_conduction_loss(
            semiconductor_data["conduction_loss"]
        )
    
    # Convert thermal model
    if thermal_model:
        new_data["thermal"] = convert_thermal_model(thermal_model)
    
    # Convert variables
    if variables:
        new_data["variables"] = convert_variables(variables)
    
    return new_data


def process_all_files(input_folder: str = "standard_database", 
                      output_folder: str = "standard_database_v2"):
    """Process all JSON files and convert to new structure."""
    
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True)
    
    json_files = list(input_path.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {input_folder}")
        return
    
    print(f"Found {len(json_files)} JSON files to restructure")
    print(f"Output folder: {output_folder}")
    
    converted_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            new_data = restructure_device(old_data)
            
            output_file = output_path / json_file.name
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)
            
            converted_count += 1
            
            if converted_count % 50 == 0:
                print(f"Restructured {converted_count}/{len(json_files)} files...")
        
        except Exception as e:
            error_count += 1
            print(f"Error processing {json_file.name}: {e}")
    
    print(f"\nRestructuring complete!")
    print(f"Successfully converted: {converted_count} files")
    if error_count > 0:
        print(f"Errors: {error_count} files")
    print(f"Output saved to: {output_folder}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Restructure device JSON files")
    parser.add_argument("--input", type=str, default="standard_database",
                        help="Input folder (default: standard_database)")
    parser.add_argument("--output", type=str, default="standard_database_v2",
                        help="Output folder (default: standard_database_v2)")
    
    args = parser.parse_args()
    
    process_all_files(args.input, args.output)

