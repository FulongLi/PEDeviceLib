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
import tempfile

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: reportlab not available. PDF generation will be disabled.")

# Import figure generation module
try:
    import sys
    data_process_path = os.path.join(os.path.dirname(__file__), 'data_process')
    if os.path.exists(data_process_path):
        sys.path.insert(0, data_process_path)
        from figure_process import generate_all_figures
        FIGURES_AVAILABLE = True
    else:
        FIGURES_AVAILABLE = False
except ImportError:
    FIGURES_AVAILABLE = False
    # Don't print warning if reportlab is also not available
    if PDF_AVAILABLE:
        print("Warning: figure_process module not available. PDF will be generated without figures.")


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


def json_to_pdf(json_data: Dict[str, Any], output_path: str, 
                figures_dir: Optional[str] = None, include_figures: bool = True) -> str:
    """Convert JSON data to PDF datasheet with optional figure integration."""
    if not PDF_AVAILABLE:
        raise ImportError("reportlab is required for PDF generation. Install it with: pip install reportlab")
    
    metadata = json_data.get('metadata', {})
    package = json_data.get('package', {})
    part_number = metadata.get('part_number', 'device')
    safe_part_number = part_number.replace('-', '_').replace(' ', '_')
    
    # Generate figures if requested and available
    figures = {}
    if include_figures and FIGURES_AVAILABLE:
        try:
            if figures_dir is None:
                # Create temporary directory for figures
                import tempfile
                temp_fig_dir = tempfile.mkdtemp()
                figures = generate_all_figures(json_data, temp_fig_dir, part_number)
            else:
                os.makedirs(figures_dir, exist_ok=True)
                figures = generate_all_figures(json_data, figures_dir, part_number)
        except Exception as e:
            print(f"Warning: Failed to generate figures: {e}")
            figures = {}
    
    # Create PDF document with custom page template
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Color scheme
    primary_color = colors.HexColor('#1e3a8a')  # Deep blue
    secondary_color = colors.HexColor('#3b82f6')  # Blue
    accent_color = colors.HexColor('#f59e0b')  # Amber
    dark_gray = colors.HexColor('#1f2937')
    light_gray = colors.HexColor('#f3f4f6')
    border_color = colors.HexColor('#e5e7eb')
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=primary_color,
        spaceAfter=15,
        spaceBefore=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=dark_gray,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    
    # Heading style
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=primary_color,
        spaceAfter=10,
        spaceBefore=20,
        fontName='Helvetica-Bold',
        borderPadding=5,
        borderColor=secondary_color,
        borderWidth=0,
        leftIndent=0
    )
    
    # Add logo if available
    logo_path = os.path.join(os.path.dirname(__file__), 'images', 'logo.png')
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=2*inch, height=0.8*inch)
            story.append(logo)
            story.append(Spacer(1, 0.1*inch))
        except Exception as e:
            print(f"Warning: Could not add logo: {e}")
    
    # Title
    title = Paragraph(f"{metadata.get('part_number', 'Device')}", title_style)
    story.append(title)
    subtitle = Paragraph("Semiconductor Device Datasheet", subtitle_style)
    story.append(subtitle)
    story.append(Spacer(1, 0.3*inch))
    
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
    
    metadata_table = Table(metadata_data, colWidths=[2.2*inch, 4.3*inch])
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), primary_color),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (1, 0), (1, -1), light_gray),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [light_gray, colors.white])
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
        package_table = Table(package_data, colWidths=[2.2*inch, 4.3*inch])
        package_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), secondary_color),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (1, 0), (1, -1), light_gray),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('GRID', (0, 0), (-1, -1), 1, border_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
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
            var_table = Table(var_headers + var_data, colWidths=[1.2*inch, 2.2*inch, 0.9*inch, 0.9*inch, 0.9*inch])
            var_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, border_color),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [light_gray, colors.white]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
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
            sem_table = Table(sem_info, colWidths=[2.2*inch, 4.3*inch])
            sem_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), secondary_color),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (1, 0), (1, -1), light_gray),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('GRID', (0, 0), (-1, -1), 1, border_color),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            story.append(sem_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Add figures if available
        if figures:
            story.append(PageBreak())
            story.append(Paragraph("Characteristic Curves", heading_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Turn-on loss figure
            if 'turnon_loss' in figures and os.path.exists(figures['turnon_loss']):
                try:
                    img = Image(figures['turnon_loss'], width=6*inch, height=3.6*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))
                except Exception as e:
                    print(f"Warning: Failed to add turn-on loss figure: {e}")
            
            # Turn-off loss figure
            if 'turnoff_loss' in figures and os.path.exists(figures['turnoff_loss']):
                try:
                    img = Image(figures['turnoff_loss'], width=6*inch, height=3.6*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))
                except Exception as e:
                    print(f"Warning: Failed to add turn-off loss figure: {e}")
            
            # Conduction characteristics figure
            if 'conduction' in figures and os.path.exists(figures['conduction']):
                try:
                    img = Image(figures['conduction'], width=6*inch, height=3.6*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))
                except Exception as e:
                    print(f"Warning: Failed to add conduction characteristics figure: {e}")
            
            # Thermal impedance figure
            if 'thermal' in figures and os.path.exists(figures['thermal']):
                try:
                    img = Image(figures['thermal'], width=6*inch, height=3.6*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))
                except Exception as e:
                    print(f"Warning: Failed to add thermal impedance figure: {e}")
            
            story.append(PageBreak())
        
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
            
            thermal_table = Table(thermal_info, colWidths=[2.2*inch, 4.3*inch])
            thermal_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), secondary_color),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (1, 0), (1, -1), light_gray),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('GRID', (0, 0), (-1, -1), 1, border_color),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            story.append(thermal_table)
    
    # Footer with styled border
    story.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=dark_gray,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    footer = Paragraph(
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Data Router | Power Electronics Device Library",
        footer_style
    )
    story.append(footer)
    
    # Build PDF
    doc.build(story)
    
    return output_path


