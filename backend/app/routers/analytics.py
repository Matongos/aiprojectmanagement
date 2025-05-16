from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import logging

from ..database import get_db
from ..auth import get_current_user
from ..models import User
from ..schemas.analytics import ProjectStats, TaskDistribution, UserProductivity, TaskAnalytics
from ..crud.task_analytics import TaskAnalytics as TaskAnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

task_analytics = TaskAnalyticsService()
logger = logging.getLogger(__name__)

@router.get("/export/{report_type}/{format}")
async def export_report(
    report_type: str,
    format: str,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export report data in CSV or PDF format
    report_type: 'projects' or 'tasks'
    format: 'csv' or 'pdf'
    """
    try:
        if format not in ['csv', 'pdf']:
            raise HTTPException(status_code=400, detail="Format must be 'csv' or 'pdf'")
        if report_type not in ['projects', 'tasks']:
            raise HTTPException(status_code=400, detail="Report type must be 'projects' or 'tasks'")

        # Get report data based on type
        if report_type == 'projects':
            if not project_id:
                raise HTTPException(status_code=400, detail="Project ID is required for project reports")
            data = get_project_report_data(db, project_id, current_user)
        else:
            data = get_task_report_data(db, current_user)

        # Export based on format
        if format == 'csv':
            return export_csv(data, report_type)
        else:
            return export_pdf(data, report_type)
    except Exception as e:
        logger.error(f"Error exporting report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}")

def get_project_report_data(db: Session, project_id: int, current_user: User):
    """Gather all project-related data for export"""
    try:
        stats = task_analytics.calculate_project_completion_rate(db=db, project_id=project_id)
        distribution = task_analytics.get_task_distribution_by_status(db=db, project_id=project_id)
        productivity = task_analytics.get_user_productivity(db=db, user_id=current_user.id)
        
        return {
            "project_stats": stats,
            "task_distribution": distribution,
            "productivity": productivity
        }
    except Exception as e:
        logger.error(f"Error getting project report data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get project report data: {str(e)}")

def get_task_report_data(db: Session, current_user: User):
    """Gather all task-related data for export"""
    try:
        summary = task_analytics.get_task_analytics_summary(db=db)
        trend = task_analytics.get_task_trend_data(db=db)
        analytics = task_analytics.get_task_analytics_summary(db=db)
        
        return {
            "task_summary": summary,
            "task_trend": trend,
            "task_analytics": analytics
        }
    except Exception as e:
        logger.error(f"Error getting task report data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get task report data: {str(e)}")

def export_csv(data: dict, report_type: str) -> Response:
    """Export report data as CSV"""
    try:
        output = BytesIO()
        
        if report_type == 'projects':
            # Convert project data to DataFrames
            stats_df = pd.DataFrame([data['project_stats']])
            distribution_df = pd.DataFrame(data['task_distribution'])
            productivity_df = pd.DataFrame([data['productivity']])
            
            # Write to Excel
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                stats_df.to_excel(writer, sheet_name='Project Stats', index=False)
                distribution_df.to_excel(writer, sheet_name='Task Distribution', index=False)
                productivity_df.to_excel(writer, sheet_name='Productivity', index=False)
        else:
            # Convert task data to DataFrames
            summary_df = pd.DataFrame([data['task_summary']])
            trend_df = pd.DataFrame(data['task_trend'])
            analytics_df = pd.DataFrame([data['task_analytics']])
            
            # Write to Excel
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                summary_df.to_excel(writer, sheet_name='Task Summary', index=False)
                trend_df.to_excel(writer, sheet_name='Task Trend', index=False)
                analytics_df.to_excel(writer, sheet_name='Task Analytics', index=False)
        
        output.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_report_{timestamp}.xlsx"
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export to CSV: {str(e)}")

def export_pdf(data: dict, report_type: str) -> Response:
    """Export report data as PDF"""
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Set up PDF styling
        pdf.set_font("Arial", "B", 16)
        title = "Project Report" if report_type == 'projects' else "Task Report"
        pdf.cell(0, 10, title, ln=True, align='C')
        pdf.set_font("Arial", size=12)
        
        if report_type == 'projects':
            # Add project stats
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Project Statistics", ln=True)
            pdf.set_font("Arial", size=12)
            stats = data['project_stats']
            for key, value in stats.items():
                pdf.cell(0, 10, f"{key.replace('_', ' ').title()}: {value}", ln=True)
            
            # Add task distribution
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Task Distribution", ln=True)
            pdf.set_font("Arial", size=12)
            for item in data['task_distribution']:
                pdf.cell(0, 10, f"{item['status']}: {item['count']}", ln=True)
        else:
            # Add task summary
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Task Summary", ln=True)
            pdf.set_font("Arial", size=12)
            summary = data['task_summary']
            for key, value in summary.items():
                pdf.cell(0, 10, f"{key.replace('_', ' ').title()}: {value}", ln=True)
            
            # Add task analytics
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Task Analytics", ln=True)
            pdf.set_font("Arial", size=12)
            analytics = data['task_analytics']
            for key, value in analytics.items():
                if not isinstance(value, list):
                    pdf.cell(0, 10, f"{key.replace('_', ' ').title()}: {value}", ln=True)
        
        output = BytesIO()
        output.write(pdf.output(dest='S').encode('latin1'))
        output.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_report_{timestamp}.pdf"
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/pdf"
        }
        
        return Response(
            content=output.getvalue(),
            media_type="application/pdf",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Error exporting to PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export to PDF: {str(e)}")

@router.get("/project/{project_id}/completion")
async def get_project_completion(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get project completion statistics"""
    return task_analytics.calculate_project_completion_rate(db=db, project_id=project_id)

@router.get("/project/{project_id}/task-distribution")
async def get_task_distribution(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task distribution by status"""
    return task_analytics.get_task_distribution_by_status(db=db, project_id=project_id)

@router.get("/user/productivity")
async def get_user_productivity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user productivity metrics"""
    return task_analytics.get_user_productivity(db=db, user_id=current_user.id)

@router.get("/tasks/summary")
async def get_task_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task summary statistics"""
    return task_analytics.get_task_analytics_summary(db=db)

@router.get("/tasks/trend")
async def get_task_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task trend data"""
    return task_analytics.get_task_trend_data(db=db)

@router.get("/tasks/analysis")
async def get_task_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed task analysis"""
    return task_analytics.get_task_analytics_summary(db=db) 