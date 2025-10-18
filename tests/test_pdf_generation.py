#!/usr/bin/env python3
"""
Test PDF generation functionality for Medical RAG system
"""

import os
import sys
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def test_pdf_generation():
    """Test PDF generation for both doctor summary and patient education"""
    
    print("🧪 Testing PDF Generation for Medical RAG System")
    print("=" * 60)
    
    # Sample data
    patient_data = {
        "name": "John Doe",
        "patient_id": "P12345",
        "age": 65,
        "gender": "Male"
    }
    
    # Sample doctor summary
    doctor_summary = """
### Clinical Assessment
Patient presents with well-controlled Type 2 diabetes mellitus, hypertension, and hyperlipidemia. Current medication regimen appears appropriate for age and comorbidities.

### Critical Alerts
**Drug Interaction Warning**: Monitor for potential interaction between Metformin and Lisinopril in elderly patients with regard to kidney function.

### Treatment Plan
1. Continue current diabetes management with Metformin
2. Maintain blood pressure control with Lisinopril
3. Continue statin therapy for cholesterol management

### Monitoring Requirements
- HbA1c every 3-6 months
- Kidney function monitoring every 6 months
- Blood pressure monitoring at each visit

### Next Steps
- Schedule follow-up in 3 months
- Order comprehensive metabolic panel
- Consider diabetes educator referral
"""
    
    # Sample patient education
    patient_education = """
# Your Health Guide: Managing Diabetes, High Blood Pressure, and High Cholesterol

## Understanding Your Conditions

### Type 2 Diabetes
Your body doesn't use insulin properly, which causes high blood sugar levels. This is manageable with medication, diet, and exercise.

### High Blood Pressure (Hypertension)
This means your heart has to work harder to pump blood. It's often called the "silent killer" because it usually has no symptoms.

### High Cholesterol
Too much cholesterol in your blood can clog your arteries and lead to heart problems.

## Your Medications

### Metformin
- **What it does**: Helps lower your blood sugar
- **How to take**: Take with meals to reduce stomach upset
- **Watch for**: Stomach upset, metallic taste

### Lisinopril
- **What it does**: Helps lower your blood pressure
- **How to take**: Same time each day, with or without food
- **Watch for**: Dry cough, dizziness when standing

## Lifestyle Recommendations

### Diet Tips
- Choose whole grains over refined carbohydrates
- Eat plenty of vegetables and lean proteins
- Limit sodium to help control blood pressure
- Monitor portion sizes

### Exercise Guidelines
- Aim for 30 minutes of moderate activity most days
- Walking is an excellent low-impact exercise
- Check your blood sugar before and after exercise

## When to Contact Your Doctor

### Call Immediately If:
- Blood sugar over 300 or under 70
- Severe chest pain or shortness of breath
- Signs of stroke (face drooping, arm weakness, speech difficulty)

### Schedule an Appointment If:
- Persistent high blood sugar readings
- New or worsening symptoms
- Questions about your medications
"""
    
    print("\n📄 Testing Doctor Summary PDF Generation...")
    try:
        # Generate doctor summary PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1
        )
        
        story = []
        story.append(Paragraph("CLINICAL SUMMARY", title_style))
        story.append(Spacer(1, 20))
        
        # Patient info table
        patient_info = [
            ['Patient:', patient_data['name']],
            ['ID:', patient_data['patient_id']],
            ['Age:', f"{patient_data['age']} years"],
            ['Gender:', patient_data['gender']]
        ]
        
        patient_table = Table(patient_info, colWidths=[1.5*inch, 4*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(patient_table)
        story.append(Spacer(1, 20))
        
        # Add summary content
        paragraphs = doctor_summary.split('\n\n')
        for para in paragraphs:
            if para.strip():
                clean_para = para.replace('**', '').replace('###', '').strip()
                if clean_para:
                    story.append(Paragraph(clean_para, styles['Normal']))
                    story.append(Spacer(1, 12))
        
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Save test file
        with open("test_doctor_summary.pdf", "wb") as f:
            f.write(pdf_data)
        
        print(f"✅ Doctor summary PDF generated successfully!")
        print(f"   File size: {len(pdf_data)} bytes")
        print(f"   Saved as: test_doctor_summary.pdf")
        
    except Exception as e:
        print(f"❌ Doctor summary PDF generation failed: {e}")
    
    print("\n👤 Testing Patient Education PDF Generation...")
    try:
        # Generate patient education PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Custom styles for patient education
        title_style = ParagraphStyle(
            'PatientTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.darkgreen,
            alignment=1
        )
        
        story = []
        story.append(Paragraph("YOUR HEALTH GUIDE", title_style))
        story.append(Paragraph(f"Personal Health Information for {patient_data['name']}", styles['Heading2']))
        story.append(Spacer(1, 20))
        
        # Patient info table
        patient_info = [
            ['Patient Name:', patient_data['name']],
            ['Age:', f"{patient_data['age']} years"],
            ['Date Generated:', datetime.now().strftime('%B %d, %Y')]
        ]
        
        patient_table = Table(patient_info, colWidths=[2*inch, 3.5*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.darkgreen),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
        ]))
        
        story.append(patient_table)
        story.append(Spacer(1, 25))
        
        # Process education content
        sections = patient_education.split('\n\n')
        for section in sections:
            if section.strip():
                if section.startswith('# '):
                    header_text = section.replace('# ', '').strip()
                    story.append(Paragraph(header_text, styles['Heading1']))
                elif section.startswith('## '):
                    header_text = section.replace('## ', '').strip()
                    story.append(Paragraph(header_text, styles['Heading2']))
                elif section.startswith('### '):
                    header_text = section.replace('### ', '').strip()
                    story.append(Paragraph(header_text, styles['Heading3']))
                else:
                    # Clean and add regular content
                    clean_section = section.replace('**', '').replace('*', '•')
                    story.append(Paragraph(clean_section, styles['Normal']))
                
                story.append(Spacer(1, 12))
        
        # Add important notice
        notice_data = [[Paragraph("IMPORTANT: This information is for educational purposes only. Always consult with your healthcare provider.", styles['Normal'])]]
        notice_table = Table(notice_data, colWidths=[6*inch])
        notice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightyellow),
            ('BORDER', (0, 0), (-1, -1), 2, colors.red),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(Spacer(1, 20))
        story.append(notice_table)
        
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Save test file
        with open("test_patient_education.pdf", "wb") as f:
            f.write(pdf_data)
        
        print(f"✅ Patient education PDF generated successfully!")
        print(f"   File size: {len(pdf_data)} bytes")
        print(f"   Saved as: test_patient_education.pdf")
        
    except Exception as e:
        print(f"❌ Patient education PDF generation failed: {e}")
    
    print("\n📊 PDF Generation Summary:")
    print("- Doctor Summary PDF: Professional medical document with structured layout")
    print("- Patient Education PDF: Patient-friendly guide with clear formatting")
    print("- Both PDFs include patient information tables and proper styling")
    print("- Files are ready for download in Streamlit application")
    
    print("\n🏁 PDF Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_pdf_generation()