def json_to_html(json_data: Dict[str, Any], output_path: str,
                 figures_dir: Optional[str] = None, include_figures: bool = True) -> str:
    """Convert JSON data to HTML datasheet."""
    metadata = json_data.get('metadata', {})
    package = json_data.get('package', {})
    part_number = metadata.get('part_number', 'device')
    safe_part_number = part_number.replace('-', '_').replace(' ', '_')
    
    # Generate figures if requested and available
    figures = {}
    if include_figures and FIGURES_AVAILABLE:
        try:
            if figures_dir is None:
                import tempfile
                temp_fig_dir = tempfile.mkdtemp()
                figures = generate_all_figures(json_data, temp_fig_dir, part_number)
            else:
                os.makedirs(figures_dir, exist_ok=True)
                figures = generate_all_figures(json_data, figures_dir, part_number)
        except Exception as e:
            print(f"Warning: Failed to generate figures: {e}")
            figures = {}
    
    # Start building HTML
    html_parts = []
    
    # Determine logo path
    logo_path = os.path.join(os.path.dirname(__file__), 'images', 'logo.png')
    logo_relative = None
    if os.path.exists(logo_path):
        # Calculate relative path from HTML file to logo
        html_dir = os.path.dirname(output_path)
        logo_relative = os.path.relpath(logo_path, html_dir).replace('\\', '/')
    
    # HTML header
    html_parts.append('<!DOCTYPE html>')
    html_parts.append('<html lang="en">')
    html_parts.append('<head>')
    html_parts.append('    <meta charset="UTF-8">')
    html_parts.append('    <meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_parts.append(f'    <title>{part_number} Datasheet</title>')
    html_parts.append('    <style>')
    html_parts.append('        * { margin: 0; padding: 0; box-sizing: border-box; }')
    html_parts.append('        body { font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }')
    html_parts.append('        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 40px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); border-radius: 10px; }')
    html_parts.append('        .header { text-align: center; margin-bottom: 40px; padding-bottom: 20px; border-bottom: 3px solid #1e3a8a; }')
    html_parts.append('        .logo-container { margin-bottom: 20px; }')
    html_parts.append('        .logo-container img { max-height: 80px; width: auto; }')
    html_parts.append('        h1 { color: #1e3a8a; font-size: 2.5em; margin: 10px 0; font-weight: 700; }')
    html_parts.append('        .subtitle { color: #6b7280; font-size: 1.1em; font-style: italic; margin-top: 5px; }')
    html_parts.append('        h2 { color: #1e3a8a; margin-top: 40px; margin-bottom: 20px; font-size: 1.8em; font-weight: 600; padding-left: 15px; border-left: 5px solid #3b82f6; }')
    html_parts.append('        table { width: 100%; border-collapse: collapse; margin: 25px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }')
    html_parts.append('        th { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 15px; text-align: left; font-weight: 600; font-size: 0.95em; }')
    html_parts.append('        td { padding: 12px 15px; border-bottom: 1px solid #e5e7eb; }')
    html_parts.append('        tr:last-child td { border-bottom: none; }')
    html_parts.append('        tr:nth-child(even) { background-color: #f9fafb; }')
    html_parts.append('        tr:hover { background-color: #f3f4f6; transition: background-color 0.2s; }')
    html_parts.append('        .metadata-table th { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); }')
    html_parts.append('        .metadata-table td:first-child { background-color: #1e3a8a; color: white; font-weight: 600; width: 30%; }')
    html_parts.append('        .metadata-table td:last-child { background-color: #f9fafb; }')
    html_parts.append('        .figure-container { margin: 40px 0; text-align: center; padding: 20px; background-color: #f9fafb; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }')
    html_parts.append('        .figure-container img { max-width: 100%; height: auto; border: 2px solid #e5e7eb; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius: 6px; }')
    html_parts.append('        .figure-title { font-weight: 600; margin: 15px 0 10px 0; color: #1e3a8a; font-size: 1.2em; }')
    html_parts.append('        .footer { text-align: center; color: #6b7280; margin-top: 50px; padding-top: 25px; border-top: 2px solid #e5e7eb; font-size: 0.9em; }')
    html_parts.append('        .section { margin-bottom: 50px; }')
    html_parts.append('        .info-badge { display: inline-block; padding: 5px 12px; background-color: #3b82f6; color: white; border-radius: 20px; font-size: 0.85em; font-weight: 500; margin: 2px; }')
    html_parts.append('        @media print { body { background: white; padding: 0; } .container { box-shadow: none; } }')
    html_parts.append('        @media (max-width: 768px) { .container { padding: 20px; } h1 { font-size: 1.8em; } table { font-size: 0.9em; } }')
    html_parts.append('    </style>')
    html_parts.append('</head>')
    html_parts.append('<body>')
    html_parts.append('    <div class="container">')
    
    # Header with logo and title
    html_parts.append('        <div class="header">')
    if logo_relative:
        html_parts.append(f'            <div class="logo-container"><img src="{logo_relative}" alt="Logo"></div>')
    html_parts.append(f'            <h1>{part_number}</h1>')
    html_parts.append('            <div class="subtitle">Semiconductor Device Datasheet</div>')
    html_parts.append('        </div>')
    
    # Metadata section
    html_parts.append('        <div class="section">')
    html_parts.append('            <h2>Device Information</h2>')
    html_parts.append('            <table class="metadata-table">')
    html_parts.append(f'                <tr><td>Manufacturer</td><td>{metadata.get("manufacturer", "N/A")}</td></tr>')
    html_parts.append(f'                <tr><td>Part Number</td><td>{metadata.get("part_number", "N/A")}</td></tr>')
    html_parts.append(f'                <tr><td>Type</td><td>{metadata.get("type", "N/A")}</td></tr>')
    html_parts.append(f'                <tr><td>Material</td><td><span class="info-badge">{metadata.get("material", "N/A")}</span></td></tr>')
    html_parts.append(f'                <tr><td>Package Type</td><td><span class="info-badge">{metadata.get("package_type", "N/A")}</span></td></tr>')
    html_parts.append(f'                <tr><td>Author</td><td>{metadata.get("author", "N/A")}</td></tr>')
    html_parts.append(f'                <tr><td>Date</td><td>{metadata.get("date", "N/A")}</td></tr>')
    html_parts.append('            </table>')
    html_parts.append('        </div>')
    
    # Package Information
    if package:
        html_parts.append('        <div class="section">')
        html_parts.append('            <h2>Package Information</h2>')
        html_parts.append('            <table>')
        html_parts.append(f'                <tr><th>Class</th><td>{package.get("class", "N/A")}</td></tr>')
        html_parts.append(f'                <tr><th>Vendor</th><td>{package.get("vendor", "N/A")}</td></tr>')
        html_parts.append(f'                <tr><th>Part Number</th><td>{package.get("partnumber", "N/A")}</td></tr>')
        html_parts.append('            </table>')
        html_parts.append('        </div>')
        
        # Variables
        variables = package.get('variables', [])
        if variables:
            html_parts.append('        <div class="section">')
            html_parts.append('            <h2>Variables</h2>')
            html_parts.append('            <table>')
            html_parts.append('                <tr><th>Name</th><th>Description</th><th>Default</th><th>Min</th><th>Max</th></tr>')
            for var in variables:
                html_parts.append('                <tr>')
                html_parts.append(f'                    <td><strong>{var.get("name", "")}</strong></td>')
                html_parts.append(f'                    <td>{var.get("description", "")}</td>')
                html_parts.append(f'                    <td><span class="info-badge">{var.get("default_value", "")}</span></td>')
                html_parts.append(f'                    <td>{var.get("min_value", "")}</td>')
                html_parts.append(f'                    <td>{var.get("max_value", "")}</td>')
                html_parts.append('                </tr>')
            html_parts.append('            </table>')
            html_parts.append('        </div>')
        
        # Semiconductor Data
        sem_data = package.get('semiconductor_data', {})
        if sem_data:
            html_parts.append('        <div class="section">')
            html_parts.append('            <h2>Semiconductor Data</h2>')
            html_parts.append('            <table>')
            html_parts.append(f'                <tr><th>Type</th><td>{sem_data.get("type", "N/A")}</td></tr>')
            html_parts.append(f'                <tr><th>Turn-On Loss Method</th><td>{sem_data.get("turn_on_loss", {}).get("computation_method", "N/A")}</td></tr>')
            html_parts.append(f'                <tr><th>Turn-Off Loss Method</th><td>{sem_data.get("turn_off_loss", {}).get("computation_method", "N/A")}</td></tr>')
            html_parts.append('            </table>')
            html_parts.append('        </div>')
        
        # Thermal Model
        thermal = package.get('thermal_model', {})
        if thermal:
            html_parts.append('        <div class="section">')
            html_parts.append('            <h2>Thermal Model</h2>')
            html_parts.append('            <table>')
            html_parts.append(f'                <tr><th>Type</th><td>{thermal.get("type", "N/A")}</td></tr>')
            rc_elements = thermal.get('rc_elements', [])
            if rc_elements:
                html_parts.append(f'                <tr><th>RC Elements</th><td>{len(rc_elements)} elements</td></tr>')
                for i, rc in enumerate(rc_elements):
                    html_parts.append(f'                <tr><th>R{i+1}</th><td>{rc.get("R", 0)} K/W</td></tr>')
                    html_parts.append(f'                <tr><th>C{i+1}</th><td>{rc.get("C", 0)} J/K</td></tr>')
            html_parts.append('            </table>')
            html_parts.append('        </div>')
    
    # Add figures if available
    if figures:
        html_parts.append('        <div class="section">')
        html_parts.append('            <h2>Characteristic Curves</h2>')
        
        # Determine relative path for images
        html_dir = os.path.dirname(output_path)
        if figures_dir:
            # Calculate relative path from HTML file to figures directory
            if os.path.isabs(figures_dir):
                fig_rel_path = os.path.relpath(figures_dir, html_dir)
            else:
                fig_rel_path = figures_dir
        else:
            fig_rel_path = 'figures'
        
        # Turn-on loss
        if 'turnon_loss' in figures and os.path.exists(figures['turnon_loss']):
            fig_filename = os.path.basename(figures['turnon_loss'])
            fig_path = os.path.join(fig_rel_path, fig_filename).replace('\\', '/')
            html_parts.append('            <div class="figure-container">')
            html_parts.append('                <div class="figure-title">Turn-On Loss Characteristics</div>')
            html_parts.append(f'                <img src="{fig_path}" alt="Turn-On Loss">')
            html_parts.append('            </div>')
        
        # Turn-off loss
        if 'turnoff_loss' in figures and os.path.exists(figures['turnoff_loss']):
            fig_filename = os.path.basename(figures['turnoff_loss'])
            fig_path = os.path.join(fig_rel_path, fig_filename).replace('\\', '/')
            html_parts.append('            <div class="figure-container">')
            html_parts.append('                <div class="figure-title">Turn-Off Loss Characteristics</div>')
            html_parts.append(f'                <img src="{fig_path}" alt="Turn-Off Loss">')
            html_parts.append('            </div>')
        
        # Conduction characteristics
        if 'conduction' in figures and os.path.exists(figures['conduction']):
            fig_filename = os.path.basename(figures['conduction'])
            fig_path = os.path.join(fig_rel_path, fig_filename).replace('\\', '/')
            html_parts.append('            <div class="figure-container">')
            html_parts.append('                <div class="figure-title">Conduction Characteristics</div>')
            html_parts.append(f'                <img src="{fig_path}" alt="Conduction Characteristics">')
            html_parts.append('            </div>')
        
        # Thermal impedance
        if 'thermal' in figures and os.path.exists(figures['thermal']):
            fig_filename = os.path.basename(figures['thermal'])
            fig_path = os.path.join(fig_rel_path, fig_filename).replace('\\', '/')
            html_parts.append('            <div class="figure-container">')
            html_parts.append('                <div class="figure-title">Thermal Impedance</div>')
            html_parts.append(f'                <img src="{fig_path}" alt="Thermal Impedance">')
            html_parts.append('            </div>')
        
        html_parts.append('        </div>')
    
    # Footer
    html_parts.append('        <div class="footer">')
    html_parts.append(f'            <p><strong>Power Electronics Device Library</strong></p>')
    html_parts.append(f'            <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} by Data Router</p>')
    html_parts.append('        </div>')
    
    html_parts.append('    </div>')
    html_parts.append('</body>')
    html_parts.append('</html>')
    
    # Write HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))
    
    return output_path


def convert_json_file(json_path: str, output_dir: str, formats: List[str] = ['xml', 'mat', 'pdf', 'html']) -> Dict[str, str]:
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
            # Create a subdirectory for figures if needed
            figures_subdir = os.path.join(output_dir, 'figures')
            json_to_pdf(json_data, pdf_path, figures_dir=figures_subdir, include_figures=True)
            output_files['pdf'] = pdf_path
        except ImportError as e:
            print(f"Warning: {e}")
        except Exception as e:
            print(f"Warning: Failed to generate PDF: {e}")
    
    if 'html' in formats:
        html_path = os.path.join(output_dir, f'{safe_part_number}.html')
        try:
            # Create a subdirectory for figures if needed
            figures_subdir = os.path.join(output_dir, 'figures')
            json_to_html(json_data, html_path, figures_dir=figures_subdir, include_figures=True)
            output_files['html'] = html_path
        except Exception as e:
            print(f"Warning: Failed to generate HTML: {e}")
    
    return output_files


def process_standard_database(
    input_dir: str = 'standard_database',
    output_dir: str = 'output',
    formats: List[str] = ['xml', 'mat', 'pdf', 'html']
):
    """Process all JSON files in standard_database and convert to specified formats."""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_dir}")
    
    # Check if input is a file or directory
    if input_path.is_file():
        json_files = [input_path]
    else:
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
    parser.add_argument('--formats', type=str, nargs='+', default=['xml', 'mat', 'pdf', 'html'],
                        choices=['xml', 'mat', 'pdf', 'html'],
                        help='Output formats (default: xml mat pdf html)')
    
    args = parser.parse_args()
    
    process_standard_database(args.input, args.output, args.formats)

