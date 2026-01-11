"""
Figure Process - Visualize JSON semiconductor data for PDF generation

This module generates visualization figures from JSON device data including:
- Turn-on loss curves
- Turn-off loss curves
- Conduction characteristics (V-I curves)
- Thermal impedance curves
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for PDF generation
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import warnings

# Set matplotlib style for publication-quality figures with white background
matplotlib.rcParams['figure.dpi'] = 300
matplotlib.rcParams['savefig.dpi'] = 300
matplotlib.rcParams['figure.facecolor'] = 'white'
matplotlib.rcParams['axes.facecolor'] = 'white'
matplotlib.rcParams['savefig.facecolor'] = 'white'
matplotlib.rcParams['savefig.edgecolor'] = 'none'
matplotlib.rcParams['font.size'] = 11
matplotlib.rcParams['axes.labelsize'] = 12
matplotlib.rcParams['axes.titlesize'] = 14
matplotlib.rcParams['xtick.labelsize'] = 10
matplotlib.rcParams['ytick.labelsize'] = 10
matplotlib.rcParams['legend.fontsize'] = 10
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['axes.grid'] = True
matplotlib.rcParams['grid.alpha'] = 0.3
matplotlib.rcParams['grid.color'] = '#cccccc'
matplotlib.rcParams['axes.edgecolor'] = '#333333'
matplotlib.rcParams['axes.linewidth'] = 1.2


def extract_energy_data(energy_data: List[List[List[float]]], 
                       current_axis: List[float],
                       voltage_axis: List[float],
                       temperature_axis: List[float],
                       scale: float = 1.0) -> Dict[str, Any]:
    """
    Extract and organize energy data for plotting.
    
    Returns a dictionary with organized data for different temperatures and voltages.
    """
    # Filter out zero/negative voltage indices (usually at index 0 or 1)
    valid_voltage_indices = [i for i, v in enumerate(voltage_axis) if v > 0]
    if not valid_voltage_indices:
        valid_voltage_indices = [len(voltage_axis) - 1]  # Use last voltage if all are zero/negative
    
    # Filter out zero/negative current indices
    valid_current_indices = [i for i, c in enumerate(current_axis) if c > 0]
    if not valid_current_indices:
        valid_current_indices = [i for i, c in enumerate(current_axis) if c >= 0]
    
    organized_data = {}
    
    for temp_idx, temp in enumerate(temperature_axis):
        if temp_idx >= len(energy_data):
            continue
        
        temp_data = energy_data[temp_idx]
        organized_data[temp] = {}
        
        for volt_idx in valid_voltage_indices:
            if volt_idx >= len(temp_data):
                continue
            
            voltage = voltage_axis[volt_idx]
            voltage_row = temp_data[volt_idx]
            
            # Extract valid current and energy pairs
            currents = []
            energies = []
            
            for curr_idx in valid_current_indices:
                if curr_idx < len(voltage_row):
                    current = current_axis[curr_idx]
                    energy = voltage_row[curr_idx] * scale
                    if energy > 0 or current == 0:  # Include zero current points
                        currents.append(current)
                        energies.append(energy)
            
            if currents and energies:
                organized_data[temp][voltage] = {
                    'current': np.array(currents),
                    'energy': np.array(energies)
                }
    
    return organized_data


def plot_turnon_loss(json_data: Dict[str, Any], output_path: str, 
                     figsize: Tuple[float, float] = (10, 6)) -> str:
    """Plot turn-on loss curves."""
    sem_data = json_data.get('package', {}).get('semiconductor_data', {})
    turnon = sem_data.get('turn_on_loss', {})
    metadata = json_data.get('metadata', {})
    
    if not turnon or 'energy' not in turnon:
        return None
    
    fig, ax = plt.subplots(figsize=figsize, facecolor='white')
    ax.set_facecolor('white')
    
    current_axis = turnon.get('current_axis', [])
    voltage_axis = turnon.get('voltage_axis', [])
    temperature_axis = turnon.get('temperature_axis', [])
    energy_data = turnon['energy'].get('data', [])
    scale = turnon['energy'].get('scale', 1.0)
    
    organized_data = extract_energy_data(energy_data, current_axis, voltage_axis, temperature_axis, scale)
    
    # Plot curves for different temperatures at the highest voltage
    if organized_data:
        max_voltage = max([max(temp_data.keys()) for temp_data in organized_data.values() if temp_data])
        
        # Use a professional color palette
        colors_map = plt.cm.tab10(np.linspace(0, 1, min(len(temperature_axis), 10)))
        if len(temperature_axis) > 10:
            colors_map = plt.cm.tab20(np.linspace(0, 1, len(temperature_axis)))
        
        for temp_idx, temp in enumerate(temperature_axis):
            if temp in organized_data and max_voltage in organized_data[temp]:
                data = organized_data[temp][max_voltage]
                if len(data['current']) > 0 and len(data['energy']) > 0:
                    # Filter out zero values for better visualization
                    valid_mask = (np.array(data['current']) > 0) & (np.array(data['energy']) > 0)
                    if np.any(valid_mask):
                        valid_current = np.array(data['current'])[valid_mask]
                        valid_energy = np.array(data['energy'])[valid_mask] * 1000  # Convert to mJ
                        ax.plot(valid_current, valid_energy,
                               marker='o', markersize=5, linewidth=2.5,
                               label=f'T_j = {temp:.0f}°C', 
                               color=colors_map[temp_idx % len(colors_map)],
                               markerfacecolor=colors_map[temp_idx % len(colors_map)],
                               markeredgecolor='white', markeredgewidth=1)
    
    ax.set_xlabel('Current (A)', fontweight='bold', fontsize=12)
    ax.set_ylabel('Turn-On Energy (mJ)', fontweight='bold', fontsize=12)
    ax.set_title(f"Turn-On Loss Characteristics - {metadata.get('part_number', 'Device')}", 
                fontweight='bold', fontsize=14, pad=15)
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
    ax.legend(loc='best', framealpha=0.95, fancybox=True, shadow=True, fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', format='png', dpi=300, facecolor='white', edgecolor='none')
    plt.close()
    
    return output_path


def plot_turnoff_loss(json_data: Dict[str, Any], output_path: str,
                     figsize: Tuple[float, float] = (10, 6)) -> str:
    """Plot turn-off loss curves."""
    sem_data = json_data.get('package', {}).get('semiconductor_data', {})
    turnoff = sem_data.get('turn_off_loss', {})
    metadata = json_data.get('metadata', {})
    
    if not turnoff or 'energy' not in turnoff:
        return None
    
    fig, ax = plt.subplots(figsize=figsize, facecolor='white')
    ax.set_facecolor('white')
    
    current_axis = turnoff.get('current_axis', [])
    voltage_axis = turnoff.get('voltage_axis', [])
    temperature_axis = turnoff.get('temperature_axis', [])
    energy_data = turnoff['energy'].get('data', [])
    scale = turnoff['energy'].get('scale', 1.0)
    
    organized_data = extract_energy_data(energy_data, current_axis, voltage_axis, temperature_axis, scale)
    
    # Plot curves for different temperatures at the highest voltage
    if organized_data:
        max_voltage = max([max(temp_data.keys()) for temp_data in organized_data.values() if temp_data])
        
        # Use a professional color palette
        colors_map = plt.cm.Set2(np.linspace(0, 1, min(len(temperature_axis), 8)))
        if len(temperature_axis) > 8:
            colors_map = plt.cm.tab20(np.linspace(0, 1, len(temperature_axis)))
        
        for temp_idx, temp in enumerate(temperature_axis):
            if temp in organized_data and max_voltage in organized_data[temp]:
                data = organized_data[temp][max_voltage]
                if len(data['current']) > 0 and len(data['energy']) > 0:
                    # Filter out zero values for better visualization
                    valid_mask = (np.array(data['current']) > 0) & (np.array(data['energy']) > 0)
                    if np.any(valid_mask):
                        valid_current = np.array(data['current'])[valid_mask]
                        valid_energy = np.array(data['energy'])[valid_mask] * 1000  # Convert to mJ
                        ax.plot(valid_current, valid_energy,
                               marker='s', markersize=5, linewidth=2.5,
                               label=f'T_j = {temp:.0f}°C', 
                               color=colors_map[temp_idx % len(colors_map)],
                               markerfacecolor=colors_map[temp_idx % len(colors_map)],
                               markeredgecolor='white', markeredgewidth=1)
    
    ax.set_xlabel('Current (A)', fontweight='bold', fontsize=12)
    ax.set_ylabel('Turn-Off Energy (mJ)', fontweight='bold', fontsize=12)
    ax.set_title(f"Turn-Off Loss Characteristics - {metadata.get('part_number', 'Device')}", 
                fontweight='bold', fontsize=14, pad=15)
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
    ax.legend(loc='best', framealpha=0.95, fancybox=True, shadow=True, fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', format='png', dpi=300, facecolor='white', edgecolor='none')
    plt.close()
    
    return output_path


def plot_conduction_characteristics(json_data: Dict[str, Any], output_path: str,
                                  figsize: Tuple[float, float] = (10, 6)) -> str:
    """Plot conduction characteristics (V-I curves)."""
    sem_data = json_data.get('package', {}).get('semiconductor_data', {})
    metadata = json_data.get('metadata', {})
    
    # Handle both single conduction_loss and list of conduction_losses
    conduction_losses = sem_data.get('conduction_loss', {})
    if isinstance(conduction_losses, list):
        # Use gate="on" if available, otherwise use the first one
        cond_loss = None
        for cl in conduction_losses:
            if cl.get('gate') == 'on':
                cond_loss = cl
                break
        if cond_loss is None and conduction_losses:
            cond_loss = conduction_losses[0]
    else:
        cond_loss = conduction_losses
    
    if not cond_loss or 'voltage_drop' not in cond_loss:
        return None
    
    fig, ax = plt.subplots(figsize=figsize, facecolor='white')
    ax.set_facecolor('white')
    
    current_axis = cond_loss.get('current_axis', [])
    temperature_axis = cond_loss.get('temperature_axis', [])
    voltage_drop_data = cond_loss['voltage_drop'].get('data', [])
    scale = cond_loss['voltage_drop'].get('scale', 1.0)
    
    # Check if data is empty - if so, try to get data from original structure
    if not voltage_drop_data or all(len(row) == 0 for row in voltage_drop_data):
        # Data might be in a different format, try to read from source
        return None
    
    # Use all current indices (including negative for reverse conduction)
    all_current_indices = list(range(len(current_axis)))
    
    if not all_current_indices or not voltage_drop_data:
        return None
    
    # Use a professional color palette
    colors_map = plt.cm.tab10(np.linspace(0, 1, min(len(temperature_axis), 10)))
    if len(temperature_axis) > 10:
        colors_map = plt.cm.tab20(np.linspace(0, 1, len(temperature_axis)))
    
    has_data = False
    for temp_idx, temp in enumerate(temperature_axis):
        if temp_idx >= len(voltage_drop_data):
            continue
        
        voltage_row = voltage_drop_data[temp_idx]
        
        # Extract valid current-voltage pairs
        currents = []
        voltages = []
        
        for curr_idx in all_current_indices:
            if curr_idx < len(voltage_row):
                current = current_axis[curr_idx]
                voltage = voltage_row[curr_idx] * scale
                # Include all points
                if current is not None and voltage is not None:
                    currents.append(current)
                    voltages.append(voltage)
        
        if currents and voltages and len(currents) > 1:
            # Sort by current for smooth curve
            sorted_pairs = sorted(zip(currents, voltages))
            sorted_currents, sorted_voltages = zip(*sorted_pairs)
            
            ax.plot(sorted_currents, sorted_voltages, 
                   marker='o', markersize=4, linewidth=2.5,
                   label=f'T_j = {temp:.0f}°C', 
                   color=colors_map[temp_idx % len(colors_map)],
                   markerfacecolor=colors_map[temp_idx % len(colors_map)],
                   markeredgecolor='white', markeredgewidth=1)
            has_data = True
    
    if not has_data:
        return None
    
    ax.set_xlabel('Current (A)', fontweight='bold', fontsize=12)
    ax.set_ylabel('Voltage Drop (V)', fontweight='bold', fontsize=12)
    ax.set_title(f"Conduction Characteristics (I-V Curve) - {metadata.get('part_number', 'Device')}", 
                fontweight='bold', fontsize=14, pad=15)
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
    ax.legend(loc='best', framealpha=0.95, fancybox=True, shadow=True, fontsize=10,
             ncol=2 if len(temperature_axis) > 4 else 1)
    ax.axhline(y=0, color='#666666', linestyle='--', linewidth=1, alpha=0.5)
    ax.axvline(x=0, color='#666666', linestyle='--', linewidth=1, alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', format='png', dpi=300, facecolor='white', edgecolor='none')
    plt.close()
    
    return output_path


def plot_thermal_impedance(json_data: Dict[str, Any], output_path: str,
                          figsize: Tuple[float, float] = (10, 6)) -> str:
    """Plot thermal impedance curve from thermal model."""
    thermal = json_data.get('package', {}).get('thermal_model', {})
    metadata = json_data.get('metadata', {})
    
    if not thermal or 'rc_elements' not in thermal:
        return None
    
    rc_elements = thermal.get('rc_elements', [])
    if not rc_elements:
        return None
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize, facecolor='white')
    ax1.set_facecolor('white')
    ax2.set_facecolor('white')
    
    # Extract R and C values
    R_values = [rc['R'] for rc in rc_elements]
    C_values = [rc['C'] for rc in rc_elements]
    tau_values = [R * C for R, C in zip(R_values, C_values)]
    
    # Calculate cumulative thermal resistance
    R_cumulative = np.cumsum([0] + R_values)
    
    # Generate time vector for thermal impedance
    t_min = min(tau_values) / 100 if tau_values else 1e-6
    t_max = sum(tau_values) * 10 if tau_values else 1
    time = np.logspace(np.log10(t_min), np.log10(t_max), 1000)
    
    # Calculate thermal impedance Z_th(t)
    Z_th = np.zeros_like(time)
    for R, tau in zip(R_values, tau_values):
        Z_th += R * (1 - np.exp(-time / tau))
    
    # Plot thermal impedance with better styling
    ax1.loglog(time * 1000, Z_th, color='#2563eb', linewidth=3, label='Thermal Impedance')
    ax1.set_xlabel('Time (ms)', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Thermal Impedance Z_th (K/W)', fontweight='bold', fontsize=12)
    ax1.set_title('Thermal Impedance vs Time', fontweight='bold', fontsize=13)
    ax1.grid(True, alpha=0.3, which='both', linestyle='--', linewidth=0.8)
    ax1.legend(framealpha=0.95, fancybox=True, shadow=True, fontsize=10)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # Plot RC network structure with better styling
    colors_bar = plt.cm.Blues(np.linspace(0.4, 0.9, len(R_values)))
    bars = ax2.barh(range(len(R_values)), R_values, align='center', 
                   color=colors_bar, edgecolor='#1e3a8a', linewidth=1.5)
    ax2.set_yticks(range(len(R_values)))
    ax2.set_yticklabels([f'R{i+1}' for i in range(len(R_values))], fontweight='bold')
    ax2.set_xlabel('Thermal Resistance (K/W)', fontweight='bold', fontsize=12)
    ax2.set_title('RC Network Structure', fontweight='bold', fontsize=13)
    ax2.grid(True, alpha=0.3, axis='x', linestyle='--', linewidth=0.8)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    # Add value labels on bars
    for i, (bar, r_val) in enumerate(zip(bars, R_values)):
        width = bar.get_width()
        ax2.text(width, bar.get_y() + bar.get_height()/2, 
                f' {r_val:.4f}', ha='left', va='center', fontweight='bold', fontsize=9)
    
    # Add text annotation for total R_th
    total_R = sum(R_values)
    ax2.text(0.98, 0.02, f'Total R_th = {total_R:.4f} K/W',
            transform=ax2.transAxes, fontsize=11, fontweight='bold',
            verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='#fef3c7', edgecolor='#f59e0b', 
                     linewidth=2, alpha=0.9))
    
    plt.suptitle(f"Thermal Model - {metadata.get('part_number', 'Device')}", 
                fontweight='bold', fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', format='png', dpi=300, facecolor='white', edgecolor='none')
    plt.close()
    
    return output_path


def generate_all_figures(json_data: Dict[str, Any], output_dir: str,
                         part_number: Optional[str] = None) -> Dict[str, str]:
    """
    Generate all figures for a device.
    
    Returns a dictionary mapping figure type to file path.
    """
    if part_number is None:
        part_number = json_data.get('metadata', {}).get('part_number', 'device')
    
    safe_part_number = part_number.replace('-', '_').replace(' ', '_')
    os.makedirs(output_dir, exist_ok=True)
    
    figures = {}
    
    # Generate turn-on loss figure
    try:
        turnon_path = os.path.join(output_dir, f'{safe_part_number}_turnon_loss.png')
        result = plot_turnon_loss(json_data, turnon_path)
        if result:
            figures['turnon_loss'] = result
    except Exception as e:
        warnings.warn(f"Failed to generate turn-on loss figure: {e}")
    
    # Generate turn-off loss figure
    try:
        turnoff_path = os.path.join(output_dir, f'{safe_part_number}_turnoff_loss.png')
        result = plot_turnoff_loss(json_data, turnoff_path)
        if result:
            figures['turnoff_loss'] = result
    except Exception as e:
        warnings.warn(f"Failed to generate turn-off loss figure: {e}")
    
    # Generate conduction characteristics figure
    try:
        cond_path = os.path.join(output_dir, f'{safe_part_number}_conduction.png')
        result = plot_conduction_characteristics(json_data, cond_path)
        if result:
            figures['conduction'] = result
    except Exception as e:
        warnings.warn(f"Failed to generate conduction characteristics figure: {e}")
    
    # Generate thermal impedance figure
    try:
        thermal_path = os.path.join(output_dir, f'{safe_part_number}_thermal.png')
        result = plot_thermal_impedance(json_data, thermal_path)
        if result:
            figures['thermal'] = result
    except Exception as e:
        warnings.warn(f"Failed to generate thermal impedance figure: {e}")
    
    return figures


def process_json_file(json_path: str, output_dir: str) -> Dict[str, str]:
    """Process a single JSON file and generate all figures."""
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    part_number = json_data.get('metadata', {}).get('part_number', Path(json_path).stem)
    
    return generate_all_figures(json_data, output_dir, part_number)


def process_directory(input_dir: str, output_dir: str):
    """Process all JSON files in a directory."""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    json_files = list(input_path.glob('*.json'))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to process")
    print(f"Output directory: {output_dir}")
    
    processed_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            process_json_file(str(json_file), output_dir)
            processed_count += 1
            
            if processed_count % 50 == 0:
                print(f"Processed {processed_count}/{len(json_files)} files...")
        
        except Exception as e:
            error_count += 1
            print(f"Failed to process {json_file}: {str(e)}")
    
    print(f"\nProcessing complete!")
    print(f"Successfully processed: {processed_count} files")
    if error_count > 0:
        print(f"Errors: {error_count} files")
    print(f"All figures saved to: {output_dir}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate visualization figures from JSON device data')
    parser.add_argument('--input', type=str, default='standard_database',
                        help='Input directory or file with JSON data (default: standard_database)')
    parser.add_argument('--output', type=str, default='figures',
                        help='Output directory for figures (default: figures)')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if input_path.is_file():
        # Process single file
        process_json_file(str(input_path), args.output)
    else:
        # Process directory
        process_directory(str(input_path), args.output)

