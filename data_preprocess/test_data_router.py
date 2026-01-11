"""
Test script for data_router.py

This script tests the conversion of a single device from JSON to:
- PLECS XML format
- Matlab .mat format
- PDF datasheet format
"""

import os
import json
from pathlib import Path
from data_router import json_to_plecs_xml, json_to_matlab, json_to_pdf

# Test device
TEST_DEVICE = 'C2M0025120D'
TEST_INPUT = f'standard_database/{TEST_DEVICE}.json'
TEST_OUTPUT_DIR = 'test_output'

def main():
    """Test conversion for a single device."""
    print(f"Testing data_router conversion for device: {TEST_DEVICE}")
    print("=" * 70)
    
    # Check if input file exists
    if not os.path.exists(TEST_INPUT):
        print(f"Error: Input file not found: {TEST_INPUT}")
        return
    
    # Load JSON data
    print(f"\n1. Loading JSON data from: {TEST_INPUT}")
    with open(TEST_INPUT, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    metadata = json_data.get('metadata', {})
    print(f"   Device: {metadata.get('part_number', 'N/A')}")
    print(f"   Manufacturer: {metadata.get('manufacturer', 'N/A')}")
    print(f"   Type: {metadata.get('type', 'N/A')}")
    print(f"   Material: {metadata.get('material', 'N/A')}")
    print(f"   Package Type: {metadata.get('package_type', 'N/A')}")
    
    # Create output directory
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    print(f"\n2. Output directory: {TEST_OUTPUT_DIR}")
    
    # Test PLECS XML conversion
    print("\n3. Testing PLECS XML conversion...")
    try:
        xml_path = os.path.join(TEST_OUTPUT_DIR, f'{TEST_DEVICE}.xml')
        json_to_plecs_xml(json_data, xml_path)
        print(f"   [OK] PLECS XML generated: {xml_path}")
        
        # Check file size
        file_size = os.path.getsize(xml_path)
        print(f"   [OK] File size: {file_size:,} bytes")
        
        # Check if file contains expected elements
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
            if '<SemiconductorLibrary>' in xml_content:
                print(f"   [OK] Contains SemiconductorLibrary element")
            if '<Package' in xml_content:
                print(f"   [OK] Contains Package element")
            if '<SemiconductorData' in xml_content:
                print(f"   [OK] Contains SemiconductorData element")
            if '<TurnOnLoss>' in xml_content:
                print(f"   [OK] Contains TurnOnLoss element")
            if '<TurnOffLoss>' in xml_content:
                print(f"   [OK] Contains TurnOffLoss element")
            if '<ConductionLoss' in xml_content:
                print(f"   [OK] Contains ConductionLoss element")
            if '<ThermalModel>' in xml_content:
                print(f"   [OK] Contains ThermalModel element")
    except Exception as e:
        print(f"   [ERROR] Error generating PLECS XML: {str(e)}")
    
    # Test Matlab .mat conversion
    print("\n4. Testing Matlab .mat conversion...")
    try:
        mat_path = os.path.join(TEST_OUTPUT_DIR, f'{TEST_DEVICE}.mat')
        json_to_matlab(json_data, mat_path)
        print(f"   [OK] Matlab .mat file generated: {mat_path}")
        
        # Check file size
        file_size = os.path.getsize(mat_path)
        print(f"   [OK] File size: {file_size:,} bytes")
        
        # Try to load and verify the .mat file
        import scipy.io as sio
        mat_data = sio.loadmat(mat_path)
        print(f"   [OK] Successfully loaded .mat file")
        
        # Check for expected keys
        part_key = TEST_DEVICE.replace('-', '_')
        if part_key in mat_data:
            device_data = mat_data[part_key]
            print(f"   [OK] Contains device data structure")
            if 'Name' in device_data.dtype.names:
                print(f"   [OK] Contains Name field")
            if 'Manufacturer' in device_data.dtype.names:
                print(f"   [OK] Contains Manufacturer field")
            if 'Package' in device_data.dtype.names:
                print(f"   [OK] Contains Package field")
    except Exception as e:
        print(f"   [ERROR] Error generating Matlab .mat file: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test PDF conversion
    print("\n5. Testing PDF datasheet conversion...")
    try:
        pdf_path = os.path.join(TEST_OUTPUT_DIR, f'{TEST_DEVICE}.pdf')
        json_to_pdf(json_data, pdf_path)
        print(f"   [OK] PDF datasheet generated: {pdf_path}")
        
        # Check file size
        file_size = os.path.getsize(pdf_path)
        print(f"   [OK] File size: {file_size:,} bytes")
        
        # Check if file is a valid PDF
        with open(pdf_path, 'rb') as f:
            header = f.read(4)
            if header == b'%PDF':
                print(f"   [OK] Valid PDF file (PDF header found)")
            else:
                print(f"   [WARNING] PDF header not found")
    except ImportError as e:
        print(f"   [SKIPPED] PDF generation skipped: {str(e)}")
        print(f"   Install reportlab with: pip install reportlab")
    except Exception as e:
        print(f"   [ERROR] Error generating PDF: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary:")
    print(f"  Input: {TEST_INPUT}")
    print(f"  Output directory: {TEST_OUTPUT_DIR}")
    
    # List generated files
    generated_files = []
    xml_file = os.path.join(TEST_OUTPUT_DIR, f'{TEST_DEVICE}.xml')
    mat_file = os.path.join(TEST_OUTPUT_DIR, f'{TEST_DEVICE}.mat')
    pdf_file = os.path.join(TEST_OUTPUT_DIR, f'{TEST_DEVICE}.pdf')
    
    if os.path.exists(xml_file):
        generated_files.append(f"  [OK] {xml_file}")
    if os.path.exists(mat_file):
        generated_files.append(f"  [OK] {mat_file}")
    if os.path.exists(pdf_file):
        generated_files.append(f"  [OK] {pdf_file}")
    
    if generated_files:
        print("\nGenerated files:")
        for file in generated_files:
            print(file)
    else:
        print("\n  No files were generated.")
    
    print("\nTest completed!")


if __name__ == '__main__':
    main()

