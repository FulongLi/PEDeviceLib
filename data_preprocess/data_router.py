"""
Data Router - Convert standardized JSON data to various formats

This script converts JSON files from standard_database to:
- PLECS XML models
- Matlab .mat files
- Datasheet PDF documents
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import scipy.io as sio

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: reportlab not available. PDF generation will be disabled.")


def format_axis_values(values: List[float]) -> str:
    """Format a list of float values as space-separated string for XML."""
    return ' '.join([str(v) for v in values])


def format_energy_data(data: List[List[List[float]]], scale: float = 1.0) -> str:
    """Format energy data for XML output."""
    # Scale the data
    scaled_data = [[[val * scale for val in row] for row in temp_data] for temp_data in data]
    
    xml_lines = []
    for temp_data in scaled_data:
        xml_lines.append('                    <Temperature>')
        for voltage_row in temp_data:
            voltage_str = format_axis_values(voltage_row)
            xml_lines.append(f'                        <Voltage>{voltage_str}</Voltage>')
        xml_lines.append('                    </Temperature>')
    
    return '\n'.join(xml_lines)


def format_voltage_drop_data(data: List[List[float]], scale: float = 1.0) -> str:
    """Format voltage drop data for XML output."""
    scaled_data = [[val * scale for val in row] for row in data]
    
    xml_lines = []
    for row in scaled_data:
        voltage_str = format_axis_values(row)
        xml_lines.append(f'                    <Temperature>{voltage_str}</Temperature>')
    
    return '\n'.join(xml_lines)


def json_to_plecs_xml(json_data: Dict[str, Any], output_path: str) -> str:
    """Convert JSON data to PLECS XML format."""
    metadata = json_data.get('metadata', {})
    package = json_data.get('package', {})
    library = json_data.get('library', {})
    
    # Create root element
    root = ET.Element('SemiconductorLibrary')
    root.set('xmlns', library.get('xmlns', 'http://www.plexim.com/xml/semiconductors/'))
    root.set('version', library.get('version', '1.4'))
    
    # Create Package element
    package_elem = ET.SubElement(root, 'Package')
    package_elem.set('class', package.get('class', ''))
    package_elem.set('vendor', package.get('vendor', metadata.get('manufacturer', '')))
    package_elem.set('partnumber', package.get('partnumber', metadata.get('part_number', '')))
    
    # Variables
    variables = package.get('variables', [])
    if variables:
        variables_elem = ET.SubElement(package_elem, 'Variables')
        for var in variables:
            var_elem = ET.SubElement(variables_elem, 'Variable')
            ET.SubElement(var_elem, 'Name').text = var.get('name', '')
            ET.SubElement(var_elem, 'Description').text = var.get('description', '')
            if 'default_value' in var:
                ET.SubElement(var_elem, 'DefaultValue').text = str(var['default_value'])
            if 'min_value' in var:
                ET.SubElement(var_elem, 'MinValue').text = str(var['min_value'])
            if 'max_value' in var:
                ET.SubElement(var_elem, 'MaxValue').text = str(var['max_value'])
    
    # SemiconductorData
    sem_data = package.get('semiconductor_data', {})
    if sem_data:
        sem_elem = ET.SubElement(package_elem, 'SemiconductorData')
        sem_elem.set('type', sem_data.get('type', ''))
        
        # TurnOnLoss
        turnon = sem_data.get('turn_on_loss', {})
        if turnon:
            turnon_elem = ET.SubElement(sem_elem, 'TurnOnLoss')
            ET.SubElement(turnon_elem, 'ComputationMethod').text = turnon.get('computation_method', 'Table only')
            if 'formula' in turnon:
                ET.SubElement(turnon_elem, 'Formula').text = turnon['formula']
            if 'current_axis' in turnon:
                ET.SubElement(turnon_elem, 'CurrentAxis').text = format_axis_values(turnon['current_axis'])
            if 'voltage_axis' in turnon:
                ET.SubElement(turnon_elem, 'VoltageAxis').text = format_axis_values(turnon['voltage_axis'])
            if 'temperature_axis' in turnon:
                ET.SubElement(turnon_elem, 'TemperatureAxis').text = format_axis_values(turnon['temperature_axis'])
            if 'energy' in turnon:
                energy = turnon['energy']
                energy_elem = ET.SubElement(turnon_elem, 'Energy')
                energy_elem.set('scale', str(energy.get('scale', 1.0)))
                energy_data = energy.get('data', [])
                for temp_data in energy_data:
                    temp_elem = ET.SubElement(energy_elem, 'Temperature')
                    for voltage_row in temp_data:
                        voltage_elem = ET.SubElement(temp_elem, 'Voltage')
                        voltage_elem.text = format_axis_values(voltage_row)
        
        # TurnOffLoss
        turnoff = sem_data.get('turn_off_loss', {})
        if turnoff:
            turnoff_elem = ET.SubElement(sem_elem, 'TurnOffLoss')
            ET.SubElement(turnoff_elem, 'ComputationMethod').text = turnoff.get('computation_method', 'Table only')
            if 'formula' in turnoff:
                ET.SubElement(turnoff_elem, 'Formula').text = turnoff['formula']
            if 'current_axis' in turnoff:
                ET.SubElement(turnoff_elem, 'CurrentAxis').text = format_axis_values(turnoff['current_axis'])
            if 'voltage_axis' in turnoff:
                ET.SubElement(turnoff_elem, 'VoltageAxis').text = format_axis_values(turnoff['voltage_axis'])
            if 'temperature_axis' in turnoff:
                ET.SubElement(turnoff_elem, 'TemperatureAxis').text = format_axis_values(turnoff['temperature_axis'])
            if 'energy' in turnoff:
                energy = turnoff['energy']
                energy_elem = ET.SubElement(turnoff_elem, 'Energy')
                energy_elem.set('scale', str(energy.get('scale', 1.0)))
                energy_data = energy.get('data', [])
                for temp_data in energy_data:
                    temp_elem = ET.SubElement(energy_elem, 'Temperature')
                    for voltage_row in temp_data:
                        voltage_elem = ET.SubElement(temp_elem, 'Voltage')
                        voltage_elem.text = format_axis_values(voltage_row)
        
        # ConductionLoss
        conduction_losses = sem_data.get('conduction_loss', {})
        if isinstance(conduction_losses, list):
            for cond_loss in conduction_losses:
                _add_conduction_loss(sem_elem, cond_loss)
        elif conduction_losses:
            _add_conduction_loss(sem_elem, conduction_losses)
    
    # ThermalModel
    thermal = package.get('thermal_model', {})
    if thermal:
        thermal_elem = ET.SubElement(package_elem, 'ThermalModel')
        branch_elem = ET.SubElement(thermal_elem, 'Branch')
        branch_elem.set('type', thermal.get('type', 'Cauer'))
        rc_elements = thermal.get('rc_elements', [])
        for rc in rc_elements:
            rc_elem = ET.SubElement(branch_elem, 'RCElement')
            rc_elem.set('R', str(rc.get('R', 0)))
            rc_elem.set('C', str(rc.get('C', 0)))
    
    # Comment
    comment = package.get('comment', [])
    if comment:
        comment_elem = ET.SubElement(package_elem, 'Comment')
        for line in comment:
            ET.SubElement(comment_elem, 'Line').text = line
    
    # Format and write XML
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='    ')
    
    # Remove extra blank lines
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    formatted_xml = '\n'.join(lines)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(formatted_xml)
    
    return output_path


def _add_conduction_loss(parent, cond_loss: Dict[str, Any]):
    """Helper function to add ConductionLoss element."""
    cond_elem = ET.SubElement(parent, 'ConductionLoss')
    gate = cond_loss.get('gate')
    if gate:
        cond_elem.set('gate', gate)
    
    ET.SubElement(cond_elem, 'ComputationMethod').text = cond_loss.get('computation_method', 'Table only')
    if 'formula' in cond_loss:
        ET.SubElement(cond_elem, 'Formula').text = cond_loss['formula']
    if 'current_axis' in cond_loss:
        ET.SubElement(cond_elem, 'CurrentAxis').text = format_axis_values(cond_loss['current_axis'])
    if 'temperature_axis' in cond_loss:
        ET.SubElement(cond_elem, 'TemperatureAxis').text = format_axis_values(cond_loss['temperature_axis'])
    if 'voltage_drop' in cond_loss:
        vdrop = cond_loss['voltage_drop']
        vdrop_elem = ET.SubElement(cond_elem, 'VoltageDrop')
        vdrop_elem.set('scale', str(vdrop.get('scale', 1.0)))
        vdrop_data = vdrop.get('data', [])
        for row in vdrop_data:
            temp_elem = ET.SubElement(vdrop_elem, 'Temperature')
            temp_elem.text = format_axis_values(row)


def json_to_matlab(json_data: Dict[str, Any], output_path: str) -> str:
    """Convert JSON data to Matlab .mat file format."""
    metadata = json_data.get('metadata', {})
    package = json_data.get('package', {})
    
    # Create Matlab-compatible dictionary
    matlab_dict = {
        'Name': metadata.get('part_number', ''),
        'Manufacturer': metadata.get('manufacturer', ''),
        'Type': metadata.get('type', ''),
        'Material': metadata.get('material', ''),
        'PackageType': metadata.get('package_type', ''),
        'Author': metadata.get('author', ''),
        'Date': metadata.get('date', ''),
        'SourceFile': metadata.get('source_file', ''),
        'SourcePath': metadata.get('source_path', '')
    }
    
    # Add package data
    if package:
        matlab_dict['Package'] = {
            'Class': package.get('class', ''),
            'Vendor': package.get('vendor', ''),
            'PartNumber': package.get('partnumber', '')
        }
        
        # Variables
        if 'variables' in package:
            matlab_dict['Variables'] = package['variables']
        
        # Semiconductor data
        sem_data = package.get('semiconductor_data', {})
        if sem_data:
            matlab_dict['SemiconductorData'] = {
                'Type': sem_data.get('type', ''),
                'TurnOnLoss': sem_data.get('turn_on_loss', {}),
                'TurnOffLoss': sem_data.get('turn_off_loss', {}),
                'ConductionLoss': sem_data.get('conduction_loss', {})
            }
        
        # Thermal model
        if 'thermal_model' in package:
            matlab_dict['ThermalModel'] = package['thermal_model']
    
    # Convert None to empty arrays for Matlab compatibility
    def clean_for_matlab(obj):
        if obj is None:
            return []
        elif isinstance(obj, dict):
            return {k: clean_for_matlab(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_matlab(item) for item in obj]
        else:
            return obj
    
    matlab_dict = clean_for_matlab(matlab_dict)
    
    # Save to .mat file
    part_number = metadata.get('part_number', 'device').replace('-', '_')
    sio.savemat(output_path, {part_number: matlab_dict})
    
    return output_path


def json_to_pdf(json_data: Dict[str, Any], output_path: str) -> str:
    """Convert JSON data to PDF datasheet."""
    if not PDF_AVAILABLE:
        raise ImportError("reportlab is required for PDF generation. Install it with: pip install reportlab")
    
    metadata = json_data.get('metadata', {})
    package = json_data.get('package', {})
    
    # Create PDF document
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Heading style
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Title
    title = Paragraph(f"{metadata.get('part_number', 'Device')} Datasheet", title_style)
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
    # Metadata table
    metadata_data = [
        ['Manufacturer:', metadata.get('manufacturer', 'N/A')],
        ['Part Number:', metadata.get('part_number', 'N/A')],
        ['Type:', metadata.get('type', 'N/A')],
        ['Material:', metadata.get('material', 'N/A')],
        ['Package Type:', metadata.get('package_type', 'N/A')],
        ['Author:', metadata.get('author', 'N/A')],
        ['Date:', metadata.get('date', 'N/A')]
    ]
    
    metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(metadata_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Package Information
    if package:
        story.append(Paragraph("Package Information", heading_style))
        package_data = [
            ['Class:', package.get('class', 'N/A')],
            ['Vendor:', package.get('vendor', 'N/A')],
            ['Part Number:', package.get('partnumber', 'N/A')]
        ]
        package_table = Table(package_data, colWidths=[2*inch, 4*inch])
        package_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(package_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Variables
        variables = package.get('variables', [])
        if variables:
            story.append(Paragraph("Variables", heading_style))
            var_headers = [['Name', 'Description', 'Default', 'Min', 'Max']]
            var_data = [[
                var.get('name', ''),
                var.get('description', ''),
                str(var.get('default_value', '')),
                str(var.get('min_value', '')),
                str(var.get('max_value', ''))
            ] for var in variables]
            var_table = Table(var_headers + var_data, colWidths=[1*inch, 2*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            var_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(var_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Semiconductor Data Summary
        sem_data = package.get('semiconductor_data', {})
        if sem_data:
            story.append(Paragraph("Semiconductor Data", heading_style))
            sem_info = [
                ['Type:', sem_data.get('type', 'N/A')],
                ['Turn-On Loss Method:', sem_data.get('turn_on_loss', {}).get('computation_method', 'N/A')],
                ['Turn-Off Loss Method:', sem_data.get('turn_off_loss', {}).get('computation_method', 'N/A')]
            ]
            sem_table = Table(sem_info, colWidths=[2*inch, 4*inch])
            sem_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(sem_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Thermal Model
        thermal = package.get('thermal_model', {})
        if thermal:
            story.append(Paragraph("Thermal Model", heading_style))
            thermal_info = [['Type:', thermal.get('type', 'N/A')]]
            rc_elements = thermal.get('rc_elements', [])
            if rc_elements:
                thermal_info.append(['RC Elements:', f'{len(rc_elements)} elements'])
                for i, rc in enumerate(rc_elements):
                    thermal_info.append([f'  R{i+1}:', f"{rc.get('R', 0)} K/W"])
                    thermal_info.append([f'  C{i+1}:', f"{rc.get('C', 0)} J/K"])
            
            thermal_table = Table(thermal_info, colWidths=[2*inch, 4*inch])
            thermal_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(thermal_table)
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    footer = Paragraph(
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Data Router",
        styles['Normal']
    )
    story.append(footer)
    
    # Build PDF
    doc.build(story)
    
    return output_path


def convert_json_file(json_path: str, output_dir: str, formats: List[str] = ['xml', 'mat', 'pdf']) -> Dict[str, str]:
    """Convert a single JSON file to specified formats."""
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    metadata = json_data.get('metadata', {})
    part_number = metadata.get('part_number', Path(json_path).stem)
    safe_part_number = part_number.replace('-', '_').replace(' ', '_')
    
    output_files = {}
    os.makedirs(output_dir, exist_ok=True)
    
    if 'xml' in formats:
        xml_path = os.path.join(output_dir, f'{safe_part_number}.xml')
        json_to_plecs_xml(json_data, xml_path)
        output_files['xml'] = xml_path
    
    if 'mat' in formats:
        mat_path = os.path.join(output_dir, f'{safe_part_number}.mat')
        json_to_matlab(json_data, mat_path)
        output_files['mat'] = mat_path
    
    if 'pdf' in formats:
        pdf_path = os.path.join(output_dir, f'{safe_part_number}.pdf')
        try:
            json_to_pdf(json_data, pdf_path)
            output_files['pdf'] = pdf_path
        except ImportError as e:
            print(f"Warning: {e}")
    
    return output_files


def process_standard_database(
    input_dir: str = 'standard_database',
    output_dir: str = 'output',
    formats: List[str] = ['xml', 'mat', 'pdf']
):
    """Process all JSON files in standard_database and convert to specified formats."""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    json_files = list(input_path.glob('*.json'))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to convert")
    print(f"Output directory: {output_dir}")
    print(f"Formats: {', '.join(formats)}")
    
    converted_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            convert_json_file(str(json_file), output_dir, formats)
            converted_count += 1
            
            if converted_count % 50 == 0:
                print(f"Converted {converted_count}/{len(json_files)} files...")
        
        except Exception as e:
            error_count += 1
            print(f"Failed to convert {json_file}: {str(e)}")
    
    print(f"\nConversion complete!")
    print(f"Successfully converted: {converted_count} files")
    if error_count > 0:
        print(f"Errors: {error_count} files")
    print(f"All files saved to: {output_dir}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert JSON semiconductor models to various formats')
    parser.add_argument('--input', type=str, default='standard_database',
                        help='Input directory with JSON files (default: standard_database)')
    parser.add_argument('--output', type=str, default='output',
                        help='Output directory for converted files (default: output)')
    parser.add_argument('--formats', type=str, nargs='+', default=['xml', 'mat', 'pdf'],
                        choices=['xml', 'mat', 'pdf'],
                        help='Output formats (default: xml mat pdf)')
    
    args = parser.parse_args()
    
    process_standard_database(args.input, args.output, args.formats)

